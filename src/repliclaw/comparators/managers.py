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

from typing import Any, Callable

from ..models import InvestigatorConfig
from .arms import ArmRunner


class SingleAgentBaseline(ArmRunner):
    """S0 — one strong agent, no peers, no aggregation."""

    strategy = "single_agent"
    n_agents = 1
    arm_label = "single_agent"

    def __init__(self, investigator_factory: Callable[[InvestigatorConfig], Any]):
        super().__init__(investigator_factory)


class AdaptiveCentralManager(ArmRunner):
    """S3 — a STRONG adaptive central manager (equal concurrency).

    Deploys the full investigator pipeline and adapts its plan as evidence
    arrives. This is the "strong" comparator: it is not a naive single agent
    and not a fixed DAG — it re-plans from the evidence it has gathered, which
    is exactly what the EESS swarm does, so the comparison isolates the
    decentralized-vs-central coordination choice at matched budgets.
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


__all__ = [
    "SingleAgentBaseline",
    "AdaptiveCentralManager",
    "OpenSharingSwarm",
]
