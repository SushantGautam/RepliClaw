"""P08/A6 — no-oracle-leak canary guard.

Implements the two-layer fix from CODE-JUDGE-HARNESS-20261008 item 3, on top of
PREREG-2026-10 v1.2 item A6 (test 1).

The sealed oracle (``experiments/policy_rag/oracle/oracle.json``) must be read
ONLY by the scorer (``src/repliclaw/p08/score.py``) and ONLY after sealing. An
arm-side path that lets evaluator/sealed truth reach a REPORTED verdict or an
arm artifact is a leakage blocker. The two arm-side paths locked down here:

  (a) the ``EESSArm._verdict`` ``claim.reference_truth`` fallback — an arm must
      never derive a reported verdict from evaluator/sealed truth; and
  (b) arm-side code must never OPEN the sealed oracle path.

The two-layer fix (CODE-JUDGE-HARNESS-20261008 item 3):
  * HARNESS layer — ``redact_claim_for_arms`` nulls ``claim.reference_truth``
    AND ``claim.seeded_fault`` (both attributes are reachable) before any arm is
    constructed, so an arm is constructible without ground truth;
  * FALLBACK layer — ``EESSArm._verdict`` returns the literal, truth-free
    ``"INCONCLUSIVE"`` when the slice yields no determined outcomes (the
    ``reference_truth`` fallback was removed).

Verdict-label vs schema-bound-conclusion mapping (documented per the judge's
item 3 note): the offline arm's OWN verdict field (``ArmResult.verdict_label``,
and the EESS fallback) is the ``VerdictLabel`` enum
``SUPPORTED|REFUTED|INCONCLUSIVE`` — so an undetermined offline slice reports
``INCONCLUSIVE``. That is a DISTINCT field from the schema-bound per-agent
``conclusion`` (``supported|refuted|uncertain``) that individual investigators
emit; on a no-signal claim that conclusion field stays ``"uncertain"``.
``"INCONCLUSIVE"`` does NOT break either schema (it is the canonical
abstain value of ``VerdictLabel``), so no cross-schema remap is required —
the mapping is simply "arm verdict_label=INCONCLUSIVE, investigator
conclusion=uncertain".

Covered here:
  * the EESSArm end-to-end must never emit the canary (artifact scan);
  * a LEAKY claim (canary ``reference_truth``) and a CLEAN (redacted) claim run
    through the redacting harness produce IDENTICAL verdicts — proving truth
    cannot reach the output;
  * the ``_verdict`` fallback (no determined outcomes) degrades to INCONCLUSIVE
    and never surfaces the canary or a real truth value;
  * the harness-layer redaction nulls both truth fields non-destructively;
  * a path guard: any ``open()``/``Path.open()`` targeting
    ``experiments/policy_rag/oracle/`` raises, and offline arms + ``run_slice``
    run clean under it;
  * a positive control proving the SCORER's sole oracle reader still works (we
    have not over-blocked the one legitimate reader).

No live LLM, no network, no API keys — offline hermetic arms only.
"""
from __future__ import annotations

import builtins
import json
from pathlib import Path
from typing import Any

import pytest

from repliclaw.comparators.arms import ArmSpec
from repliclaw.comparators.budget import BudgetEnvelope, BudgetLedger
from repliclaw.comparators.managers import EESSArm, SingleAgentBaseline
from repliclaw.comparators.runner import redact_claim_for_arms
from repliclaw.investigators import DeterministicInvestigator
from repliclaw.models import Claim

CANARY = "CANARY_ORACLE_LEAK_9f3a"
FIX = Path(__file__).resolve().parent / "fixtures"
_ORACLE_DIR = Path(__file__).resolve().parents[1] / "experiments" / "policy_rag" / "oracle"

# The canonical abstain labels in each of the two DISTINCT schemas.
ARM_VERDICT_INCONCLUSIVE = "INCONCLUSIVE"  # VerdictLabel enum (arm verdict_label)
CONCLUSION_UNCERTAIN = "uncertain"  # schema-bound per-agent investigator conclusion


def _det_factory(cfg: Any) -> DeterministicInvestigator:
    return DeterministicInvestigator(cfg)


def _claim(reference_truth: str, seeded_fault: str | None = None) -> Claim:
    """Build a fixture-backed claim whose evaluator-truth fields carry the
    supplied (canary or real) value(s)."""
    fx = json.loads((FIX / "clean_supported.json").read_text())
    c = fx["claim"]
    return Claim(
        claim_id=f"claim-a6-{abs(hash(reference_truth)) % 10**8}",
        statement=c["statement"],
        domain=c.get("domain", "general"),
        data=c.get("data"),
        reference_truth=reference_truth,
        seeded_fault=seeded_fault,
    )


