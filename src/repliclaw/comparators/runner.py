"""Comparator harness + matched-budget parity proof for P05.

``ComparatorHarness`` runs every registered arm under ONE shared
``BudgetEnvelope`` and produces a per-arm result table plus a parity report.
``assert_budget_parity`` is the pure function that decides whether a set of
``ArmResult``s constitutes a valid matched-budget comparison:

- every arm must have been given the SAME envelope (identical content hash),
  AND
- no arm may have consumed more than the envelope declared.

If either fails, ``parity`` is ``False`` and the comparison is flagged
invalid — the harness never silently fakes parity.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List

from ..models import Claim, InvestigatorConfig
from .arms import ArmResult, ArmSpec
from .budget import BudgetEnvelope, BudgetLedger
from .managers import AdaptiveCentralManager, EESSArm, OpenSharingSwarm, SingleAgentBaseline

# Evaluator/sealed-truth fields that must NEVER be carried by an arm-side
# ``Claim``. An arm constructing a REPORTED verdict (or an artifact) from any
# of these would leak the oracle into a scored output. See
# PREREG-2026-10 v1.2 A6 and CODE-JUDGE-HARNESS-20261008 item 3 (the
# harness-layer redaction of the two-layer no-oracle-leak fix).
_ARM_SIDE_TRUTH_FIELDS = ("reference_truth", "seeded_fault")


def redact_claim_for_arms(claim: Claim) -> Claim:
    """Return a copy of ``claim`` with all evaluator/sealed-truth fields
    nulled, for safe hand-off to an arm.

    This is the HARNESS-layer guard of the two-layer no-oracle-leak fix
    (CODE-JUDGE-HARNESS-20261008 item 3): the arm must be constructible
    without any ground-truth label, so no arm object can carry it. The
    fallback-layer guard (``EESSArm._verdict`` no longer consulting
    ``claim.reference_truth``) is defense in depth.

    Returns a NEW ``Claim`` (the caller's object is not mutated); the
    statement/data the arm actually reasons over are preserved.
    """
    return claim.model_copy(update={f: None for f in _ARM_SIDE_TRUTH_FIELDS})


def arm_registry() -> Dict[str, Callable[[Callable[[InvestigatorConfig], Any]], Any]]:
    """The named comparator arms, keyed by arm name.

    Values are constructors taking an investigator factory.
    """
    return {
        "single_agent": SingleAgentBaseline,
        "adaptive_central": AdaptiveCentralManager,
        "open_sharing_swarm": OpenSharingSwarm,
        "eess": EESSArm,
    }


def assert_budget_parity(
    results: List[ArmResult],
    envelope: BudgetEnvelope,
) -> Dict[str, Any]:
    """Decide whether a set of arm results is a valid matched-budget comparison.

    Returns a report dict with:
      * ``parity``            — True only if all arms share one envelope AND
                                none exceeded it;
      * ``n_arms``            — number of arms checked;
      * ``envelope_sha256``   — the envelope hash all arms should match;
      * ``envelope_hashes``   — the set of distinct envelope hashes observed;
      * ``over_budget_arms``  — arms whose reported usage exceeds the envelope.
    """
    expected = envelope.sha256()
    hashes = {r.envelope_sha256 for r in results}
    over = [
        r.arm_name
        for r in results
        if r.total_tokens > envelope.max_tokens
        or r.total_wall_s > envelope.max_wall_s + 1e-9
        or r.n_agents > envelope.max_agents
    ]
    parity = hashes == {expected} and not over
    return {
        "parity": parity,
        "n_arms": len(results),
        "envelope_sha256": expected,
        "envelope_hashes": sorted(hashes),
        "over_budget_arms": over,
    }


class ComparatorHarness:
    """Runs all registered arms under ONE shared envelope and reports parity.

    Each arm gets a FRESH ``BudgetLedger`` bound to the SAME envelope, so an
    arm that overruns the shared budget raises ``BudgetOverflow`` (parity is
    never silently faked). The returned report carries the per-arm results and
    the parity verdict.
    """

    def __init__(self, investigator_factory: Callable[[InvestigatorConfig], Any]):
        self._factory = investigator_factory

    def run(
        self,
        claim: Claim,
        envelope: BudgetEnvelope,
        work_root: Path,
    ) -> Dict[str, Any]:
        work_root = Path(work_root)
        # Harness-layer no-oracle-leak guard: redact evaluator/sealed truth
        # BEFORE any arm is constructed (CODE-JUDGE-HARNESS-20261008 item 3).
        # The shared claim passed to every arm must carry no ground-truth
        # label; ``claim.model_copy`` keeps the caller's object intact.
        claim = redact_claim_for_arms(claim)
        registry = arm_registry()
        results: List[ArmResult] = []
        for name, ctor in registry.items():
            arm = ctor(self._factory)
            ledger = BudgetLedger(envelope)
            spec = ArmSpec(arm_name=name, claim_id=claim.claim_id, envelope=envelope)
            results.append(arm.run(claim, ledger, spec, work_root / name))
        report = assert_budget_parity(results, envelope)
        return {
            "claim_id": claim.claim_id,
            "envelope": envelope.to_dict(),
            "envelope_sha256": envelope.sha256(),
            "arms": {r.arm_name: r.to_dict() for r in results},
            "parity": report,
        }


__all__ = [
    "ComparatorHarness",
    "arm_registry",
    "assert_budget_parity",
    "redact_claim_for_arms",
]
