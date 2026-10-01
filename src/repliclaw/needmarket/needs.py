"""Need + capability models for the decentralized task market (contract §4).

A :class:`Need` is an unmet scientific need an agent publishes for others to
claim. :class:`WorkerCapability` is an agent's self-declared capability
(what it can produce, at what budget). :func:`eligible` is a pure,
agent-local self-check — there is no central pre-assignment.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

NEED_SCHEMA = "repliclaw.need/v1"

# Need lifecycle states (contract §4).
NEED_STATUS = ("open", "leased", "done", "cancelled", "expired")


class CostEstimate(BaseModel):
    """Forecast cost of satisfying a need (budget enforcement input)."""

    tokens: Optional[int] = None
    wall_s: float = 0.0

    model_config = {"frozen": True}


class Need(BaseModel):
    """A published, claimable scientific need (contract §4, frozen v1)."""

    schema_: str = Field(default=NEED_SCHEMA, alias="schema")
    need_id: str
    case_id: str
    title: str
    description: str
    proposer_id: str
    proposed_at: str
    required_capability: str
    cost_estimate: CostEstimate = Field(default_factory=CostEstimate)
    status: str = Field(default="open", pattern=r"^(open|leased|done|cancelled|expired)$")

    model_config = {"populate_by_name": True, "frozen": True}

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True)


class WorkerCapability(BaseModel):
    """An agent's self-declared capability (no pre-assignment)."""

    agent_id: str
    producible_types: list[str]
    method_family: str
    model: str
    budget_tokens: Optional[int] = None
    budget_wall_s: Optional[float] = None

    model_config = {"frozen": True}


def eligible(need: Need, capability: WorkerCapability) -> bool:
    """Pure self-check: can this agent, by its own declaration, do this need?

    This is the ONLY eligibility logic and it runs in the agent, not a broker.
    The required_capability is treated as a method-family/type tag; an agent
    is eligible if its method_family matches OR its producible_types cover the
    required capability. No ranking, no allocation.
    """
    if need.status != "open":
        return False
    if need.required_capability == capability.method_family:
        return True
    return need.required_capability in capability.producible_types


__all__ = [
    "NEED_SCHEMA",
    "NEED_STATUS",
    "CostEstimate",
    "Need",
    "WorkerCapability",
    "eligible",
]
