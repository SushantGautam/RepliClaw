"""Evidence-aware verdict engine (M4).

Decision rule (NOT majority vote):
  1. Weighted evidence score: each piece of evidence contributes
     +1 (supports), -1 (contradicts), +0.5 (replicates), -0.5
     (fails-to-replicate), 0 (neutral), scaled by an importance factor that
     rewards EXECUTABLE and independent evidence and penalizes suspicious
     quality. Confidence modulates, but does not dominate, the weight.
  2. Conflict gate: if there is an unresolved independent conflict, the
     verdict is at most INCONCLUSIVE unless an independent FOLLOW-UP produced
     a decisive, executable, directional lean — in which case the follow-up
     adjudicates (recovery from misleading evidence, AC12).
  3. Sufficiency gate: if evidence is insufficient (no executable evidence,
     or mostly abstentions), verdict is INCONCLUSIVE.
  4. Confidence is a calibration-ish score combining agreement fraction,
     executable-evidence fraction, and conflict penalty.

Unresolved conflicts and abstention are always surfaced in the output.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .evidence import detect_conflicts, insufficient_evidence
from .models import Claim, Evidence, EvidenceRelation, Verdict, VerdictLabel

WEIGHTS = {
    EvidenceRelation.SUPPORTS: 1.0,
    EvidenceRelation.CONTRADICTS: -1.0,
    EvidenceRelation.REPLICATES: 0.5,
    EvidenceRelation.FAILS_TO_REPLICATE: -0.5,
    EvidenceRelation.DEPENDS_ON: 0.0,
    EvidenceRelation.NEUTRAL: 0.0,
}


def _importance(ev: Evidence, n_agents: int) -> float:
    w = 1.0
    if ev.executable:
        w *= 1.5
    if ev.quality == "suspicious":
        w *= 0.25
    elif ev.quality == "empty":
        w *= 0.5
    # Independence bonus: evidence from one of several agents is more
    # valuable than a single-source finding.
    if n_agents > 1:
        w *= 1.0 + 0.1 * (n_agents - 1)
    # Confidence modulates (capped) so a confident-but-solo finding cannot
    # outvote two skeptical independent ones.
    w *= 0.7 + 0.6 * (ev.confidence or 0.5)
    return w


def weighted_score(evidence: List[Evidence]) -> float:
    n_agents = len({e.agent_id for e in evidence}) or 1
    total = 0.0
    for ev in evidence:
        total += WEIGHTS.get(ev.relation, 0.0) * _importance(ev, n_agents)
    return total


def _weighted_side(evidence: List[Evidence]) -> str:
    """'support' / 'refute' / 'balanced' by which side's weighted magnitude
    is larger (ties and zeros → balanced)."""
    sup = sum(
        WEIGHTS[e.relation] * _importance(e, len({x.agent_id for x in evidence}) or 1)
        for e in evidence
        if WEIGHTS.get(e.relation, 0.0) > 0
    )
    ref = -sum(
        WEIGHTS[e.relation] * _importance(e, len({x.agent_id for x in evidence}) or 1)
        for e in evidence
        if WEIGHTS.get(e.relation, 0.0) < 0
    )
    if abs(sup - ref) < 1e-9:
        return "balanced"
    return "support" if sup > ref else "refute"


def _decisive_adjudicator(followups: List[Evidence]) -> Optional[Evidence]:
    """The strongest follow-up that is directional, EXECUTABLE, not
    suspicious, and confident enough to adjudicate a conflict. `None` when
    no follow-up is strong enough (a weak follow-up must not force a
    verdict)."""
    decisive = [
        f for f in followups
        if f.executable
        and f.quality != "suspicious"
        and f.relation
        in (
            EvidenceRelation.SUPPORTS,
            EvidenceRelation.CONTRADICTS,
            EvidenceRelation.REPLICATES,
            EvidenceRelation.FAILS_TO_REPLICATE,
        )
        and (f.confidence or 0.0) >= 0.6
    ]
    if not decisive:
        return None
    return max(decisive, key=lambda f: f.confidence or 0.0)


def compute_verdict(
    claim: Claim,
    evidence: List[Evidence],
    conflicts: List[Dict[str, Any]] | None = None,
    independent_count: int | None = None,
    followup_evidence: List[Evidence] | None = None,
) -> Verdict:
    if conflicts is None:
        conflicts = detect_conflicts(evidence)
    if independent_count is None:
        independent_count = len({e.agent_id for e in evidence})

    support = [e for e in evidence if e.relation == EvidenceRelation.SUPPORTS]
    contradict = [
        e for e in evidence
        if e.relation in (EvidenceRelation.CONTRADICTS, EvidenceRelation.FAILS_TO_REPLICATE)
    ]
    replicate = [e for e in evidence if e.relation == EvidenceRelation.REPLICATES]
    fail_rep = [e for e in evidence if e.relation == EvidenceRelation.FAILS_TO_REPLICATE]

    score = weighted_score(evidence)
    n = len(evidence) or 1
    agreement_frac = (max(len(support), len(contradict)) / n)
    executable_frac = (sum(1 for e in evidence if e.executable) / n) if n else 0.0

    unresolved_conflicts = [c.get("agents", []) for c in (conflicts or []) if c.get("independent")]
    insufficient = insufficient_evidence(evidence)
    adjudicator: Optional[Evidence] = None

    # ---- Decide ----------------------------------------------------------
    if insufficient and not evidence:
        label = VerdictLabel.INCONCLUSIVE
        reasoning = "No usable evidence produced; abstain."
    elif unresolved_conflicts:
        # A real independent conflict that survived follow-up. Default: abstain
        # (no forced certainty). BUT the protocol's deadlock-breaker is the
        # independent follow-up: if it produced a DECISIVE, executable,
        # directional lean, it ADJUDICATES the conflict (recovery, AC12). A
        # weak or non-executable follow-up cannot break the tie — it stays
        # INCONCLUSIVE with the conflict surfaced.
        adjudicator = _decisive_adjudicator(followup_evidence or [])
        if adjudicator is not None:
            label = (
                VerdictLabel.SUPPORTED
                if adjudicator.relation in (
                    EvidenceRelation.SUPPORTS,
                    EvidenceRelation.REPLICATES,
                )
                else VerdictLabel.REFUTED
            )
            reasoning = (
                f"Independent conflict between "
                f"{[a for c in unresolved_conflicts for a in c]} was ADJUDICATED by "
                f"independent follow-up {adjudicator.agent_id} "
                f"({adjudicator.relation.value}, executable={adjudicator.executable}); "
                f"weighted score {score:+.2f}. Recovery from misleading evidence."
            )
        else:
            label = VerdictLabel.INCONCLUSIVE
            leaning = _weighted_side(evidence)
            reasoning = (
                "Unresolved independent disagreement between "
                f"{[a for c in unresolved_conflicts for a in c]}; weighted score "
                f"{score:+.2f} ({leaning}). No decisive follow-up; abstain."
            )
    elif insufficient:
        label = VerdictLabel.INCONCLUSIVE
        reasoning = (
            "Evidence insufficient (no executable directional evidence); "
            f"weighted score {score:+.2f}. Abstain."
        )
    elif score > 0:
        label = VerdictLabel.SUPPORTED
        reasoning = (
            f"Weighted evidence score {score:+.2f} in favor; "
            f"{len(support)} support / {len(contradict)} contradict; "
            f"{len(replicate)} replication(s). No unresolved independent conflict."
        )
    elif score < 0:
        label = VerdictLabel.REFUTED
        reasoning = (
            f"Weighted evidence score {score:+.2f} against; "
            f"{len(support)} support / {len(contradict)} contradict; "
            f"{len(fail_rep)} failed replication(s). No unresolved independent conflict."
        )
    else:
        label = VerdictLabel.INCONCLUSIVE
        reasoning = f"Balanced weighted evidence (score {score:+.2f}); abstain."

    # ---- Confidence (calibration-ish) ------------------------------------
    conflict_penalty = 0.3 * len(unresolved_conflicts)
    confidence = (
        0.5 * agreement_frac
        + 0.3 * executable_frac
        + 0.2 * min(1.0, abs(score) / (n * 1.0))
    )
    confidence = max(0.05, min(0.98, confidence - conflict_penalty))
    if label == VerdictLabel.INCONCLUSIVE:
        confidence = min(confidence, 0.6)  # abstention is never high-confidence

    return Verdict(
        claim_id=claim.claim_id,
        label=label,
        confidence=round(confidence, 3),
        n_support=len(support),
        n_contradict=len(contradict) + len(fail_rep),
        n_replicate=len(replicate),
        n_fail_replicate=len(fail_rep),
        independent_evidence_count=independent_count,
        unresolved_conflicts=[
            {"agents": c.get("agents", []),
             "support": c.get("support_evidence", []),
             "contradict": c.get("contradict_evidence", [])}
            for c in (conflicts or [])
        ],
        evidence_refs=[e.evidence_id for e in evidence],
        reasoning=reasoning,
        error_correlation=None,  # filled by benchmark across runs
    )