def _envelope() -> BudgetEnvelope:
    return BudgetEnvelope(max_tokens=10_000, max_wall_s=30.0, max_agents=3)


def _run_eess_arm(claim: Claim, work_root: Path):
    """Run the offline EESSArm end-to-end (its harness entry point: the full
    ``run_slice`` lifecycle -> budget ledger -> verdict -> ArmResult)."""
    arm = EESSArm(_det_factory)
    env = _envelope()
    spec = ArmSpec(arm_name="eess", claim_id=claim.claim_id, envelope=env)
    result = arm.run(claim, BudgetLedger(env), spec, work_root)
    return result, work_root


def _scan_for_canary(work_root: Path, result: Any) -> list[str]:
    """Every file the arm wrote under ``work_root`` plus the in-memory
    ArmResult (verdict + detail). Returns the locations holding the canary
    (empty == no leak)."""
    hits: list[str] = []
    try:
        blob = json.dumps(result.to_dict(), ensure_ascii=False)
    except Exception:  # noqa: BLE001 - fall back to a coarse string form
        blob = str(result)
    if CANARY in blob:
        hits.append("<ArmResult>")
    for p in sorted(work_root.rglob("*")):
        if not p.is_file():
            continue
        try:
            if CANARY in p.read_text(encoding="utf-8", errors="ignore"):
                hits.append(str(p.relative_to(work_root)))
        except Exception:  # noqa: BLE001 - unreadable binary: skip, not a leak
            continue
    return hits


# ---------------------------------------------------------------------------
# 1. Canary never reaches an arm verdict or artifact (end-to-end)
# ---------------------------------------------------------------------------
def test_canary_in_no_arm_artifact_end_to_end(tmp_path: Path) -> None:
    """A canary carried in the claim's reference_truth must appear in NO arm
    artifact (final verdict, traces, budget ledger, run metadata, and every
    file written under the arm work dir)."""
    claim = _claim(CANARY)
    result, work_root = _run_eess_arm(claim, tmp_path)

    # The run really produced an arm verdict + on-disk artifacts (guard is
    # live, not vacuous).
    assert result.verdict_label in ("SUPPORTED", "REFUTED", ARM_VERDICT_INCONCLUSIVE)
    assert any(work_root.rglob("*")), "expected the arm to write artifacts"

    hits = _scan_for_canary(work_root, result)
    assert hits == [], f"canary leaked into arm artifact(s): {hits}"


# ---------------------------------------------------------------------------
# 2. The _verdict fallback (no determined outcomes) must not surface truth
# ---------------------------------------------------------------------------
def test_fallback_does_not_emit_canary_verdict() -> None:
    """With no determined EESS outcomes, the fallback must NOT emit the
    reference_truth canary as (or into) the reported verdict."""
    claim = _claim(CANARY)
    label, conf = EESSArm._verdict({}, claim)
    assert label == ARM_VERDICT_INCONCLUSIVE
    assert conf == 0.5
    assert CANARY not in label


def test_fallback_ignores_real_truth_value() -> None:
    """Regression for the REMOVED leak: a REAL oracle truth ("supported"/
    "refuted") with no determined outcomes used to produce a reported
    SUPPORTED/REFUTED. It must now degrade to the truth-free INCONCLUSIVE —
    a missing-outcome verdict is never sourced from sealed truth. The normal
    (determined-outcome) branch is unaffected."""
    assert EESSArm._verdict({}, _claim("supported")) == (ARM_VERDICT_INCONCLUSIVE, 0.5)
    assert EESSArm._verdict({}, _claim("refuted")) == (ARM_VERDICT_INCONCLUSIVE, 0.5)
    # determined outcomes still map as before:
    assert EESSArm._verdict({"a": {"outcome": "supported"}}, _claim("supported"))[0] == "SUPPORTED"
    assert EESSArm._verdict(
        {"a": {"outcome": "refuted"}, "b": {"outcome": "refuted"}}, _claim("supported")
    )[0] == "REFUTED"


# ---------------------------------------------------------------------------
# 3. Judge's stronger canary: LEAKY claim vs CLEAN (redacted) claim through the
#    redacting harness produce IDENTICAL verdicts (truth cannot reach output)
# ---------------------------------------------------------------------------
def test_leaky_vs_clean_claim_identical_verdict_end_to_end(tmp_path: Path) -> None:
    """A LEAKY claim (canary ``reference_truth``) and an otherwise-identical
    CLEAN claim (redacted) run through the redacting harness must return
    IDENTICAL verdicts. If the arm's output differed, truth were reaching the
    verdict — the leak channel is closed when it does not."""
    leaky = _claim(CANARY, seeded_fault=CANARY)
    clean = redact_claim_for_arms(leaky)
    # The redacting harness really stripped the truth before the arm saw it.
    assert clean.reference_truth is None
    assert clean.seeded_fault is None

    r_leaky, _ = _run_eess_arm(leaky, tmp_path / "leaky")
    r_clean, _ = _run_eess_arm(clean, tmp_path / "clean")

    # Identical arm verdict (label + confidence) regardless of the claim's
    # reference truth -> truth cannot reach the output.
    assert r_leaky.verdict_label == r_clean.verdict_label
    assert r_leaky.detail["confidence"] == r_clean.detail["confidence"]

    # And the canary is absent from BOTH arms' artifacts.
    for label, res, root in (("leaky", r_leaky, tmp_path / "leaky"),
                             ("clean", r_clean, tmp_path / "clean")):
        hits = _scan_for_canary(root, res)
        assert hits == [], f"canary leaked in {label} arm: {hits}"


