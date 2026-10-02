"""Per-LLM-call budget accounting for the live EESS arms (P08 contract §3).

The P08 ``budget_ledger.json`` records one entry per LLM *call* (prompt /
completion / total tokens, wall seconds, and whether the provider reported
usage at all). That is finer-grained than the P05 ``BudgetLedger`` which
accumulates per-arm records. This module wraps the shared, fail-loud
:class:`repliclaw.comparators.budget.BudgetLedger` so that the SAME envelope
enforcement (``BudgetOverflow`` on any cap) applies to live per-call
consumption, and adds the per-call detail the artifact contract requires.

Two deliberate semantic choices (both justified in the P08 contract):

* **Agent cap is enforced over DISTINCT agents, not per-call.** A swarm of
  3 agents making many calls must not be aborted because 3 agents x N calls
  > the 3-agent ceiling. The shared ledger's per-record ``n_agents`` is
  therefore passed as ``0`` on live calls and the distinct-agent set is
  tracked here (raising :class:`BudgetOverflow` past ``max_agents``).
* **Missing usage invalidates, it is never zero-filled** (science-judge Q13
  / item 7). A call whose provider usage delta is zero is recorded with
  ``usage_present=False``; the harness marks the run ``invalid_usage``. We do
  NOT silently count a missing-usage call as 0 tokens and call it compliant.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from ..comparators.budget import (
    BudgetEnvelope,
    BudgetLedger,
    BudgetOverflow,
    BudgetRecord,
)


class UsageMissingError(RuntimeError):
    """A client returned a response with no usage object at all (Q13).

    Distinct from a zero-usage delta (recorded as ``usage_present=False``):
    this means the client itself never exposed usage, so the run cannot be
    accounted and is void.
    """


@dataclass
class LiveCall:
    """One LLM call's observed consumption (P08 budget_ledger.json ``calls[]``)."""

    seq: int
    agent_id: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    wall_s: float
    usage_present: bool
    purpose: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seq": self.seq,
            "agent_id": self.agent_id,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "wall_s": round(self.wall_s, 6),
            "usage_present": self.usage_present,
        }


class LiveBudgetLedger(BudgetLedger):
    """A :class:`BudgetLedger` that also accumulates per-LLM-call detail.

    Token and wall-clock caps are enforced by delegating to the parent
    :meth:`record` (which raises :class:`BudgetOverflow` fail-loud); the
    agent cap is enforced over the set of distinct agents that have made a
    call. Per-call records are kept for the ``budget_ledger.json`` artifact.
    """

    def __init__(self, envelope: BudgetEnvelope) -> None:
        super().__init__(envelope)
        self.calls: List[LiveCall] = []
        self.overflow_events: List[Dict[str, Any]] = []
        self._agent_ids: set = set()

    def record_live_call(
        self,
        agent_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        wall_s: float,
        purpose: str = "",
        usage_present: bool = True,
    ) -> LiveCall:
        """Record one LLM call against the envelope (fail-loud on overrun)."""
        total = (int(prompt_tokens) + int(completion_tokens)) if usage_present else 0
        # Agent cap: one count per DISTINCT agent (not per call).
        if agent_id not in self._agent_ids:
            if len(self._agent_ids) + 1 > self.envelope.max_agents:
                raise BudgetOverflow(
                    f"agent budget exceeded: {len(self._agent_ids) + 1} > "
                    f"{self.envelope.max_agents}"
                )
            self._agent_ids.add(agent_id)
        # Token + wall caps: delegated to the shared, fail-loud ledger.
        super().record(BudgetRecord(agent_id=agent_id, tokens=total, wall_s=wall_s, n_agents=0))
        call = LiveCall(
            seq=len(self.calls) + 1,
            agent_id=agent_id,
            prompt_tokens=int(prompt_tokens),
            completion_tokens=int(completion_tokens),
            total_tokens=total,
            wall_s=wall_s,
            usage_present=bool(usage_present),
            purpose=purpose,
        )
        self.calls.append(call)
        return call

    def record_overflow(self, message: str, kind: str) -> None:
        """Append a budget-overflow event (called by the arm on abort)."""
        self.overflow_events.append(
            {
                "kind": kind,
                "message": message,
                "tokens_at_event": self.total_tokens,
                "llm_calls_at_event": len(self.calls),
            }
        )

    def record_overflow_call(
        self,
        agent_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        wall_s: float,
        purpose: str = "",
        usage_present: bool = True,
        message: str = "",
        kind: str = "budget_exhausted",
    ) -> LiveCall:
        """Record the call that TRIPPED the budget, then the overflow event.

        When :meth:`record_live_call` raises :class:`BudgetOverflow` the
        parent ledger has NOT mutated (fail-loud before state change) and the
        offending call is not in ``self.calls``. This appends that call — with
        its REAL, never-zero-filled usage — so the ``aborted_budget`` run's
        ``budget_ledger.json`` still shows the consumption that caused the
        abort, and appends the overflow event. The parent's cumulative totals
        are left untouched so the fail-loud invariant (no over-budget state is
        ever recorded as compliant) is preserved; ``to_contract_dict`` derives
        its ``totals`` from ``self.calls``, so the artifact stays consistent.
        """
        total = (int(prompt_tokens) + int(completion_tokens)) if usage_present else 0
        if agent_id not in self._agent_ids:
            self._agent_ids.add(agent_id)
        call = LiveCall(
            seq=len(self.calls) + 1,
            agent_id=agent_id,
            prompt_tokens=int(prompt_tokens),
            completion_tokens=int(completion_tokens),
            total_tokens=total,
            wall_s=wall_s,
            usage_present=bool(usage_present),
            purpose=purpose,
        )
        self.calls.append(call)
        self.record_overflow(message, kind)
        return call

    @property
    def distinct_agents(self) -> int:
        return len(self._agent_ids)

    def to_contract_dict(self) -> Dict[str, Any]:
        """The exact ``p08.budget_ledger/1`` schema (P08 contract §3)."""
        return {
            "schema": "p08.budget_ledger/1",
            "envelope": {**self.envelope.to_dict(), "sha256": self.envelope.sha256()},
            "calls": [c.to_dict() for c in self.calls],
            "totals": {
                "prompt_tokens": sum(c.prompt_tokens for c in self.calls),
                "completion_tokens": sum(c.completion_tokens for c in self.calls),
                "total_tokens": sum(c.total_tokens for c in self.calls),
                "llm_calls": len(self.calls),
                "wall_s": round(sum(c.wall_s for c in self.calls), 6),
            },
            "overflow_events": list(self.overflow_events),
        }


__all__ = ["LiveBudgetLedger", "LiveCall"]
