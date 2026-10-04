"""P08 runner CLI acceptance tests.

Every test runs through ``python -m repliclaw.comparators.runner``'s in-process
``main()`` with the ``FakeLLMClient`` (``--client-factory fake``); no live LLM
API key, no network. Covers the four recovery defects from the dead worker's
WIP plus the task-spec acceptance list:

* R1 — the ``tox21_ar_agonist`` secondary case resolves (claim built from the
  case docstring, never importing the RDKit-dependent case module);
* R2 — every arm writes the full contract run layout under ``<out>/run-01``;
* R3 — C1 same-task: one shared claim statement and ONE envelope sha256 across
  all arms' ``run_metadata.json``;
* R4 — ``tox21`` + a live arm exits **2** with a clean refusal message (never
  an unhandled exception / exit 1).

A8 (RC-1, executor parity) adaptation, DEFECT C1 (case-conditional): S0/S3/S4
are LIVE arms on the PRIMARY case (policy_rag_v1) — the P1 pair and RQ2
comparators must run the same live-LLM executor as S5, so they record
``model="fake-v1"``/``offline_arm=false`` with the fake client. But they are
live-ONLY on the primary: on the secondary no-LLM case (``tox21_ar_agonist``)
they run OFFLINE (deterministic, exit 0) — that is the frozen v1.1 RQ4/P4
sub-study, which pre-dates A8. Only ``eess_offline`` is offline on BOTH cases.
The live-ONLY arms S5/A1/A3 refuse the no-LLM ``tox21`` secondary case with a
clean exit 2 (the A8/v1.1-H secondary refusal).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List

import pytest

from repliclaw.comparators import case_loader
from repliclaw.comparators.runner import main

# A8 (RC-1): only eess_offline is a purely offline arm. S0/S3/S4 are now live
# (executor parity with S5); they run on the live-LLM path with the fake client.
OFFLINE_ARMS = ["eess_offline"]
LIVE_STRATEGY_ARMS = ["S0", "S3", "S4"]  # newly live (A8): comparators arms + LLM factory
LIVE_ARMS = ["S5", "A1", "A3"]
LIVE_ALL = LIVE_STRATEGY_ARMS + LIVE_ARMS  # all six primary arms are live (A8)
CONTRACT_FILES = (
    "final_verdict.json",
    "budget_ledger.json",
    "traces.jsonl",
    "run_metadata.json",
)

# Volatile fields stripped before the deterministic-rerun comparison.
STRIP_KEYS = {
    "start_ts",
    "end_ts",
    "wall_s",
    "ts",
    "published_at",
    "proposed_at",
    "committed_at",
    "created_at",
}


def run_cli(
    arm: str,
    case: str,
    *extra: str,
    monkeypatch: pytest.MonkeyPatch,
    out: Path,
) -> int:
    """Run the CLI in-process (main()); returns the exit code it would raise.

    ``REPLICLAW_LLM_ALLOW_LIVE`` is always cleared so the live-client gate
    cannot be bypassed by ambient environment.
    """
    monkeypatch.delenv("REPLICLAW_LLM_ALLOW_LIVE", raising=False)
    return main(["--arm", arm, "--case", case, "--out", str(out), *extra])


def run_argv(
    argv: List[str],
    monkeypatch: pytest.MonkeyPatch,
) -> int:
    monkeypatch.delenv("REPLICLAW_LLM_ALLOW_LIVE", raising=False)
    return main(argv)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _strip(o: Any) -> Any:
    if isinstance(o, dict):
        return {k: _strip(v) for k, v in o.items() if k not in STRIP_KEYS}
    if isinstance(o, list):
        return [_strip(x) for x in o]
    return o


def normalized_tree(root: Path) -> dict:
    """All JSON/JSONL artifacts under root, normalized for determinism diffs."""
    out = {}
    for p in sorted(Path(root).rglob("*")):
        if not p.is_file() or p.suffix not in (".json", ".jsonl"):
            continue
        text = p.read_text(encoding="utf-8")
        if p.suffix == ".jsonl":
            content = [
                _strip(json.loads(line))
                for line in text.splitlines()
                if line.strip()
            ]
        else:
            content = _strip(json.loads(text))
        out[str(p.relative_to(root))] = content
    return out


# ---------------------------------------------------------------------------
# R2 — the purely offline arm (eess_offline), end-to-end, full contract layout
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("arm", OFFLINE_ARMS)
def test_cli_offline_arm_writes_contract_run(arm: str, tmp_path: Path, monkeypatch):
    out = tmp_path / arm
    code = run_cli(arm, "policy_rag", monkeypatch=monkeypatch, out=out)
    assert code == 0, f"offline arm {arm} should complete"

    run_dir = out / "run-01"
    for name in CONTRACT_FILES:
        assert (run_dir / name).is_file(), f"{name} missing for {arm}"

    fv = read_json(run_dir / "final_verdict.json")
    meta = read_json(run_dir / "run_metadata.json")
    ledger = read_json(run_dir / "budget_ledger.json")

    assert fv["schema"] == "p08.final_verdict/1"
    assert fv["case_id"] == "policy_rag_v1"
    assert fv["status"] == "completed"
    assert fv["harness_seed"] == 20261010
    assert meta["harness_seed"] == 20261010
    assert meta["status"] == "completed"
    assert meta["tree_sha"] not in ("", "unknown")
    # Purely offline: deterministic model, no live endpoint.
    assert meta["model"] == "deterministic" and meta["endpoint"] == "offline"
    assert meta["offline_arm"] is True

    # No sealed-truth leakage into arm-side artifacts.
    assert "reference_truth" not in json.dumps(fv)
    assert "reference_truth" not in json.dumps(ledger)

    # Declared offline accounting: every call usage_present=true.
    assert ledger["envelope"]["max_tokens"] == 60_000
    assert all(c["usage_present"] for c in ledger["calls"])

    # C1 hash consistency WITHIN the run: fv == ledger == metadata.
    assert fv["envelope_sha256"] == ledger["envelope"]["sha256"]
    assert fv["envelope_sha256"] == meta["envelope_sha256"]


# ---------------------------------------------------------------------------
# R2 (A8) — the newly-live S0/S3/S4 strategy arms write the SAME contract
# layout, but with REAL (fake-client) LLM usage and offline_arm=false.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("arm", LIVE_STRATEGY_ARMS)
def test_cli_live_strategy_arm_writes_contract_run(
    arm: str, tmp_path: Path, monkeypatch
):
    out = tmp_path / arm
    code = run_cli(
        arm, "policy_rag", "--client-factory", "fake",
        monkeypatch=monkeypatch, out=out,
    )
    assert code == 0, f"live strategy arm {arm} should complete"

    run_dir = out / "run-01"
    for name in CONTRACT_FILES:
        assert (run_dir / name).is_file(), f"{name} missing for {arm}"

    fv = read_json(run_dir / "final_verdict.json")
    meta = read_json(run_dir / "run_metadata.json")
    ledger = read_json(run_dir / "budget_ledger.json")

    assert fv["schema"] == "p08.final_verdict/1"
    assert fv["case_id"] == "policy_rag_v1"
    assert fv["status"] == "completed"
    assert fv["harness_seed"] == 20261010
    assert meta["harness_seed"] == 20261010
    assert meta["status"] == "completed"
    assert meta["tree_sha"] not in ("", "unknown")
    # A8: these arms are now LIVE — fake client identity, not deterministic.
    assert meta["model"] == "fake-v1" and meta["endpoint"] == "http://fake.invalid/v1"
    assert meta["offline_arm"] is False
    assert meta["client_factory"] == "fake"

    # No sealed-truth leakage into arm-side artifacts.
    assert "reference_truth" not in json.dumps(fv)
    assert "reference_truth" not in json.dumps(ledger)

    # Real (fake-client) usage accounting, NOT the offline nominal cost.
    assert ledger["envelope"]["max_tokens"] == 60_000
    assert all(c["usage_present"] for c in ledger["calls"])

    # C1 hash consistency WITHIN the run: fv == ledger == metadata.
    assert fv["envelope_sha256"] == ledger["envelope"]["sha256"]
    assert fv["envelope_sha256"] == meta["envelope_sha256"]

    # R2 root cause: S3's follow-up deploys a 4th agent and still completes
    # (legal under the A7 4-agent envelope, now honestly recorded).
    if arm == "S3":
        assert fv["n_agents"] == 4


def test_cli_eess_offline_deterministic_tokens(
    tmp_path: Path, monkeypatch
):
    out = tmp_path / "eess_offline"
    assert run_cli("eess_offline", "policy_rag", monkeypatch=monkeypatch, out=out) == 0
    fv = read_json(out / "run-01" / "final_verdict.json")
    assert fv["status"] == "completed"
    assert fv["verdict"] == "supported"
    assert fv["total_tokens"] == 3_500  # one deterministic offline arm cost
    assert fv["n_agents"] == 3


# ---------------------------------------------------------------------------
# R3 — C1 same-task: ONE claim, ONE envelope sha256 across ALL arms
# ---------------------------------------------------------------------------


def test_c1_same_claim_statement_for_every_arm():
    a = case_loader.load_arm_claim("policy_rag")
    b = case_loader.load_arm_claim("policy_rag")
    c = case_loader.load_arm_claim("tox21_ar_agonist")
    assert a.statement == b.statement and a.claim_id == b.claim_id
    assert a.statement and c.statement and a.statement != c.statement


def test_c1_all_arms_share_one_envelope_sha(
    tmp_path: Path, monkeypatch
):
    """A8: all SEVEN arms (six live + eess_offline) share one envelope hash.

    The six live arms (S0/S3/S4/S5/A1/A3) run with the fake client; the single
    offline arm (eess_offline) runs deterministically. Every one must carry the
    SAME content-addressed envelope sha256 (matched-budget precondition).
    """
    seen = set()
    for arm in OFFLINE_ARMS:
        out = tmp_path / arm
        assert run_cli(arm, "policy_rag", monkeypatch=monkeypatch, out=out) == 0
        meta = read_json(out / "run-01" / "run_metadata.json")
        fv = read_json(out / "run-01" / "final_verdict.json")
        assert meta["envelope_sha256"] == fv["envelope_sha256"]
        seen.add(meta["envelope_sha256"])
    for arm in LIVE_ALL:
        out = tmp_path / arm
        assert run_cli(
            arm, "policy_rag", "--client-factory", "fake",
            monkeypatch=monkeypatch, out=out,
        ) == 0
        meta = read_json(out / "run-01" / "run_metadata.json")
        fv = read_json(out / "run-01" / "final_verdict.json")
        assert meta["envelope_sha256"] == fv["envelope_sha256"]
        seen.add(meta["envelope_sha256"])
    assert len(seen) == 1, f"arms did not share one envelope hash: {seen}"


# ---------------------------------------------------------------------------
# Live arms (fake client): complete, share the hash, deterministic rerun
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("arm", LIVE_ARMS)
def test_cli_live_arm_fake_client_completes(arm: str, tmp_path: Path, monkeypatch):
    out = tmp_path / arm
    code = run_cli(
        arm, "policy_rag", "--client-factory", "fake",
        monkeypatch=monkeypatch, out=out,
    )
    assert code == 0, f"live arm {arm} (fake client) should complete"

    run_dir = out / "run-01"
    for name in CONTRACT_FILES:
        assert (run_dir / name).is_file()
    assert (run_dir / "counterfactuals").is_dir()

    meta = read_json(run_dir / "run_metadata.json")
    assert meta["status"] == "completed"
    assert meta["offline_arm"] is False
    assert meta["client_factory"] == "fake"
    assert meta["model"] == "fake-v1"
    assert meta["endpoint"] == "http://fake.invalid/v1"
    # D-10 frozen pin recorded in run_metadata.
    assert meta["lam"] == 0.5
    assert meta["mu"] == 0.5
    assert meta["max_cycles"] == 6
    assert meta["lease_ttl_s"] == 120.0
    fv = read_json(run_dir / "final_verdict.json")
    assert fv["status"] == "completed"
    assert all(c["usage_present"] for c in read_json(run_dir / "budget_ledger.json")["calls"])


def test_c1_live_arms_share_one_envelope_hash(
    tmp_path: Path, monkeypatch
):
    """A8: all SIX live arms (S0/S3/S4/S5/A1/A3) share one envelope hash."""
    seen = set()
    for arm in LIVE_ALL:
        out = tmp_path / arm
        assert run_cli(
            arm, "policy_rag", "--client-factory", "fake",
            monkeypatch=monkeypatch, out=out,
        ) == 0
        meta = read_json(out / "run-01" / "run_metadata.json")
        seen.add(meta["envelope_sha256"])
    assert len(seen) == 1


def test_live_rerun_is_deterministic(tmp_path: Path, monkeypatch):
    r1 = tmp_path / "r1"
    r2 = tmp_path / "r2"
    argv = ["--arm", "S5", "--case", "policy_rag", "--client-factory", "fake"]
    assert run_argv(argv + ["--out", str(r1)], monkeypatch) == 0
    assert run_argv(argv + ["--out", str(r2)], monkeypatch) == 0

    t1 = normalized_tree(r1 / "run-01")
    t2 = normalized_tree(r2 / "run-01")
    assert set(t1) == set(t2)
    diffs = {k for k in t1 if t1[k] != t2[k]}
    assert not diffs, f"non-deterministic artifacts: {sorted(diffs)}"
    assert t1["run_metadata.json"] == t2["run_metadata.json"]


# ---------------------------------------------------------------------------
# D-10 frozen pin: --assert-frozen
# ---------------------------------------------------------------------------


def test_assert_frozen_passes_on_frozen_path(tmp_path: Path, monkeypatch):
    out = tmp_path / "frozen_ok"
    code = run_cli(
        "S5", "policy_rag", "--client-factory", "fake", "--assert-frozen",
        monkeypatch=monkeypatch, out=out,
    )
    assert code == 0
    assert (out / "run-01" / "final_verdict.json").is_file()


def test_assert_frozen_fails_before_any_run(
    tmp_path: Path, monkeypatch, capfd
):
    """Deviation is caught BEFORE the arm runs: no run dir, exit 2, reason
    printed to stderr (R: --assert-frozen fails non-zero on max_cycles=2)."""
    out = tmp_path / "frozen_bad"
    with pytest.raises(SystemExit) as exc:
        run_cli(
            "S5", "policy_rag", "--client-factory", "fake",
            "--assert-frozen", "--max-cycles", "2",
            monkeypatch=monkeypatch, out=out,
        )
    assert exc.value.code == 2
    err = capfd.readouterr().err
    assert "max_cycles=2" in err
    assert "frozen pin" in err
    assert not out.exists()  # checked before any run


# ---------------------------------------------------------------------------
# case_loader: oracle-path guard
# ---------------------------------------------------------------------------


def test_case_loader_never_opens_oracle(monkeypatch):
    oracle_path = (
        case_loader.repo_root()
        / "experiments" / "policy_rag" / "oracle" / "oracle.json"
    )
    opened: List[Path] = []
    real_open = open

    def spy_open(file, *a, **k):
        try:
            opened.append(Path(str(file)).resolve())
        except OSError:
            pass
        return real_open(file, *a, **k)

    monkeypatch.setattr("builtins.open", spy_open)
    claim = case_loader.load_arm_claim("policy_rag")
    assert claim.statement
    for p in opened:
        assert "oracle" not in p.parts, f"oracle opened: {p}"
        assert p != oracle_path


def test_default_envelope_is_task_spec_values():
    env = case_loader.default_envelope("policy_rag")
    assert (env.max_tokens, env.max_wall_s, env.max_agents) == (60_000, 900.0, 4)
    assert env.sha256() == case_loader.default_envelope("tox21_ar_agonist").sha256()


# ---------------------------------------------------------------------------
# R1 + R4 — tox21 secondary case: resolves, refuses LLM arms with exit 2
# ---------------------------------------------------------------------------


def test_tox21_secondary_case_resolves(monkeypatch):
    spec = case_loader.resolve_case("tox21_ar_agonist")
    assert spec.case_id == "tox21_ar_agonist"
    assert spec.secondary is True
    assert spec.oracle_path.name == "oracle.json"

    claim = case_loader.load_arm_claim("tox21_ar_agonist")
    stmt = claim.statement.lower()
    assert "functionalization" in stmt
    assert "logp" in stmt
    # Same-task guard: the rooted offline EESS slice refuses the secondary.
    with pytest.raises(case_loader.CaseNotSupportedError):
        case_loader.assert_same_task("eess_offline", spec, claim)


def test_cli_tox21_secondary_refuses_live_arms(
    tmp_path: Path, monkeypatch, capfd
):
    """R4: must be a CLEAN exit-2 refusal, never an unhandled exception."""
    out = tmp_path / "s5_tox21"
    code = run_cli(
        "S5", "tox21_ar_agonist", "--client-factory", "fake",
        monkeypatch=monkeypatch, out=out,
    )
    assert code == 2
    err = capfd.readouterr().err
    assert "no-LLM" in err
    assert not (out / "run-01").exists()


def test_cli_tox21_refuses_eess_offline(tmp_path: Path, monkeypatch, capfd):
    code = run_cli(
        "eess_offline", "tox21_ar_agonist",
        monkeypatch=monkeypatch, out=tmp_path / "eo",
    )
    assert code == 2
    assert "same-task" in capfd.readouterr().err


def test_cli_tox21_offline_arms_complete(tmp_path: Path, monkeypatch):
    """DEFECT C1 fix (frozen v1.1 RQ4/P4 no-LLM sub-study, restored): S0/S3/S4
    are live on the PRIMARY case only; on the secondary no-LLM case
    ``tox21_ar_agonist`` they run OFFLINE exactly as before — deterministic,
    exit 0, ``offline_arm=true``, ``model="deterministic"``."""
    for arm in ["S0", "S3", "S4"]:
        out = tmp_path / arm
        assert run_cli(arm, "tox21_ar_agonist", monkeypatch=monkeypatch, out=out) == 0
        meta = read_json(out / "run-01" / "run_metadata.json")
        assert meta["case_id"] == "tox21_ar_agonist"
        assert meta["status"] == "completed"
        # Offline executor on the secondary case (the frozen RQ4/P4 coverage).
        assert meta["model"] == "deterministic"
        assert meta["endpoint"] == "offline"
        assert meta["offline_arm"] is True
        assert meta["client_factory"] == "none"


# ---------------------------------------------------------------------------
# Refusals and gates
# ---------------------------------------------------------------------------


def test_unknown_arm_refused(tmp_path: Path, monkeypatch, capfd):
    code = run_cli("NOPE", "policy_rag", monkeypatch=monkeypatch, out=tmp_path)
    assert code == 2
    assert "unknown arm" in capfd.readouterr().err


def test_unknown_case_refused(tmp_path: Path, monkeypatch, capfd):
    code = run_cli("S0", "not_a_case", monkeypatch=monkeypatch, out=tmp_path)
    assert code == 2
    assert "case" in capfd.readouterr().err


def test_live_client_factory_requires_env(
    tmp_path: Path, monkeypatch, capfd
):
    code = run_cli(
        "S5", "policy_rag", "--client-factory", "live",
        monkeypatch=monkeypatch, out=tmp_path,
    )
    assert code == 2
    assert "REPLICLAW_LLM_ALLOW_LIVE" in capfd.readouterr().err


# ---------------------------------------------------------------------------
# usage-invalidation propagation (checklist item 7)
# ---------------------------------------------------------------------------


def test_live_usage_invalidation_propagates_to_status(
    tmp_path: Path, monkeypatch
):
    """A live arm whose endpoint reports no usage is INVALIDATED (void),
    never zero-filled: status=invalid_usage in final_verdict + run_metadata,
    exit code 3, and the ledger shows usage_present=false for the tripping
    call instead of a fabricated 0."""
    from repliclaw.eess_live import FakeLLMClient

    real_chat = FakeLLMClient.chat

    def chat_no_usage(self, prompt, system="You are a careful, quantitative scientific investigator.", max_tokens=None):
        bp, bc = self.usage.prompt_tokens, self.usage.completion_tokens
        response = real_chat(self, prompt, system=system, max_tokens=max_tokens)
        self.usage.prompt_tokens = bp
        self.usage.completion_tokens = bc
        self.usage.total_tokens = bp + bc
        return response

    monkeypatch.setattr(FakeLLMClient, "chat", chat_no_usage)
    out = tmp_path / "invalid"
    code = run_cli(
        "S5", "policy_rag", "--client-factory", "fake",
        monkeypatch=monkeypatch, out=out,
    )
    assert code == 3  # ran but void — not a refusal (2), not success (0)
    meta = read_json(out / "run-01" / "run_metadata.json")
    fv = read_json(out / "run-01" / "final_verdict.json")
    assert meta["status"] == "invalid_usage"
    assert fv["status"] == "invalid_usage"
    ledger = read_json(out / "run-01" / "budget_ledger.json")
    assert any(c["usage_present"] is False for c in ledger["calls"])


# ---------------------------------------------------------------------------
# PREREG-2026-10 v1.2 A6: CLI-level redaction (CODE-JUDGE-HARNESS item 3,
# post-merge extension — the CLI runs arms directly, bypassing
# ComparatorHarness.run, so it must redact evaluator truth itself)
# ---------------------------------------------------------------------------


def test_cli_redacts_evaluator_truth_before_arms(tmp_path: Path, monkeypatch):
    """A truth-bearing claim must never reach an arm's verdict or any artifact.

    Simulates a claim whose reference_truth/seeded_fault are populated and
    asserts the CLI redacts them (non-destructively) before construction:
    arm-side verdict cannot be truth-derived, and no artifact contains the
    truth marker.
    """
    out = tmp_path / "S5x"
    TRUTH_MARKER = "retrieval_omission_marker_test"
    original = case_loader.load_arm_claim

    def leaky_loader(case_id: str, root: Path):
        claim = original(case_id, root)
        return claim.model_copy(
            update={
                "reference_truth": TRUTH_MARKER,
                "seeded_fault": TRUTH_MARKER,
            }
        )

    monkeypatch.setattr(case_loader, "load_arm_claim", leaky_loader)
    assert run_cli("S0", "policy_rag", monkeypatch=monkeypatch, out=out) == 0

    # The original claim object must be untouched (non-mutating redaction).
    clean = original("policy_rag", Path("."))
    assert clean.reference_truth is None

    # No artifact may contain the truth marker (verdict leak would).
    blob = json.dumps(normalized_tree(out))
    assert TRUTH_MARKER not in blob


# ---------------------------------------------------------------------------
# envelope override flags
# ---------------------------------------------------------------------------


def test_envelope_override_flags(tmp_path: Path, monkeypatch):
    out = tmp_path / "S0x"
    assert (
        run_cli(
            "S0", "policy_rag",
            "--envelope-tokens", "12345",
            "--envelope-wall", "10",
            "--envelope-agents", "2",
            monkeypatch=monkeypatch, out=out,
        )
        == 0
    )
    meta = read_json(out / "run-01" / "run_metadata.json")
    assert meta["envelope"] == {
        "max_tokens": 12_345,
        "max_wall_s": 10.0,
        "max_agents": 2,
        "sha256": meta["envelope_sha256"],
    }
    # The overridden envelope must hash differently from the default one.
    assert meta["envelope_sha256"] != case_loader.default_envelope(
        "policy_rag"
    ).sha256()
