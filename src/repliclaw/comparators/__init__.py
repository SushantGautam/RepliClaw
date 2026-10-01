"""P05 — matched-budget comparator baselines against the EESS swarm.

The comparison is only valid at MATCHED budgets: every arm consumes the same
declared token/time/agent budget envelope. This package provides:

- the budget envelope + ledger (``budget``) that enforces and proves parity;
- the common arm interface + result schema (``arms``);
- the three named comparator arms (``managers``): the S0 single-agent
  baseline, the S3 strong adaptive central manager, and the S4 open-sharing
  swarm;
- the harness + parity proof (``runner``).

The arms reuse the shared coordination baselines in ``repliclaw.strategies``
so the scientific task and verdict engine are identical across arms — only
the coordination regime differs.
"""
from __future__ import annotations

from .arms import ArmResult, ArmRunner, ArmSpec, ComparatorArm
from .budget import BudgetEnvelope, BudgetLedger, BudgetOverflow, BudgetRecord
from .managers import AdaptiveCentralManager, OpenSharingSwarm, SingleAgentBaseline
from .runner import ComparatorHarness, arm_registry, assert_budget_parity

__all__ = [
    "AdaptiveCentralManager",
    "ArmResult",
    "ArmRunner",
    "ArmSpec",
    "BudgetEnvelope",
    "BudgetLedger",
    "BudgetOverflow",
    "BudgetRecord",
    "ComparatorArm",
    "ComparatorHarness",
    "OpenSharingSwarm",
    "SingleAgentBaseline",
    "arm_registry",
    "assert_budget_parity",
]