def test_harness_redaction_nulls_both_truth_fields() -> None:
    """The harness-layer guard (CODE-JUDGE-HARNESS-20261008 item 3) nulls BOTH
    reachable truth fields — ``reference_truth`` AND ``seeded_fault`` —
    non-destructively (the caller's object is untouched), while preserving the
    statement/data the arm actually reasons over."""
    leaky = _claim(CANARY, seeded_fault="some_fault_tag")
    clean = redact_claim_for_arms(leaky)

    assert clean.reference_truth is None
    assert clean.seeded_fault is None
    # caller's object is NOT mutated (model_copy, not in-place):
    assert leaky.reference_truth == CANARY
    assert leaky.seeded_fault == "some_fault_tag"
    # the arm-facing fields are preserved:
    assert clean.statement == leaky.statement
    assert clean.data == leaky.data
    assert clean.claim_id == leaky.claim_id


# ---------------------------------------------------------------------------
# 4. Mapping documented: arm verdict_label=INCONCLUSIVE (VerdictLabel enum) vs
#    the DISTINCT schema-bound investigator conclusion=uncertain
# ---------------------------------------------------------------------------
def test_verdict_label_vs_conclusion_mapping() -> None:
    """Documents the CODE-JUDGE-HARNESS-20261008 item 3 label mapping:
    the offline arm's OWN verdict field is the ``VerdictLabel`` enum
    (``SUPPORTED|REFUTED|INCONCLUSIVE``) so an undetermined slice reports
    ``INCONCLUSIVE``; that is a DISTINCT field from the schema-bound per-agent
    ``conclusion`` (``supported|refuted|uncertain``), which a no-signal
    investigator emits as ``uncertain``. Both schemas stay intact (INCONCLUSIVE
    is the canonical abstain of VerdictLabel, so it breaks nothing)."""
    from repliclaw.models import InvestigatorConfig, InvestigatorRole, VerdictLabel

    # Arm-side: the fallback label is a valid VerdictLabel value (schema OK).
    assert EESSArm._verdict({}, _claim(CANARY))[0] == VerdictLabel.INCONCLUSIVE.value
    assert ARM_VERDICT_INCONCLUSIVE == VerdictLabel.INCONCLUSIVE.value

    # Investigator-side: a no-signal claim (no bundled data) yields the
    # schema-bound "uncertain" conclusion — a different field, left as-is (no
    # remap to INCONCLUSIVE). The canary is on this claim too, so this also
    # shows the investigator never echoes reference_truth into its conclusion.
    cfg = InvestigatorConfig(agent_id="no-signal", role=InvestigatorRole.ANALYST,
                             allowed_sources=["bundled_data"])
    no_signal = Claim(statement="no data", reference_truth=CANARY)
    finding = _det_factory(cfg).run(_ContextFor(no_signal))
    assert finding.get("conclusion") == CONCLUSION_UNCERTAIN
    assert CANARY not in json.dumps(finding, ensure_ascii=False)
    # The two schemas coexist: arm=INCONCLUSIVE, conclusion=uncertain.
    assert ARM_VERDICT_INCONCLUSIVE != CONCLUSION_UNCERTAIN


class _ContextFor:
    """Minimal stand-in for the isolation context (exposes ``.claim``)."""

    def __init__(self, claim: Claim):
        self.claim = claim


