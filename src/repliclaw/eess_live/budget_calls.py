"""Per-LLM-call usage accounting for the live EESS arms (P08 contract §3).

The arm's ``BudgetLedger`` (P05) enforces the matched-budget envelope at the
arm level; this module produces the PER-CALL ``budget_ledger.json`` record
that the P08 artifact contract demands (one entry per LLM call, with the
endpoint's reported usage).

Usage-invalidation rule (judge item 7 / prereg §5.3): if the endpoint omits
the usage fields for a call, the call is recorded with ``usage_present=False``
and the run is marked ``invalid_usage`` — it is never zero-filled and never
silently estimated.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from ..comparators.budget import BudgetEnvelope


class InvalidUsageError(Exception):
    """A call came back without usable usage fields — the run is void."""


@dataclass
class UsageSnapshot:
    """A point-in-time copy of the client's cumulative usage counters."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    llm_calls: int = 0


def usage_snapshot(client: Any) -> UsageSnapshot:
    u = client.usage
    return UsageSnapshot(
        prompt_tokens=int(u.prompt_tokens),
        completion_tokens=int(u.completion_tokens),
        total_tokens=int(u.total_tokens),
        llm_calls=int(u.llm_calls),
    )


def usage_delta(before: UsageSnapshot, after: UsageSnapshot) -> UsageSnapshot:
    return UsageSnapshot(
        prompt_tokens=after.prompt_tokens - before.prompt_tokens,
        completion_tokens=after.completion_tokens - before.completion_tokens,
        total_tokens=after.total_tokens - before.total_tokens,
        llm_calls=after.llm_calls - before.llm_calls,
    )


def usage_present(d: UsageSnapshot) -> bool:
    """True iff the endpoint actually reported nonzero usage for the call."""
    return d.prompt_tokens > 0 or d.completion_tokens > 0


def build_budget_ledger(envelope: BudgetEnvelope, calls: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Assemble the ``p08.budget_ledger/1`` document from per-call records.

    ``calls`` entries need: ``agent_id``, ``prompt_tokens``,
    ``completion_tokens``, ``total_tokens``, ``wall_s``, ``usage_present``
    (``seq`` is assigned here, in order).
    """
    numbered = []
    tot = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "llm_calls": 0, "wall_s": 0.0}
    for i, c in enumerate(calls, start=1):
        rec = {
            "seq": i,
            "agent_id": c["agent_id"],
            "prompt_tokens": int(c["prompt_tokens"]),
            "completion_tokens": int(c["completion_tokens"]),
            "total_tokens": int(c["total_tokens"]),
            "wall_s": round(float(c["wall_s"]), 6),
            "usage_present": bool(c["usage_present"]),
        }
        numbered.append(rec)
        tot["prompt_tokens"] += rec["prompt_tokens"]
        tot["completion_tokens"] += rec["completion_tokens"]
        tot["total_tokens"] += rec["total_tokens"]
        tot["llm_calls"] += 1
        tot["wall_s"] += rec["wall_s"]
    return {
        "schema": "p08.budget_ledger/1",
        "envelope": {
            "max_tokens": envelope.max_tokens,
            "max_wall_s": envelope.max_wall_s,
            "max_agents": envelope.max_agents,
            "sha256": envelope.sha256(),
        },
        "calls": numbered,
        "totals": {**tot, "wall_s": round(tot["wall_s"], 6)},
        "overflow_events": [],
    }


__all__ = [
    "InvalidUsageError",
    "UsageSnapshot",
    "usage_snapshot",
    "usage_delta",
    "usage_present",
    "build_budget_ledger",
]
