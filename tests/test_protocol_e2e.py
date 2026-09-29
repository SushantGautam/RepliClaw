"""End-to-end protocol run (hermetic, deterministic backend): correct verdicts
on known-answer fixtures + verdict provenance (AC07/AC08/AC12/AC15)."""
import json
from pathlib import Path

from repliclaw.investigators import DeterministicInvestigator
from repliclaw.models import Claim
from repliclaw.protocol import STRATEGY_REPLICLAW, RepliClawProtocol

FIX = Path(__file__).resolve().parent / "fixtures"


def load_claim(name):
    fx = json.loads((FIX / f"{name}.json").read_text())
    c = fx["claim"]
    return Claim(
        claim_id=f"claim-{name}",
        statement=c["statement"],
        domain=c.get("domain", "general"),
        data=c.get("data"),
        reference_truth=c.get("reference_truth"),
        seeded_fault=c.get("seeded_fault"),
    ), fx["truth"]


def run(claim, tmp):
    proto = RepliClawProtocol(
        run_root=Path(tmp),
        investigator_factory=lambda cfg: DeterministicInvestigator(cfg),
        strategy=STRATEGY_REPLICLAW,
        min_independent=3,
    )
    return proto.run(claim)


def test_clean_supported_is_supported(tmp_path):
    claim, truth = load_claim("clean_supported")
    res = run(claim, tmp_path)
    assert truth == "supported"
    assert res.verdict.label.value == "SUPPORTED"
    assert res.verdict.n_support == 3
    assert res.verdict.n_contradict == 0
    assert res.verdict.unresolved_conflicts == []
    # No follow-up needed when all agree.
    assert res.needs == []
    assert res.errors == []


def test_clean_refuted_is_refuted(tmp_path):
    """A clean null (no effect, CI includes 1) must yield REFUTED, not merely
    abstention — the falsifier's directional executable signal is sufficient."""
    claim, truth = load_claim("clean_refuted")
    res = run(claim, tmp_path)
    assert truth == "refuted"
    assert res.verdict.label.value == "REFUTED"
    assert res.verdict.n_support == 0
    assert res.verdict.n_contradict >= 1


def test_misleading_recovers_to_refuted_with_conflict_surfaced(tmp_path):
    """Fault mode: naive means test 'supports', raw events refute. There is a
    GENUINE independent conflict, the falsifier-lens follow-up ADJUDICATES it,
    the conflict is surfaced, and the final verdict recovers to REFUTED (AC12)."""
    claim, truth = load_claim("misleading_wrong_test")
    res = run(claim, tmp_path)
    assert truth == "refuted"
    assert res.verdict.label.value == "REFUTED"
    # The disagreement was real and was surfaced.
    assert any(c for c in res.verdict.unresolved_conflicts)
    # A falsification follow-up need was triggered.
    kinds = [n.get("kind") for n in res.needs]
    assert "falsification" in kinds
    # Recovery came from a decisive executable follow-up.
    assert "ADJUDICATED" in res.verdict.reasoning
    # Confidence must be LOWER than the clean supported case (calibration).
    supp, _ = load_claim("clean_supported")
    res_s = run(supp, tmp_path / "supported_run")
    assert res.verdict.confidence < res_s.verdict.confidence


def test_verdict_provenance_is_complete(tmp_path):
    claim, _ = load_claim("misleading_wrong_test")
    res = run(claim, tmp_path)
    v = res.verdict
    # Every piece of cited evidence must exist in the run.
    ev_ids = {e.evidence_id for e in res.evidence}
    assert set(v.evidence_refs) <= ev_ids
    # Provenance: each evidence references its commitment + artifacts.
    for e in res.evidence:
        assert e.commitment_id
        assert e.finding
        # Executable deterministic findings are marked executable.
        assert e.executable is True
    # Verdict decomposition counts are consistent.
    assert v.n_support + v.n_contradict + v.n_replicate + v.n_fail_replicate <= len(res.evidence)
    # The run persisted a verdict + commitments + events.
    from repliclaw.runstore import RunStore

    store = RunStore(Path(res.run_dir))
    kinds = {e["kind"] for e in store.events()}
    assert {"committed", "revealed", "phase"} <= kinds


def test_investigators_are_independent_agents(tmp_path):
    claim, _ = load_claim("clean_supported")
    res = run(claim, tmp_path)
    agents = {e.agent_id for e in res.evidence}
    assert len(agents) >= 3
    assert res.verdict.independent_evidence_count >= 3
