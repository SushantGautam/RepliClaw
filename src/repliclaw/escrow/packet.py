"""Prediction packets and escrow commitments (EESS contract §1).

A :class:`PredictionPacket` is the full, private, pre-outcome commitment an
agent makes to a falsifiable hypothesis. Only the public projection
(:class:`PacketCommitment`) may appear before the reveal boundary — and the
projection is asserted, at byte level, to carry none of the statement,
prediction, refutation or competing-explanation content.

Canonical form (contract §1): ``json.dumps(obj, sort_keys=True,
separators=(",", ":"))`` encoded UTF-8. This module reuses
:mod:`repliclaw.canonical`, which implements exactly that form.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator

from repliclaw.canonical import canonical_json, sha256_hex

PACKET_SCHEMA = "repliclaw.prediction_packet/v1"


class EstimatedCost(BaseModel):
    """Budget the agent forecasts for the intervention (contract §1)."""

    tokens: Optional[int] = None
    wall_s: float = 0.0

    model_config = {"frozen": True}


class PredictionPacket(BaseModel):
    """Full private prediction packet (contract §1, frozen schema v1)."""

    schema_: str = Field(default=PACKET_SCHEMA, alias="schema")
    packet_id: str
    case_id: str
    agent_id: str
    hypothesis_id: str
    hypothesis_version: int = Field(ge=1)
    hypothesis_statement: str
    intervention_id: str
    predicted_outcome: str
    refutation_criterion: str
    estimated_cost: EstimatedCost = Field(default_factory=EstimatedCost)
    competing_explanation: str
    prior_evidence_snapshot_sha256: str

    model_config = {"populate_by_name": True, "frozen": True}

    @field_validator("packet_id")
    @classmethod
    def _packet_id_is_uuid4_hex(cls, v: str) -> str:
        if len(v) != 32 or any(c not in "0123456789abcdef" for c in v.lower()):
            raise ValueError("packet_id must be a uuid4 hex string")
        return v

    @field_validator(
        "hypothesis_statement",
        "predicted_outcome",
        "refutation_criterion",
        "competing_explanation",
    )
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("packet fields must be non-empty")
        return v

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True)

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict()).encode("utf-8")


def canonical_bytes(packet: PredictionPacket) -> bytes:
    """Canonical UTF-8 bytes of the full packet (contract §1)."""
    return packet.canonical_bytes()


def commitment_hash(packet: PredictionPacket) -> str:
    """SHA-256 hex of the packet's canonical bytes."""
    return sha256_hex(packet.canonical_bytes())


class PacketCommitment(BaseModel):
    """Public pre-reveal projection of a packet (contract §1).

    Public content before reveal is ONLY (packet_id, commitment_sha256,
    committed_at, agent_id, hypothesis_id, intervention_id, case_id, phase).
    Never the statement/prediction/refutation/competing-explanation text.
    """

    packet_id: str
    agent_id: str
    case_id: str
    commitment_sha256: str
    committed_at: str
    phase: str
    hypothesis_id: str
    intervention_id: str

    model_config = {"frozen": True}

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    def canonical_bytes(self) -> bytes:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )


def project_commitment(
    packet: PredictionPacket, commitment_sha256: str, committed_at: str, phase: str
) -> PacketCommitment:
    """Build the public projection, asserting no private bytes leak.

    Byte-level assertion: the projection's canonical bytes must not contain
    any of the packet's private statement bytes. The private fields are long,
    unique sentences by contract, so a full-substring containment check is
    the intended guard (a short statement could theoretically collide with
    an unrelated field, but the contract makes them distinctive sentences).
    """
    proj = PacketCommitment(
        packet_id=packet.packet_id,
        agent_id=packet.agent_id,
        case_id=packet.case_id,
        commitment_sha256=commitment_sha256,
        committed_at=committed_at,
        phase=phase,
        hypothesis_id=packet.hypothesis_id,
        intervention_id=packet.intervention_id,
    )
    projected = proj.canonical_bytes()
    for secret in (
        packet.hypothesis_statement,
        packet.predicted_outcome,
        packet.refutation_criterion,
        packet.competing_explanation,
    ):
        if secret.encode("utf-8") in projected:
            raise ValueError(
                f"public projection for {packet.packet_id} leaks private packet bytes"
            )
    return proj


__all__ = [
    "PACKET_SCHEMA",
    "EstimatedCost",
    "PredictionPacket",
    "PacketCommitment",
    "canonical_bytes",
    "commitment_hash",
    "project_commitment",
]