# ---------------------------------------------------------------------------
# 5. Path guard: arm-side code must never open the sealed oracle
# ---------------------------------------------------------------------------
def test_arm_side_never_opens_oracle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Monkeypatch built-in ``open`` / ``Path.open`` to raise on any path under
    ``experiments/policy_rag/oracle/``; then run offline arms + the offline
    EESS slice (``run_slice`` on a tmp dir) and assert the guard never fired
    (only the scorer may open the oracle)."""
    assert _ORACLE_DIR.is_dir(), "expected the sealed oracle dir to exist"
    oracle_prefix = str(_ORACLE_DIR)  # resolved, no trailing slash
    oracle_opened: list[str] = []  # recorded ONLY from arm/slice runs below

    def _check(p: Any) -> None:
        if p is None or isinstance(p, int):  # fd or non-path first arg
            return
        try:
            s = str(Path(p).resolve())
        except Exception:  # noqa: BLE001
            s = str(p)
        if s == oracle_prefix or s.startswith(oracle_prefix + "/") or ("policy_rag/oracle" in s):
            oracle_opened.append(s)
            raise AssertionError(f"arm-side code opened sealed oracle path: {s}")

    real_open = builtins.open
    real_path_open = Path.open

    def guarded_open(file, *a, **k):
        _check(file)
        return real_open(file, *a, **k)

    def guarded_path_open(self, *a, **k):
        _check(self)
        return real_path_open(self, *a, **k)

    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(Path, "open", guarded_path_open)

    # sanity: the guard is live — opening the oracle WOULD raise. Use a SEPARATE
    # detector from ``oracle_opened`` so the expected sanity failures don't
    # poison the arm/slice assertion that follows.
    sanity_hits: list[str] = []

    def _sanity(file, *a, **k):
        s = str(file)
        if "policy_rag/oracle" in s:
            sanity_hits.append(s)
            raise AssertionError("expected: oracle open blocked by guard")
        return real_open(file, *a, **k)

    monkeypatch.setattr(builtins, "open", _sanity)
    monkeypatch.setattr(Path, "open", lambda self, *a, **k: _sanity(self, *a, **k))
    with pytest.raises(AssertionError):
        open(_ORACLE_DIR / "oracle.json")  # type: ignore[call-overload]
    with pytest.raises(AssertionError):
        (_ORACLE_DIR / "oracle.json").open()  # type: ignore[call-overload]
    assert len(sanity_hits) == 2, f"guard did not fire as expected: {sanity_hits}"

    # restore the recording guard for the real arm/slice runs.
    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(Path, "open", guarded_path_open)

    # (i) the EESS comparator arm (full run_slice lifecycle), and
    result, _ = _run_eess_arm(_claim(CANARY), tmp_path / "eess_guard")
    assert result.verdict_label in ("SUPPORTED", "REFUTED", ARM_VERDICT_INCONCLUSIVE)

    # (ii) a strategy-based offline arm (the ArmRunner/run_strategy path used
    #     by the S0/S3/S4 comparators).
    sa_claim = _claim(CANARY)
    sa_env = _envelope()
    sa_res = SingleAgentBaseline(_det_factory).run(
        sa_claim,
        BudgetLedger(sa_env),
        ArmSpec(arm_name="single_agent", claim_id=sa_claim.claim_id, envelope=sa_env),
        tmp_path / "s0_guard",
    )
    assert sa_res.verdict_label in ("SUPPORTED", "REFUTED", ARM_VERDICT_INCONCLUSIVE)

    # (iii) the offline EESS slice directly on a tmp dir.
    from repliclaw.slice import run_slice

    report = run_slice(tmp_path / "slice_guard")
    assert report.result.case_id == "policy_rag_v1"

    assert oracle_opened == [], f"oracle opened by arm-side code: {oracle_opened}"


# ---------------------------------------------------------------------------
# 6. Positive control: the scorer (the ONLY allowed reader) can still read it
# ---------------------------------------------------------------------------
def test_scorer_can_still_read_oracle() -> None:
    """We have not over-blocked: the sealed oracle parses, and the scorer's
    sole reader (``score.load_oracle``) still opens it successfully."""
    from repliclaw.p08 import score as sc

    assert _ORACLE_DIR.is_dir()
    oracle_path = _ORACLE_DIR / "oracle.json"
    data = json.loads(oracle_path.read_text(encoding="utf-8"))
    assert data.get("case") == "policy_rag_v1"
    assert "true_cause" in data

    # the scorer's DEFAULT_ORACLES points at the same sealed file, and its
    # sole reader opens it (post-seal, scorer-side only).
    assert sc.DEFAULT_ORACLES["policy_rag_v1"] == oracle_path
    oracle = sc.load_oracle("policy_rag_v1")
    assert oracle["case"] == "policy_rag_v1"
    assert oracle["true_cause"] == data["true_cause"]


# ---------------------------------------------------------------------------
# 7. Positive control: the scorer test suite itself stays green (not over-blocked)
# ---------------------------------------------------------------------------
def test_scorer_self_test_still_passes() -> None:
    """The scorer's own P02 replay self-test (run via the same CLI entry the
    gate uses) must still pass — the guard in test 5 does not interfere with
    the scorer's legitimate oracle/case access."""
    from repliclaw.p08 import score as sc

    res = sc.p02_replay_self_test()
    assert res["error"] is None, f"scorer self-test raised: {res['error']}"
    assert res["replay_ok"] is True
    assert res["determinism_ok"] is True
