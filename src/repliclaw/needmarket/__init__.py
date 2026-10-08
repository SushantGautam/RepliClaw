"""Decentralized need market: publish needs, self-rank, atomic leases.

EESS contract §4 + F04 design (NEED_DISPATCH.md §4–§7). Public surface:

- :class:`Need` / :class:`WorkerCapability` / :func:`eligible`
- :class:`NeedBroker` (O_EXCL atomic leases; enforces lease/dedup/budget
  ONLY — never ranks)
- :class:`LocalEigPolicy` / :class:`RandomPolicy` / :class:`GreedySharedPolicy`
- :class:`NeedWorker` (one agent's local choice loop)
- :func:`snapshot` / :func:`replay_events` / :func:`ranking_from_events`
"""
from __future__ import annotations

from repliclaw.needmarket.broker import (
    BrokerError,
    BudgetExhausted,
    Lease,
    NeedBroker,
)
from repliclaw.needmarket.needs import (
    CostEstimate,
    Need,
    WorkerCapability,
    eligible,
)
from repliclaw.needmarket.policy import (
    ActionPolicy,
    GreedySharedPolicy,
    LocalEigPolicy,
    RandomPolicy,
    RankedAction,
)
from repliclaw.needmarket.replay import (
    ranking_from_events,
    replay_events,
    snapshot,
)
from repliclaw.needmarket.worker import CycleResult, NeedWorker

__all__ = [
    "Need",
    "WorkerCapability",
    "CostEstimate",
    "eligible",
    "NeedBroker",
    "Lease",
    "BrokerError",
    "BudgetExhausted",
    "ActionPolicy",
    "RankedAction",
    "LocalEigPolicy",
    "RandomPolicy",
    "GreedySharedPolicy",
    "NeedWorker",
    "CycleResult",
    "snapshot",
    "replay_events",
    "ranking_from_events",
]
