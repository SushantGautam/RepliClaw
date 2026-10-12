"""EVALUATOR-ONLY scorer for the falsification comparison.

This module is the SOLE reader of the adversarial-audit ground truth and trap
annotations (:mod:`repliclaw.benchmarks.adversarial_audit.ground_truth`). It
must run in the trusted scorer process and must NEVER be imported from
investigator/agent code. The arm runners (:mod:`.arms`) only ever see the
public evidence loader; they cannot reach the answers.

Metrics per arm (over the selected claims):
  * ``accuracy`` — fraction of claims whose team verdict equals ground truth.
  * ``abstention_rate`` — fraction of claims the arm abstained on.
  * ``robustness_trap_accuracy`` — accuracy restricted to TRAP claims (claims
    whose decisive evidence includes a misleading / contradictory / unreliable
    artifact). This is the metric that speaks to the scientific question.
  * ``total_tokens`` / ``total_tool_calls`` / ``total_llm_calls`` /
    ``total_wall_s`` — the arm's actual spend (matched across arms).
  * ``individual_accuracy`` — accuracy over every (claim, investigator) vote.
  * ``false_consensus_*`` — for team arms: how often the team's agreed
    conclusion is wrong, and how often that error overrode a correct individual
    (the herding signature).
"""
from __future__ import annotations

from typing import Any, Dict, List, Set

from repliclaw.benchmarks.adversarial_audit import data as aa_data
from repliclaw.benchmarks.adversarial_audit import ground_truth as gt

from .arms import ArmResult

#: Trap tags that mark an artifact as misleading / contradictory / unreliable
#: (as opposed to genuinely supporting or mere context).
_TRAP_TAGS = frozenset(
    {"misleading_statistic", "contradiction", "unreliable_source", "small_n_no_ci", "spurious_correlation"}
)


def trap_claim_ids() -> Set[str]:
    """EVALUATOR-ONLY. The set of claims whose evidence includes a trap artifact.

    A claim is a "trap claim" if at least one artifact that addresses it carries
    a trap tag (misleading / contradictory / unreliable). Derived from the
    private trap taxonomy + the public ``claims_addressed`` mapping.
    """
    ann = {a["artifact_id"]: a for a in gt.load_trap_annotations()["annotations"]}
    trap_artifacts = {
        aid for aid, a in ann.items() if _TRAP_TAGS & set(a.get("trap_tags", []))
    }
    trap_claims: Set[str] = set()
    for art in aa_data.load_evidence():
        if art["artifact_id"] in trap_artifacts:
            trap_claims.update(art.get("claims_addressed", []))
    return trap_claims


def score_arm(arm: str, results: List[ArmResult]) -> Dict[str, Any]:
    """EVALUATOR-ONLY. Score one arm's per-claim results against ground truth."""
    answers = gt.answers()
    trap_claims = trap_claim_ids()

    n = len(results)
    correct = abstained = 0
    trap_correct = trap_total = 0
    total_tokens = total_tool_calls = total_llm_calls = 0
    total_wall = 0.0
    per_claim: Dict[str, Any] = {}

    individual_correct = individual_total = 0
    team_wrong = 0
    team_wrong_individual_right = 0

    for r in results:
        claim_id = r.claim_id
        expected = answers.get(claim_id)
        verdict = r.team_verdict
        is_correct = verdict == expected
        is_abstain = verdict == "ABSTAIN"
        is_trap = claim_id in trap_claims

        total_tokens += r.total_tokens
        total_tool_calls += r.total_tool_calls
        total_llm_calls += r.total_llm_calls
        total_wall += r.total_wall_s

        if is_correct:
            correct += 1
        if is_abstain:
            abstained += 1
        if is_trap:
            trap_total += 1
            if is_correct:
                trap_correct += 1

        # Individual votes (team arms have N; single-agent arms have 1).
        votes = [iv for iv in r.individual_verdicts.values() if iv is not None]
        for iv in votes:
            individual_total += 1
            if iv == expected:
                individual_correct += 1

        if not is_correct:
            team_wrong += 1
            if any(iv == expected for iv in votes):
                team_wrong_individual_right += 1

        per_claim[claim_id] = {
            "expected": expected,
            "predicted": verdict,
            "correct": is_correct,
            "abstained": is_abstain,
            "is_trap": is_trap,
            "individual_verdicts": r.individual_verdicts,
        }

    return {
        "arm": arm,
        "total": n,
        "correct": correct,
        "accuracy": (correct / n) if n else 0.0,
        "abstained": abstained,
        "abstention_rate": (abstained / n) if n else 0.0,
        "trap_total": trap_total,
        "trap_correct": trap_correct,
        "robustness_trap_accuracy": (trap_correct / trap_total) if trap_total else None,
        "total_tokens": total_tokens,
        "total_tool_calls": total_tool_calls,
        "total_llm_calls": total_llm_calls,
        "total_wall_s": round(total_wall, 4),
        "individual_total": individual_total,
        "individual_correct": individual_correct,
        "individual_accuracy": (individual_correct / individual_total) if individual_total else None,
        "team_wrong": team_wrong,
        "team_wrong_individual_right": team_wrong_individual_right,
        "false_consensus_rate": (
            (team_wrong_individual_right / team_wrong) if team_wrong else None
        ),
        "per_claim": per_claim,
    }


def score_all(arm_results: Dict[str, List[ArmResult]]) -> Dict[str, Any]:
    """EVALUATOR-ONLY. Score every arm; return the results table."""
    return {arm: score_arm(arm, results) for arm, results in arm_results.items()}


__all__ = ["trap_claim_ids", "score_arm", "score_all"]
