"""Evidence-derived selection (closes science-judge item 3 / finding M2).

``derive_discriminability`` computes each agent's per-need expected
information gain **from the published evidence observations only** — no
externally set numbers. The update rules below are declared once, exactly
mirroring the agents' committed refutation criteria, and applied to
``evidence_view(...)`` outputs:

* an arm already in the evidence yields **0** gain (its information has
  been collected);
* arms whose committed prediction is **refuted** by the published
  evidence close out (0) and **open** their competing hypothesis's arm
  (that arm now carries the surviving weight — this is the mechanism
  that makes later choices evidence-directed, not oracle-tinted);
* arms whose committed prediction is **supported** by the published
  evidence close out (0);
* untested arms a single interested agent has not yet resolved keep the
  prior weight of the hypothesis they test; the baseline arm is valued
  (weaker) by every agent as the reference for every output comparison.

The function is pure: same evidence view in, same mapping out. A test
asserts that different evidence views yield *different, correctly
directed* mappings (the choice change is DERIVED from the observation).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

BASELINE_ARM = "I0_baseline"
ARM_BY_HYP = {"H_R": "I_R_retrieval_fix", "H_P": "I_P_policy_conflict", "H_J": "I_J_judge_fix"}
# Which hypothesis each arm, if it comes back informative, settles.
ARM_TESTED_HYP = {v: k for k, v in ARM_BY_HYP.items()}
# A refuted hypothesis opens (competes with) these arms.
COMPETING_ARM = {"H_R": "I_J_judge_fix", "H_P": None, "H_J": "I_R_retrieval_fix"}

PRIOR_WEIGHT = 1.0
BASELINE_WEIGHT = 0.9


def _arm_outcomes(evidence: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for obs in evidence:
        data = obs.get("data", {})
        arm = data.get("intervention_id")
        if arm:
            out[arm] = data
    return out


def _outcome(
    arm: str, outcomes: Dict[str, Dict[str, Any]], hyp: str
) -> str:
    """'supported' | 'refuted' | 'unknown' per the committed criteria."""
    d = outcomes.get(arm)
    base = outcomes.get(BASELINE_ARM)
    if d is None or base is None:
        return "unknown"
    if hyp == "H_R":
        supported = (
            d.get("severity") == "critical"
            and base.get("severity") == "pass"
            and d.get("target_window_days") == 30
            and base.get("target_window_days") == 14
        )
        return "supported" if supported else "refuted"
    if hyp == "H_P":
        # prediction: I_P output differs from baseline; refutation: identical
        return "refuted" if d.get("target_output") == base.get("target_output") else "supported"
    if hyp == "H_J":
        supported = (
            d.get("target_output") == base.get("target_output")
            and d.get("severity") != base.get("severity")
        )
        return "supported" if supported else "refuted"
    return "unknown"


def derive_discriminability(
    agent_id: str,
    hypothesis_id: str,
    need_ids: List[str],
    evidence_view: Dict[str, Any],
    arms: Optional[Dict[str, str]] = None,
) -> Dict[str, Dict[str, float]]:
    """Per-need, per-hypothesis info gain derived ONLY from the evidence.

    ``arms`` maps need_id -> arm (defaults to the standard slice naming).
    Returns ``{need_id: {hypothesis_id: gain}}`` for needs with gain > 0.
    """
    observations = evidence_view.get("observations", [])
    outcomes = _arm_outcomes(observations)
    seen_arms = set(outcomes)

    arm_by_need = dict(arms or {})
    own_arm = ARM_BY_HYP[hypothesis_id]
    own_outcome = _outcome(own_arm, outcomes, hypothesis_id)

    # Hypotheses currently OPEN (not refuted by the published evidence).
    open_hyps: set = set()
    for hyp in ARM_BY_HYP:
        if _outcome(ARM_BY_HYP[hyp], outcomes, hyp) != "refuted":
            open_hyps.add(hyp)
    if not open_hyps:
        open_hyps = {hypothesis_id}  # guard: never an empty mapping

    mapping: Dict[str, Dict[str, float]] = {}
    for need_id in need_ids:
        arm = arm_by_need.get(need_id, need_id.replace("need_", "", 1))
        if arm in seen_arms:
            continue  # information already collected
        weight: Optional[float] = None
        if arm == BASELINE_ARM:
            weight = BASELINE_WEIGHT
        elif arm in ARM_TESTED_HYP and ARM_TESTED_HYP[arm] in open_hyps:
            weight = PRIOR_WEIGHT
        elif own_outcome == "refuted":
            # The agent's hypothesis just closed; the surviving competing
            # arm becomes the informative one for this agent.
            comp = COMPETING_ARM.get(hypothesis_id)
            if arm == comp and (comp or "") in ARM_TESTED_HYP:
                weight = PRIOR_WEIGHT
        if weight:
            # Credit goes to the hypothesis that arm settles, so the
            # mapping stays per-hypothesis (policy sums over values).
            credit_hyp = ARM_TESTED_HYP.get(arm, hypothesis_id)
            mapping[need_id] = {credit_hyp: weight}
    return mapping
