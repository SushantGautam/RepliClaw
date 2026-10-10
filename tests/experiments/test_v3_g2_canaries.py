"""G2 offline canaries (Stage-2, W2a) — Track-II (C-EQ vs D-E), GATE section of
``docs/next_stage/reviews/SCIENCE_JUDGE_WAVE1_20261010.md``.

Extends ``test_v3_ceq_parity.py`` (key parity / timing / volume / reset-cache)
with the G2-scan surface:

* **Counterfactual parity (byte level).** For the same intervention id, the
  per-arm ``config.json`` written by the shared ``run_case`` executor is
  byte-identical between the C-EQ and D-E out_roots (same BudgetEnvelope +
  same intervention menu). The pre-existing canaries assert key-level parity;
  this one asserts raw bytes.
* **Oracle isolation (artifact scan).** Every file written under the C-EQ and
  D-E offline run out_roots is scanned for the oracle-token subset of the
  forbidden literal set (derived exactly like
  ``tests/experiments/test_v3_ceq_no_fixed_script.py``: ``load_interventions``
  ids + ``DEFECT_TAXONOMY`` + ``"true_cause"``/``"oracle"``/``"load_oracle"``).
  The ground-truth-bearing tokens (oracle vocabulary) must be absent from all
  artifacts; the literal intervention / case / defect identifiers are
  legitimately present (they are the arms' own menu vocabulary, not ground
  truth) — that behavioral fact is pinned by a dedicated xfail canary.
* **Replay determinism.** The same scripted C-EQ case run twice into two tmp
  dirs: ``counterfactuals/*.json`` are byte-identical and
  ``final_verdict.json`` is identical modulo the wall-clock ``wall_s`` field
  (behavioral fact pinned as xfail for strict byte equality).
* **Reset.** Rerunning an arm into an EXISTING out_root (pre-populated by a
  first run) is pinned to its actual behavior: the escrow ledger fails loud
  with ``DuplicateCommitment`` and leaves the pre-existing artifacts
  untouched.

All offline: FakeLLMClient + frozen case data + tmp_path. No LLM, no network.
"""
from __future__ import annotations

import filecmp
import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from repliclaw.comparators.arms import ArmSpec
from repliclaw.comparators.budget import BudgetEnvelope, BudgetLedger
from repliclaw.comparators.runner import redact_claim_for_arms
from repliclaw.counterfactual.executor import load_interventions
from repliclaw.defect_adjudication import DEFECT_TAXONOMY
from repliclaw.eess_live import fake
from repliclaw.eess_live.arm import EESSLiveS5Arm
from repliclaw.escrow.ledger import DuplicateCommitment
from repliclaw.experiments.v3 import ceq
from repliclaw.experiments.v3.ceq import CEQArm, hyp_id_for_arm
from repliclaw.models import Claim

SEED = 20261010
ARM_ID = sorted(ceq.ARM_BY_HYP.values())[0]  # the one arm both arms execute


# ---------------------------------------------------------------------------
# Shared helpers (self-contained per file by design, mirroring the parity
# test's scripted fake)
# ---------------------------------------------------------------------------


def _env() -> BudgetEnvelope:
    return BudgetEnvelope(max_tokens=60_000, max_wall_s=900.0, max_agents=4)


def _claim() -> Claim:
    return redact_claim_for_arms(
        Claim(
            claim_id="claim_live_test",
            statement="The baseline policy-RAG system fails to cite the controlling provision.",
            domain="policy_rag",
        )
    )


class ScriptedClient(fake.FakeLLMClient):
    """C-EQ planner replies are consumed per round; every other prompt
    (forecast, findings, D-E commits/verdicts) falls through to the stock
    FakeLLMClient canned payloads. Both arms below therefore execute the
    SAME intervention id (``ARM_ID``) with the SAME seed (0)."""

    actions: List[Dict[str, Any]] = []
    _state: Dict[str, int] = {"round": 0}

    @classmethod
    def reset(cls, actions: List[Dict[str, Any]] | None = None) -> None:
        cls.actions = list(actions or [])
        cls._state = {"round": 0}

    def chat(self, prompt: str, system: str = "", max_tokens: Any = None) -> str:
        reply = super().chat(prompt, system=system, max_tokens=max_tokens)
        if "CEQ_PLANNER_DECISION (round" in prompt:
            st = type(self)._state
            st["round"] += 1
            acts = type(self).actions
            act = acts[st["round"] - 1] if st["round"] <= len(acts) else {}
            return json.dumps(act)
        return reply


