"""P02 hero case: the first executable counterfactual AI-failure experiment.

Seven contract tests (ticket P02 "Red tests to write FIRST"):
  1. test_one_factor_at_a_time       — pairwise effective-config diff
  2. test_causal_discrimination      — arm verdicts/outputs vs sealed oracle
  3. test_clean_replay               — two run_case same seed identical + replay
  4. test_machine_provenance         — engine metadata + forged-manifest reject
  5. test_self_attestation / swapped — in tests/test_execution.py (ported f02)
  6. test_oracle_not_leaked          — grep canonical artifacts for oracle literals
  7. test_determinism_across_seeds   — seed does not change deterministic output
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from repliclaw.counterfactual import (
    ARM_FILES,
    load_case,
    load_interventions,
    replay,
    run_case,
)
from repliclaw.counterfactual.case import (
    ALL_FACTORS,
    FACTOR_JUDGE_REFERENCE,
    FACTOR_POLICY_CONFLICT,
    FACTOR_RETRIEVAL,
)
from repliclaw.counterfactual.frozen_backend import extract_window_days

CANONICAL = Path("artifacts/science/p02-hero-canonical")
ORACLE = Path("experiments/policy_rag/oracle/oracle.json")
CASE_ID = "policy_rag_v1"


@pytest.fixture(scope="module")
def case():
    return load_case(CASE_ID)


@pytest.fixture(scope="module")
def interventions():
    return {i.intervention_id: i for i in load_interventions(CASE_ID)}


@pytest.fixture(scope="module")
def oracle():
    return json.loads(ORACLE.read_text())


@pytest.fixture(scope="module")
def runs(tmp_path_factory, case):
    """All five arms, persisted, in a module-scoped temp dir."""
    out = tmp_path_factory.mktemp("p02_runs")
    return {
        i.intervention_id: run_case(case, i, seed=0, out_root=out)
        for i in load_interventions(CASE_ID)
    }, out


def _runs_only(runs):
    return runs[0]


# 1 --------------------------------------------------------------------------
def test_one_factor_at_a_time(interventions):
    """Every causal arm changes exactly ONE factor vs base; I_C the two."""
    for iid, iv in interventions.items():
        changed = set(iv.changed_factors())
        assert changed.issubset(set(ALL_FACTORS))
    assert set(interventions["I0_baseline"].changed_factors()) == set()
    assert set(interventions["I_R_retrieval_fix"].changed_factors()) == {FACTOR_RETRIEVAL}
    assert set(interventions["I_P_policy_conflict"].changed_factors()) == {FACTOR_POLICY_CONFLICT}
    assert set(interventions["I_J_judge_fix"].changed_factors()) == {FACTOR_JUDGE_REFERENCE}
    assert set(interventions["I_C_retrieval_judge"].changed_factors()) == {
        FACTOR_RETRIEVAL,
        FACTOR_JUDGE_REFERENCE,
    }
    # Pairwise effective-config diff: I0 vs each arm touches exactly the
    # declared factor(s) and NOTHING else.
    case = load_case(CASE_ID)
    base = case.base_config()
    for iid, iv in interventions.items():
        eff = iv.resolve(case)
        diff = {k for k in ALL_FACTORS if eff[k] != base[k]}
        assert diff == set(iv.changed_factors()), f"{iid}: diff={diff}"


# 2 --------------------------------------------------------------------------
def test_causal_discrimination(runs, oracle):
    """Arm outcomes match the sealed oracle; I_R exposes the planted fault."""
    r = _runs_only(runs)
    expected = oracle["expected_arm_outcomes"]
    assert r["I0_baseline"].severity == expected["I0_baseline"]["severity"] == "pass"
    assert extract_window_days(r["I0_baseline"].target_output) == 14
    assert r["I_R_retrieval_fix"].severity == expected["I_R_retrieval_fix"]["severity"] == "critical"
    assert extract_window_days(r["I_R_retrieval_fix"].target_output) == 30
    # I_P: byte-identical output to I0 -> H_P not supported.
    assert r["I_P_policy_conflict"].target_output == r["I0_baseline"].target_output
    assert r["I_P_policy_conflict"].severity == "pass"
    # I_J: byte-identical output, verdict flipped (stale judge hid a violation).
    assert r["I_J_judge_fix"].target_output == r["I0_baseline"].target_output
    assert r["I_J_judge_fix"].severity == "critical"
    # I_C control: 30d target + 30d rubric -> consistent PASS.
    assert extract_window_days(r["I_C_retrieval_judge"].target_output) == 30
    assert r["I_C_retrieval_judge"].severity == "pass"
    # Hypothesis supported by the intervention pattern.
    assert oracle["true_cause"] == "retrieval_omission"
    assert oracle["supports_hypothesis"]["H_R"] == "I_R"


# 3 --------------------------------------------------------------------------
def test_clean_replay(tmp_path, case, interventions):
    """Same seed twice -> identical outputs/judgment/hashes; replay() True."""
    iv = interventions["I_R_retrieval_fix"]
    out1 = tmp_path / "a"
    out2 = tmp_path / "b"
    r1 = run_case(case, iv, seed=0, out_root=out1)
    r2 = run_case(case, iv, seed=0, out_root=out2)
    assert r1.target_output == r2.target_output
    assert r1.judgment == r2.judgment
    assert r1.config_sha256 == r2.config_sha256
    assert r1.artifact_hashes == r2.artifact_hashes
    # Persisted arm files byte-identical across the two run dirs.
    for name in ARM_FILES:
        b1 = (out1 / "interventions" / iv.intervention_id / name).read_bytes()
        b2 = (out2 / "interventions" / iv.intervention_id / name).read_bytes()
        assert b1 == b2, name

    # Full-case canonical replay: pin manifest, then verify.
    canon = tmp_path / "canon"
    from repliclaw.counterfactual import run_canonical

    run_canonical(case, load_interventions(CASE_ID), seed=0, out_root=canon)
    assert replay(CASE_ID, canon) is True


# 4 --------------------------------------------------------------------------
def test_machine_provenance(tmp_path, case, interventions):
    """Every run carries engine name/version/git-sha + machine-replayable
    provenance; a forged manifest (tampered target_output pin) is rejected."""
    from repliclaw.counterfactual import sha256_bytes

    r = run_case(case, interventions["I0_baseline"], seed=0, out_root=tmp_path / "x")
    assert r.engine["name"] == "simpleaudit"
    assert r.engine["version"], "engine version must be pinned"
    assert r.engine["git_sha"], "engine git sha must be recorded"
    assert r.run_id and r.model_id and r.config_sha256 and r.case_sha256
    assert r.exit_code == 0
    assert r.token_counts["real_token_calls"] == 0

    # Forged manifest: pin the I0 target_output.txt to a hash of bytes that
    # were never produced. Stored-artifact pass must reject.
    canon = tmp_path / "forged"
    from repliclaw.counterfactual import run_canonical

    run_canonical(case, load_interventions(CASE_ID), seed=0, out_root=canon)
    manifest = json.loads((canon / "manifest.json").read_text())
    manifest["arms"]["I0_baseline"]["artifacts"]["target_output.txt"] = sha256_bytes(
        b"never produced\n"
    )
    (canon / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    assert replay(CASE_ID, canon) is False


# 6 --------------------------------------------------------------------------
def test_oracle_not_leaked():
    """Sealed oracle literals must not appear anywhere in the canonical
    artifact tree; oracle/ is not on any target/judge code path."""
    assert ORACLE.exists(), "sealed oracle must exist (it is the ground truth)"
    oracle = json.loads(ORACLE.read_text())
    literals = [
        oracle["true_cause"],
        oracle["seeded_fault"],
        oracle["fault_marker"],
        "retrieval_omission",
        "14-day-stale-top1",
    ]
    canon = CANONICAL
    assert canon.exists(), f"canonical run missing: {canon} (generate before full gate)"
    scanned = 0
    for p in canon.rglob("*"):
        if p.is_file():
            scanned += 1
            text = p.read_text(errors="ignore")
            for lit in literals:
                assert lit not in text, f"oracle literal {lit!r} leaked into {p}"
    assert scanned > 0, "canonical artifact tree is empty"
    # The target/judge modules must not load the oracle file. (Docstrings
    # may mention the concept; only the concrete file reference counts.)
    for mod in ("frozen_backend.py", "executor.py", "case.py"):
        src = Path("src/repliclaw/counterfactual") / mod
        assert "oracle.json" not in src.read_text(), f"{mod} references the oracle file"


# 7 --------------------------------------------------------------------------
def test_determinism_across_seeds(case, interventions):
    """Seed is recorded for live-target parity; the deterministic backend's
    output is seed-invariant."""
    iv = interventions["I_R_retrieval_fix"]
    r0 = run_case(case, iv, seed=0)
    r7 = run_case(case, iv, seed=7)
    assert r0.seed == 0 and r7.seed == 7
    assert r0.target_output == r7.target_output
    assert r0.judgment == r7.judgment
    assert r0.config_sha256 == r7.config_sha256
