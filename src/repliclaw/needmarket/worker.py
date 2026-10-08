"""Need worker: one decentralized agent running the local choice loop
(ticket P04, G4).

Loop (per ``cycle()``):

1. ``open_needs`` (broker filter — no ranking),
2. ``eligible`` self-check per need (pure, local),
3. ``policy.rank`` — the ONLY scientific ranking; recorded as
   ``choice_ranked`` (full components) BEFORE any claim,
4. ``claim`` (atomic O_EXCL lease; loser returns None and the worker
   abstains this cycle),
5. ``execute(need)`` — a blind injected callback (P07 wires the P02
   SimpleAudit executor here later); the callback returns a dict with at
   least ``artifact_id`` and ``verified``,
6. ``fulfill(verified=...)`` — only verified work marks the need done,
7. if the ranking for this snapshot differs from the agent's previous
   ranking, emit ``choice_changed`` with {prev_ranking, new_ranking,
   snapshot_sha, delta_reason}.

The worker never calls a central allocator: everything it decides comes
from its own policy over the public open-need list and the evidence
snapshot.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from repliclaw.needmarket.broker import BudgetExhausted, NeedBroker
from repliclaw.needmarket.needs import Need, WorkerCapability, eligible
from repliclaw.needmarket.policy import ActionPolicy, RankedAction
from repliclaw.needmarket.replay import snapshot as evidence_snapshot


@dataclass
class CycleResult:
    cycle: int
    ranked: List[RankedAction]
    claimed_need_id: Optional[str]
    claimed: bool
    fulfilled: Optional[bool]
    abstained: bool
    abstain_reason: Optional[str] = None


class NeedWorker:
    """One agent's local need-market loop."""

    def __init__(
        self,
        capability: WorkerCapability,
        broker: NeedBroker,
        policy: ActionPolicy,
        execute: Callable[[Need], Dict[str, Any]],
        rng_seed: int = 0,
    ) -> None:
        self.capability = capability
        self.broker = broker
        self.policy = policy
        self.execute = execute
        self.rng_seed = rng_seed
        self._prev_ranking: Optional[List[Dict[str, Any]]] = None
        self._cycle = 0

    # -- choice trace --------------------------------------------------------
    @staticmethod
    def _ranking_view(ranked: List[RankedAction]) -> List[Dict[str, Any]]:
        return [
            {"need_id": r.need_id, "utility": r.utility, "components": r.components}
            for r in ranked
        ]

    def _emit_choice_events(
        self, ranked: List[RankedAction], snapshot_sha: str
    ) -> Optional[Dict[str, Any]]:
        view = self._ranking_view(ranked)
        self.broker.record(
            "choice_ranked",
            agent_id=self.capability.agent_id,
            snapshot_sha=snapshot_sha,
            ranking=view,
        )
        changed = None
        if self._prev_ranking is not None and self._prev_ranking != view:
            changed = {
                "prev_ranking": self._prev_ranking,
                "new_ranking": view,
                "snapshot_sha": snapshot_sha,
                "delta_reason": (
                    "local policy re-ranked under a different evidence "
                    "snapshot; see components for the changed terms"
                ),
            }
            self.broker.record(
                "choice_changed",
                agent_id=self.capability.agent_id,
                **changed,
            )
        self._prev_ranking = view
        return changed

    # -- main loop ---------------------------------------------------------------
    def cycle(self, evidence: Any = None) -> Optional[CycleResult]:
        """One local choice + claim + execute + fulfill pass."""
        self._cycle += 1
        snapshot_sha = evidence_snapshot(evidence if evidence is not None else {})
        open_needs = self.broker.open_needs(exclude_agent=self.capability.agent_id)
        if not open_needs:
            self.broker.record(
                "abstained",
                agent_id=self.capability.agent_id,
                snapshot_sha=snapshot_sha,
                reason="no open needs",
            )
            return CycleResult(self._cycle, [], None, False, None, True, "no open needs")

        ranked = self.policy.rank(
            self.capability.agent_id, open_needs, snapshot_sha, self.rng_seed
        )
        self._emit_choice_events(ranked, snapshot_sha)

        # First eligible, highest-ranked need.
        chosen: Optional[Need] = None
        for ra in ranked:
            need = next((n for n in open_needs if n.need_id == ra.need_id), None)
            if need is not None and eligible(need, self.capability):
                chosen = need
                break
        if chosen is None:
            self.broker.record(
                "abstained",
                agent_id=self.capability.agent_id,
                snapshot_sha=snapshot_sha,
                reason="no eligible need in local ranking",
            )
            return CycleResult(
                self._cycle, ranked, None, False, None, True, "no eligible need"
            )

        try:
            lease = self.broker.claim(
                chosen.need_id,
                self.capability.agent_id,
                agent_budget_tokens=self.capability.budget_tokens,
            )
        except BudgetExhausted as exc:
            self.broker.record(
                "abstained",
                agent_id=self.capability.agent_id,
                snapshot_sha=snapshot_sha,
                reason=f"budget_exhausted: {exc}",
            )
            return CycleResult(
                self._cycle, ranked, chosen.need_id, False, None, True, str(exc)
            )
        if lease is None:
            self.broker.record(
                "abstained",
                agent_id=self.capability.agent_id,
                snapshot_sha=snapshot_sha,
                reason=f"lost claim race for {chosen.need_id}",
            )
            return CycleResult(
                self._cycle, ranked, chosen.need_id, False, None, True, "claim lost"
            )

        # Blind execution: the callback does the real work (P07 wires the
        # SimpleAudit executor in later).
        result = self.execute(chosen) or {}
        verified = bool(result.get("verified", False))
        fulfilled = self.broker.fulfill(
            chosen.need_id,
            str(result.get("artifact_id", "")),
            lease,
            verified=verified,
        )
        return CycleResult(
            self._cycle, ranked, chosen.need_id, True, fulfilled, False, None
        )

    def run(self, max_cycles: int, evidence: Any = None) -> List[CycleResult]:
        """Run up to ``max_cycles`` passes (stop early on clean abstain)."""
        results: List[CycleResult] = []
        for _ in range(max_cycles):
            res = self.cycle(evidence)
            if res is None:
                break
            results.append(res)
        return results


__all__ = ["NeedWorker", "CycleResult"]