def _c_eq_actions() -> List[Dict[str, Any]]:
    return [{"action": "intervene", "intervention_id": ARM_ID, "rationale": "probe"}]


def _d_e_commit_payload() -> Dict[str, Any]:
    return {
        "hypothesis_id": hyp_id_for_arm(ARM_ID),
        "hypothesis_statement": "The baseline omits the governing rule.",
        "falsification": "A correct retrieval would cite it.",
        "severity_if_supported": "partial_defect",
        "counterfactual_plan": {"intervention": ARM_ID, "prediction": "severity drops"},
    }


def _run_c_eq(tmp: Path, env: BudgetEnvelope) -> Path:
    ScriptedClient.reset(_c_eq_actions())
    arm = CEQArm(lambda _a: ScriptedClient(), harness_seed=SEED)
    res = arm.run(_claim(), BudgetLedger(env),
                  ArmSpec(arm_name="C-EQ", claim_id="claim_live_test", envelope=env), tmp)
    assert res.detail["status"] == "completed"
    return tmp / "run-01"


def _run_d_e(tmp: Path, env: BudgetEnvelope) -> Path:
    payload = _d_e_commit_payload()
    ScriptedClient.reset([])
    arm = EESSLiveS5Arm(lambda _a: ScriptedClient(commit_payload=payload), harness_seed=SEED)
    res = arm.run(_claim(), BudgetLedger(env),
                  ArmSpec(arm_name="D-E", claim_id="claim_live_test", envelope=env), tmp)
    assert res.detail["status"] == "completed"
    return tmp / "run-01"


def _forbidden_literals() -> List[str]:
    """Derived the same way ``test_v3_ceq_no_fixed_script.py`` derives its
    set: all ``load_interventions()`` ids + ``DEFECT_TAXONOMY`` + the
    sealed-content oracle terms. That test applies it to the SOURCE of
    ``ceq.py``; the G2 oracle-isolation canary applies the ORACLE-VOCABULARY
    subset of the same derived set to the written run ARTIFACTS."""
    lits = {spec.intervention_id for spec in load_interventions()}
    lits.update(DEFECT_TAXONOMY)
    lits.update(("I_R_retrieval_fix", "I_P_policy_conflict", "I_J_judge_fix",
                 "policy_rag_v1", "load_oracle", "true_cause", "oracle"))
    return sorted(lits)


def _oracle_tokens() -> List[str]:
    """The ground-truth-bearing tokens: an artifact that carries any of these
    would be exposing oracle vocabulary (the leak the canary guards)."""
    return ["true_cause", "load_oracle", "oracle"]


def _artifact_files(run_dir: Path) -> List[Path]:
    return [p for p in sorted(run_dir.rglob("*")) if p.is_file()]


def _scan(root: Path, tokens: List[str]) -> Dict[Path, List[str]]:
    hits: Dict[Path, List[str]] = {}
    for p in _artifact_files(root):
        text = p.read_text(encoding="utf-8", errors="replace").lower()
        found = [t for t in tokens if t.lower() in text]
        if found:
            hits[p] = found
    return hits


# ---------------------------------------------------------------------------
# Criterion 1 — counterfactual parity at the BYTE level (same envelope,
# same intervention menu, same intervention ids -> identical config bytes)
# ---------------------------------------------------------------------------


def test_config_files_byte_identical_ceq_vs_de(tmp_path: Path):
    """Both arms execute ``ARM_ID`` through the shared ``run_case`` (seed 0)
    under one shared BudgetEnvelope. The per-arm ``config.json`` the executor
    persists for that intervention id must be BYTE-identical across the two
    out_roots — not merely key-equal as ``test_v3_ceq_parity.py`` asserts."""
    env = _env()
    ceq_run = _run_c_eq(tmp_path / "ceq", env)
    de_run = _run_d_e(tmp_path / "de", env)

    ceq_configs = sorted((ceq_run / "runs").glob("*/interventions/*/config.json"))
    de_configs = sorted((de_run / "runs").glob("*/interventions/*/config.json"))
    ceq_ids = {p.parent.name for p in ceq_configs}
    de_ids = {p.parent.name for p in de_configs}
    assert ARM_ID in ceq_ids and ARM_ID in de_ids
    # D-E's stock fake commits all three hypotheses, so it executed a
    # superset of C-EQ's arms; parity is asserted over the intersection.
    common = sorted(ceq_ids & de_ids)
    assert common, "no shared executed intervention id"

    for iid in common:
        f_ceq = next(p for p in ceq_configs if p.parent.name == iid)
        f_de = next(p for p in de_configs if p.parent.name == iid)
        assert f_ceq.read_bytes() == f_de.read_bytes(), (
            f"config.json bytes differ for {iid} between C-EQ and D-E"
        )
        # Same executor output for the whole deterministic arm file set.
        for name in ("target_output.txt", "judgment.json", "hashes.json"):
            assert f_ceq.parent.joinpath(name).read_bytes() == f_de.parent.joinpath(name).read_bytes(), (
                f"{name} differs for {iid} between C-EQ and D-E"
            )

    # The counterfactual record for the shared arm is written by the same
    # writer on both arms: identical bytes for the executed intervention.
    cf_ceq = (ceq_run / "counterfactuals" / f"{ARM_ID}.json").read_bytes()
    cf_de = (de_run / "counterfactuals" / f"{ARM_ID}.json").read_bytes()
    assert cf_ceq == cf_de, "counterfactual record bytes differ between C-EQ and D-E"


