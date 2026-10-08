"""Matched-budget envelope + ledger for P05 comparators.

The comparison between the EESS swarm and its comparator baselines is only
valid at MATCHED budgets: every arm must be given the SAME declared
token/time/agent budget envelope, and no arm may consume more than it was
declared. This module is the mechanism that enforces and proves that
property.

- ``BudgetEnvelope`` — the frozen, content-addressed declaration of the
  shared budget (max tokens, max wall-clock seconds, max agents).
- ``BudgetRecord``   — one arm's observed consumption.
- ``BudgetLedger``   — accumulates records against an envelope and raises
  ``BudgetOverflow`` the moment any cap would be exceeded.

Canonical hashing reuses ``repliclaw.canonical`` (byte-stable, sort_keys,
compact separators, UTF-8) so the envelope hash is stable across runs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field

from .. import canonical


class BudgetOverflow(Exception):
    """Raised when an arm's consumption would exceed the declared envelope."""


class BudgetEnvelope(BaseModel):
    """The declared, shared budget envelope for a matched-budget comparison.

    Frozen: once constructed, an arm cannot widen its own budget. The
    ``sha256()`` content hash is what the parity check compares across arms —
    identical envelopes must hash identically.
    """

    model_config = ConfigDict(frozen=True)

    max_tokens: int = Field(default=10_000, ge=0)
    max_wall_s: float = Field(default=30.0, ge=0.0)
    max_agents: int = Field(default=3, ge=1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_tokens": self.max_tokens,
            "max_wall_s": self.max_wall_s,
            "max_agents": self.max_agents,
        }

    def sha256(self) -> str:
        """Content hash of the canonical envelope declaration."""
        return canonical.commit_hash(self.to_dict())


@dataclass(frozen=True)
class BudgetRecord:
    """One arm's observed consumption against the envelope.

    ``n_agents`` is the number of distinct investigators the arm deployed;
    the ledger sums it so the agent cap is enforced per-arm (an arm that
    deploys more agents than the envelope allows overruns the budget).
    """

    agent_id: str
    tokens: int = 0
    wall_s: float = 0.0
    n_agents: int = 1


class BudgetLedger:
    """Accumulates ``BudgetRecord``s and enforces the envelope's caps.

    A ledger is bound to ONE envelope. Calling :meth:`record` with a value
    that would push any cumulative total past its cap raises
    :class:`BudgetOverflow` immediately (fail-loud, never silently faked).
    """

    def __init__(self, envelope: BudgetEnvelope):
        self.envelope = envelope
        self._records: list[BudgetRecord] = []
        self._tokens = 0
        self._wall_s = 0.0
        self._agents = 0

    def record(self, rec: BudgetRecord) -> None:
        new_tokens = self._tokens + rec.tokens
        new_wall = self._wall_s + rec.wall_s
        new_agents = self._agents + rec.n_agents
        if new_tokens > self.envelope.max_tokens:
            raise BudgetOverflow(
                f"token budget exceeded: {new_tokens} > {self.envelope.max_tokens}"
            )
        if new_wall > self.envelope.max_wall_s + 1e-9:
            raise BudgetOverflow(
                f"wall-clock budget exceeded: {new_wall:.4f} > {self.envelope.max_wall_s}"
            )
        if new_agents > self.envelope.max_agents:
            raise BudgetOverflow(
                f"agent budget exceeded: {new_agents} > {self.envelope.max_agents}"
            )
        self._tokens = new_tokens
        self._wall_s = new_wall
        self._agents = new_agents
        self._records.append(rec)

    @property
    def total_tokens(self) -> int:
        return self._tokens

    @property
    def total_wall_s(self) -> float:
        return self._wall_s

    @property
    def n_agents(self) -> int:
        return self._agents

    @property
    def exhausted(self) -> bool:
        return (
            self._tokens >= self.envelope.max_tokens
            or self._wall_s >= self.envelope.max_wall_s - 1e-9
            or self._agents >= self.envelope.max_agents
        )

    def records(self) -> list[BudgetRecord]:
        return list(self._records)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "envelope_sha256": self.envelope.sha256(),
            "total_tokens": self._tokens,
            "total_wall_s": round(self._wall_s, 6),
            "n_agents": self._agents,
            "exhausted": self.exhausted,
        }


__all__ = [
    "BudgetEnvelope",
    "BudgetLedger",
    "BudgetOverflow",
    "BudgetRecord",
]
