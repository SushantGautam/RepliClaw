"""Verdict engine unit tests: evidence-weighting, sufficiency, and the
decisive-follow-up adjudication rule (AC05 / AC12)."""
from repliclaw.models import (
    Claim,
    Evidence,
    EvidenceRelation,
    VerdictLabel,
)
from repliclaw.verdict import (
    _decisive_adjudicator,
    compute_verdict,
    weighted_score,
)


def ev(agent, relation, executable=True, confidence=0.8, quality="ok", notes=""):
    return Evidence(
        evidence_id=f"ev-{agent}-{relation.value}",
        claim_id="claim-u",
        agent_id=agent,
        relation=relation,
        finding={"conclusion": relation.value},
        commitment_id=f"cmt-{agent}",
        executable=executable,
        quality=quality,
        confidence=confidence,
        notes=notes,
    )


def test_weighted_score_direction_and_magnitude():
    support = [ev("a", EvidenceRelation.SUPPORTS)]
    contradict = [ev("b", EvidenceRelation.CONTRADICTS)]
    assert weighted_score(support) > 0
    assert weighted_score(contradict) < 0
    # Executable evidence is weighted more than opinion on the same relation.
    opinion = [ev("a", EvidenceRelation.SUPPORTS, executable=False, confidence=0.8)]
    assert weighted_score(support) > weighted_score(opinion)


def test_executable_beats_opinion_weight():
    strong = [ev("a", EvidenceRelation.CONTRADICTS, executable=True)]
    weak = [ev("b", EvidenceRelation.SUPPORTS, executable=False)]
    # One strong executable contradiction should outweigh one weak opinion,
    # whether considered alone or combined with the opposing opinion.
    assert weighted_score(strong) < 0
    assert weighted_score(strong + weak) < 0


def test_sufficiency_requires_directional_executable():
    claim = Claim(claim_id="claim-u", statement="x")
    # Pure abstention -> inconclusive.
    abstain = [ev("a", EvidenceRelation.NEUTRAL, executable=True)]
    assert compute_verdict(claim, abstain).label == VerdictLabel.INCONCLUSIVE
    # Directional but non-executable (opinion only) -> inconclusive.
    opinion = [ev("a", EvidenceRelation.SUPPORTS, executable=False)]
    assert compute_verdict(claim, opinion).label == VerdictLabel.INCONCLUSIVE
    # Directional + executable -> a real verdict.
    real = [ev("a", EvidenceRelation.CONTRADICTS, executable=True)]
    assert compute_verdict(claim, real).label == VerdictLabel.REFUTED


def test_decisive_adjudicator_requires_executable_directional_confident():
    f = EvidenceRelation
    good = ev("follow", f.CONTRADICTS, executable=True, confidence=0.7, notes="fulfills need x")
    non_exec = ev("f2", f.CONTRADICTS, executable=False, confidence=0.9)
    suspicious = ev("f3", f.CONTRADICTS, executable=True, confidence=0.9, quality="suspicious")
    low_conf = ev("f4", f.CONTRADICTS, executable=True, confidence=0.4)
    neutral = ev("f5", f.NEUTRAL, executable=True, confidence=0.9)

    assert _decisive_adjudicator([good]) is not None
    assert _decisive_adjudicator([non_exec]) is None
    assert _decisive_adjudicator([suspicious]) is None
    assert _decisive_adjudicator([low_conf]) is None
    assert _decisive_adjudicator([neutral]) is None
    assert _decisive_adjudicator([non_exec, suspicious, low_conf]) is None
    # Picks the most confident decisive one.
    pick = _decisive_adjudicator([good, ev("f6", f.CONTRADICTS, confidence=0.95)])
    assert pick is not None and pick.confidence == 0.95


def test_conflict_adjudicated_by_decisive_followup():
    claim = Claim(claim_id="claim-u", statement="x")
    f = EvidenceRelation
    evidence = [
        ev("a", f.SUPPORTS),
        ev("b", f.SUPPORTS),
        ev("c", f.CONTRADICTS),  # the conflict
    ]
    follow = ev("follow", f.CONTRADICTS, executable=True, confidence=0.8,
                notes="fulfills need x")
    v = compute_verdict(
        claim, evidence,
        followup_evidence=[follow],
    )
    assert v.label == VerdictLabel.REFUTED
    assert "ADJUDICATED" in v.reasoning
    # The conflict is still surfaced.
    assert v.unresolved_conflicts


def test_conflict_without_decisive_followup_stays_inconclusive():
    claim = Claim(claim_id="claim-u", statement="x")
    f = EvidenceRelation
    evidence = [ev("a", f.SUPPORTS), ev("b", f.CONTRADICTS)]
    # Weak (non-executable) follow-up cannot break the tie.
    follow = ev("follow", f.CONTRADICTS, executable=False, confidence=0.9,
                notes="fulfills need x")
    v = compute_verdict(claim, evidence, followup_evidence=[follow])
    assert v.label == VerdictLabel.INCONCLUSIVE
    assert v.unresolved_conflicts


def test_inconclusive_is_never_high_confidence():
    claim = Claim(claim_id="claim-u", statement="x")
    abstain = [ev("a", EvidenceRelation.NEUTRAL, executable=True, confidence=0.99)]
    v = compute_verdict(claim, abstain)
    assert v.label == VerdictLabel.INCONCLUSIVE
    assert v.confidence <= 0.6