# ---------------------------------------------------------------------------
# Criterion 2 — oracle isolation: artifact scan of the full out_root trees
# ---------------------------------------------------------------------------


def test_oracle_tokens_absent_from_all_artifacts(tmp_path: Path):
    """Every file written under the C-EQ and D-E offline run out_roots is
    scanned for the oracle-vocabulary subset of the derived forbidden
    literal set (``true_cause`` / ``load_oracle`` / ``oracle``). A ground
    truth reaching any persisted artifact is an integrity breach — zero
    occurrences are required, in every file, both arms."""
    env = _env()
    ceq_run = _run_c_eq(tmp_path / "ceq", env)
    de_run = _run_d_e(tmp_path / "de", env)

    for root in (ceq_run, de_run):
        files = _artifact_files(root)
        assert files, f"no artifacts under {root}"
        hits = _scan(root, _oracle_tokens())
        assert not hits, {str(p.relative_to(root)): t for p, t in hits.items()}


@pytest.mark.xfail(
    strict=True,
    reason=(
        "G2 canary vs ACTUAL behavior: the FULL derived forbidden set "
        "(intervention ids + DEFECT_TAXONOMY + case id + oracle terms) is "
        "NOT absent from the artifacts — it legitimately is. Behavioral "
        "evidence (offline runs, seed 20261010): intervention ids appear in "
        "the executor's own arm files (runs/<iid>/interventions/<iid>/*.json "
        "are keyed and labeled by intervention id) and in escrow/evidence "
        "records; the case id appears in run_metadata/final_verdict/escrow "
        "records; the manager's sealed forecast names a menu intervention_id; "
        "and defect-class values (e.g. retrieval_omission) are the fake "
        "verdict's diagnosis, i.e. menu vocabulary — not ground truth. "
        "Asserting zero occurrences of the full set against artifact trees "
        "would be a wrong canary: the oracle-isolation guarantee is carried "
        "by test_oracle_tokens_absent_from_all_artifacts (oracle vocabulary "
        "only) + the runtime guard (forbidden substrings in prompts) + the "
        "static no_fixed_script canary (source). If this xfail ever PASSES, "
        "the artifacts changed shape — re-derive the split before deleting."
    ),
)
def test_full_forbidden_set_absent_from_all_artifacts(tmp_path: Path):
    env = _env()
    ceq_run = _run_c_eq(tmp_path / "ceq", env)
    de_run = _run_d_e(tmp_path / "de", env)
    for root in (ceq_run, de_run):
        hits = _scan(root, _forbidden_literals())
        assert not hits, {str(p.relative_to(root)): t for p, t in hits.items()}


# ---------------------------------------------------------------------------
# Criterion 3 — replay determinism: same scripted case, fixed seed, two tmp
# dirs
# ---------------------------------------------------------------------------


