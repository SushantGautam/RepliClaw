"""The three named comparator arms for P05 (matched-budget baselines).

Per IMPLEMENTATION_PLAN P05 ("fair strong comparators") the headline
comparison is the EESS swarm against a STRONG adaptive central manager at
equal concurrency, plus the two cheap baselines. The arms map onto the shared
coordination baselines in ``repliclaw.strategies`` so the scientific task and
verdict engine are IDENTICAL across arms — only the coordination regime
differs:

- ``SingleAgentBaseline``    (S0) — one strong agent, no peers, no
  aggregation. The floor: is a single strong agent enough?
- ``AdaptiveCentralManager`` (S3) — a STRONG adaptive central manager. It
  deploys the full three-investigator pipeline and, as evidence arrives,
  adapts its plan (the "strong equal-concurrency" comparator). Reuses the
  ``repl_claw`` coordination regime, which is the adaptive, evidence-driven
  decentralized/central follow-up path.
- ``OpenSharingSwarm``       (S4) — N agents sharing context, each seeing
  prior agents' revealed conclusions (correlated by construction). Reuses the
  ``open_debate`` coordination regime.

None of these arms re-implements the task or the verdict engine; they select
a coordination regime and run it under the shared budget envelope.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from ..models import InvestigatorConfig
from .arms import ArmResult, ArmRunner, ArmSpec
from .budget import BudgetLedger, BudgetRecord


class SingleAgentBaseline(ArmRunner):
    """S0 — one strong agent, no peers, no aggregation."""

    strategy = "single_agent"
    n_agents = 1
    arm_label = "single_agent"

    def __init__(self, investigator_factory: Callable[[InvestigatorConfig], Any]):
        super().__init__(investigator_factory)


class AdaptiveCentralManager(ArmRunner):
    """S3 — incumbent RepliClaw full protocol (blind commit/reveal + central
    adaptive follow-up).

    Registry key ``adaptive_central`` (unchanged; A3 keeps artifact/naming keys
    stable). ``AdaptiveCentralManager`` wraps the FULL incumbent
    ``RepliClawProtocol``: blind commit/reveal (an escrow-like mechanism) plus
    a central adaptive follow-up. It is therefore NOT a neutral central
    manager — it already bundles an escrow-like commitment, so
    centrality-vs-escrow are confounded (v1.1 D-1 / v1.2 A3, Hotspots
    Critical 4).

    A3 confounding disclosure: the S5-vs-S3 comparison is the CONFOUNDED
    P2/RQ2 comparison, NOT a clean isolation of the decentralized-vs-central
    coordination choice. It contrasts the new protocol (need-market selection
    + counterfactual slots) against the incumbent full protocol, with the
    centralized-vs-decentralized control confounded with the protocol
    difference — a "cost of centralization" comparison against the incumbent,
    not a causal isolation of decentralization. The P1 estimand is S5-vs-S4
    (``open_sharing_swarm``), which does NOT carry an escrow-like mechanism.
    """

    strategy = "repl_claw"
    n_agents = 3
    arm_label = "adaptive_central"

    def __init__(self, investigator_factory: Callable[[InvestigatorConfig], Any]):
        super().__init__(investigator_factory)


class OpenSharingSwarm(ArmRunner):
    """S4 — N agents sharing context, each seeing prior conclusions.

    The correlated-by-construction swarm: every agent sees the earlier
    agents' revealed conclusions, so their outputs are correlated. This is the
    natural "many agents" baseline the EESS swarm is compared against.
    """

    strategy = "open_debate"
    n_agents = 3
    arm_label = "open_sharing_swarm"

    def __init__(
        self,
        investigator_factory: Callable[[InvestigatorConfig], Any],
        n_agents: int = 3,
    ):
        super().__init__(investigator_factory)
        self.n_agents = n_agents


class EESSArm(ArmRunner):
    """S5 — the EESS swarm: the REAL EESS pipeline, offline and matched-budget.

    This is the arm the headline comparison is *about*: it routes through the
    genuine EESS lifecycle (escrow-commit -> local need choice ->
    counterfactual executor -> verified evidence) via
    ``repliclaw.slice.run_slice``, rather than re-using the shared
    ``run_strategy`` runner the baselines use. It is the offline
    matched-budget arm: ``run_slice`` is fully deterministic (no live LLM, no
    real token spend — live-token runs are a separate P08 concern), so it runs
    hermetically under the SAME ``BudgetEnvelope`` as S3/S4.

    The result reuses the common ``ArmResult`` schema so it lines up with the
    baselines on correctness + cost + latency. The per-arm verdict is derived
    from the EESS post-run prediction outcomes (supported/refuted per
    committed hypothesis) against the case's sealed reference truth; the
    budget consumed is the deterministic offline token accounting (one
    ``COST_TOKENS_PER_ARM`` per executed arm, no live tokens).
    """

    strategy = "eess"
    n_agents = 3
    arm_label = "eess"

    def __init__(self, investigator_factory: Callable[[InvestigatorConfig], Any]):
        super().__init__(investigator_factory)

    def run(
        self,
        claim: "Any",
        ledger: BudgetLedger,
        spec: ArmSpec,
        work_dir: Path,
    ) -> ArmResult:
        # Imported here so the comparator package does not pull the slice
        # (and its simpleaudit dependency) at import time.
        from ..slice import run_slice

        work_dir = Path(work_dir)
        t0 = time.monotonic()
        report = run_slice(work_dir / "eess")
        wall = max(0.0, time.monotonic() - t0)
        result = report.result

        # Deterministic offline token accounting: one COST_TOKENS_PER_ARM per
        # executed arm, plus the agents' committed needs. No live tokens.
        from ..slice.orchestrate import COST_TOKENS_PER_ARM

        n_agents = len(result.agent_ids)
        tokens = (result.published_evidence + n_agents) * COST_TOKENS_PER_ARM

        # Record the arm's observed consumption against the shared envelope
        # (raises BudgetOverflow if it would overrun — parity is never faked).
        ledger.record(
            BudgetRecord(
                agent_id="eess-arm",
                tokens=tokens,
                wall_s=wall,
                n_agents=n_agents,
            )
        )

        # Per-arm verdict: derive from the EESS post-run prediction outcomes
        # against the case's sealed reference truth (post-reveal only).
        verdict_label, confidence = self._verdict(result.predictions_outcome, claim)

        return ArmResult(
            arm_name=self.name(),
            claim_id=claim.claim_id,
            verdict_label=verdict_label,
            n_agents=n_agents,
            total_tokens=tokens,
            total_wall_s=wall,
            envelope_sha256=spec.envelope.sha256(),
            detail={
                "strategy": self.strategy,
                "eess": True,
                "eess_result": result.to_dict(),
                "n_evidence": result.published_evidence,
                "n_needs": result.published_evidence + n_agents,
                "confidence": confidence,
                "agreement": {},
                "errors": [],
            },
        )

    @staticmethod
    def _verdict(predictions_outcome: dict, claim: "Any") -> tuple[str, float]:
        """Map the EESS per-hypothesis outcomes to the common verdict label.

        The EESS slice is a counterfactual case (its own reference truth), not
        the claim's, so we report the arm's own post-run verdict: the
        majority of the committed hypotheses' supported/refuted outcomes.

        When the slice yields no determined outcomes the verdict degrades to
        the non-scorable ``INCONCLUSIVE`` (confidence 0.5). It must NEVER fall
        back on ``claim.reference_truth`` (evaluator truth): an arm-side
        verdict derived from sealed truth would leak the oracle into a
        reported/scored output. PREREG-2026-10 v1.2 A6 (Hotspots Critical 5)
        and CODE-JUDGE-HARNESS-20261008 item 3 require the ``EESSArm._verdict``
        fallback not feed any reported verdict, so that fallback was removed:
        an undetermined offline slice is INCONCLUSIVE by definition and there
        is no legitimate source for any other label. ``claim`` is retained in
        the signature for API stability and is intentionally unused here.
        """
        outcomes = [
            v.get("outcome") for v in predictions_outcome.values()
            if v.get("outcome") in ("supported", "refuted")
        ]
        if outcomes:
            n_sup = outcomes.count("supported")
            n_ref = outcomes.count("refuted")
            if n_sup == n_ref:
                return "INCONCLUSIVE", 0.5
            label = "SUPPORTED" if n_sup > n_ref else "REFUTED"
            return label, round(max(n_sup, n_ref) / len(outcomes), 4)
        # No determined outcomes -> non-scorable "INCONCLUSIVE". Deliberately
        # NOT derived from claim.reference_truth (PREREG-2026-10 v1.2 A6;
        # CODE-JUDGE-HARNESS-20261008 item 3: harness redaction + this
        # truth-free literal are the two-layer fix).
        return "INCONCLUSIVE", 0.5


__all__ = [
    "SingleAgentBaseline",
    "AdaptiveCentralManager",
    "OpenSharingSwarm",
    "EESSArm",
]