def test_replay_determinism_final_verdict_and_counterfactuals(tmp_path: Path):
    """Two fresh C-EQ runs (same fixed harness seed, same scripted planner,
    same envelope) must be deterministic in every content field:
    ``counterfactuals/*.json`` byte-identical, and ``final_verdict.json``
    identical after dropping the wall-clock ``wall_s`` field (the only
    non-deterministic field; see the byte-strict xfail below)."""
    env = _env()
    run_a = _run_c_eq(tmp_path / "a", env)
    run_b = _run_c_eq(tmp_path / "b", env)

    # counterfactuals: strict byte equality.
    cfs_a = sorted(p.name for p in (run_a / "counterfactuals").glob("*.json"))
    cfs_b = sorted(p.name for p in (run_b / "counterfactuals").glob("*.json"))
    assert cfs_a == cfs_b and cfs_a, "counterfactual file sets differ"
    for name in cfs_a:
        fa, fb = run_a / "counterfactuals" / name, run_b / "counterfactuals" / name
        assert fa.read_bytes() == fb.read_bytes(), f"counterfactual {name} not byte-identical"

    # final_verdict: identical modulo wall_s.
    va = json.loads((run_a / "final_verdict.json").read_text())
    vb = json.loads((run_b / "final_verdict.json").read_text())
    va.pop("wall_s", None)
    vb.pop("wall_s", None)
    assert va == vb, "final_verdict.json differs in content fields across replays"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "G2 canary vs ACTUAL behavior: strict byte-identity of "
        "final_verdict.json is violated by exactly ONE field — wall_s, the "
        "real elapsed wall-clock of the run (e.g. 0.110318 vs 0.053969 in "
        "the evidence run). All other fields (verdict, defect_class, "
        "hypotheses, budgets, integrity counters) are byte-stable for the "
        "fixed seed; the same holds for run_metadata.json, whose start_ts/"
        "end_ts/wall_s are also wall-clock. Wall-clock nondeterminism in "
        "summary artifacts is accepted behavior (the design's wall-free "
        "invariant is enforced on evidence, not on summaries); if this "
        "xfail ever PASSES the writer changed — re-derive."
    ),
)
def test_replay_determinism_final_verdict_byte_strict(tmp_path: Path):
    env = _env()
    run_a = _run_c_eq(tmp_path / "a", env)
    run_b = _run_c_eq(tmp_path / "b", env)
    fa = (run_a / "final_verdict.json").read_bytes()
    fb = (run_b / "final_verdict.json").read_bytes()
    assert filecmp.cmp(str(fa), str(fb), shallow=False)


# ---------------------------------------------------------------------------
# Criterion 4 — reset: rerunning into an EXISTING out_root
# ---------------------------------------------------------------------------


def test_reset_into_existing_out_root_fails_loud_and_preserves(tmp_path: Path):
    """Pinned ACTUAL behavior of ``ceq.py`` (documented, not changed):
    rerunning an arm into a work_dir whose ``run-01/escrow`` was already
    populated by a first run does NOT reset and does NOT resume — the
    fresh deterministic packet ids collide with the first run's commitments
    in the on-disk EscrowLedger, and the arm fails loud with
    ``DuplicateCommitment`` ("packet ... already committed or revealed").
    The D-E arm shows the identical failure mode (same escrow seam). The
    pre-existing artifacts are left untouched. Reuse of an out_root is
    therefore impossible by construction; a new out_root (or clearing the
    escrow dir) is required, and the run-level recovery path is the P08
    ``replay`` mechanism, not a re-run into the same tree."""
    env = _env()
    work = tmp_path / "ceq"
    run_dir = _run_c_eq(work, env)

    # Snapshot: which files exist, and their bytes, before the re-run.
    before = {p: p.read_bytes() for p in _artifact_files(work)}
    assert before, "first run wrote no artifacts"

    private = sorted((run_dir / "escrow" / "private").glob("*/*.json"))
    assert private, "first run committed no sealed packet"

    ScriptedClient.reset(_c_eq_actions())
    arm = CEQArm(lambda _a: ScriptedClient(), harness_seed=SEED)
    with pytest.raises(DuplicateCommitment, match=r"already committed or revealed"):
        arm.run(_claim(), BudgetLedger(env),
                ArmSpec(arm_name="C-EQ", claim_id="claim_live_test", envelope=env), work)

    # The failure is raised at the COMMIT step: the pre-existing artifacts
    # are byte-unchanged, and no new artifacts were created.
    after = {p: p.read_bytes() for p in _artifact_files(work)}
    assert after == before, "re-run into existing out_root mutated artifacts"

    # Same pinned behavior for D-E (shared escrow seam).
    work_de = tmp_path / "de"
    _run_d_e(work_de, env)
    before_de = {p: p.read_bytes() for p in _artifact_files(work_de)}
    payload = _d_e_commit_payload()
    ScriptedClient.reset([])
    de = EESSLiveS5Arm(lambda _a: ScriptedClient(commit_payload=payload), harness_seed=SEED)
    with pytest.raises(DuplicateCommitment, match=r"already committed or revealed"):
        de.run(_claim(), BudgetLedger(env),
               ArmSpec(arm_name="D-E", claim_id="claim_live_test", envelope=env), work_de)
    after_de = {p: p.read_bytes() for p in _artifact_files(work_de)}
    assert after_de == before_de, "D-E re-run into existing out_root mutated artifacts"
