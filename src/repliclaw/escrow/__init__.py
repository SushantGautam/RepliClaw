"""Evidence escrow: pre-outcome commitments, phase-gated reveal, ledger.

EESS contract §1–§3, ticket P03. Public surface:

- :class:`PredictionPacket` / :class:`PacketCommitment`,
  :func:`commitment_hash`, :func:`project_commitment`
- :class:`Phase`, :class:`PhaseGate`, :class:`PhaseViolation`
- :class:`EscrowLedger`, :class:`EvidenceObservation`, :func:`verify_ledger`
"""
from __future__ import annotations

from repliclaw.escrow.ledger import (
    DuplicateCommitment,
    EscrowLedger,
    EvidenceObservation,
    LedgerError,
    RevealResult,
    verify_ledger,
)
from repliclaw.escrow.packet import (
    PACKET_SCHEMA,
    EstimatedCost,
    PacketCommitment,
    PredictionPacket,
    canonical_bytes,
    commitment_hash,
    project_commitment,
)
from repliclaw.escrow.phase import PHASE_ACTIONS, Phase, PhaseGate, PhaseViolation

__all__ = [
    "PACKET_SCHEMA",
    "EstimatedCost",
    "PredictionPacket",
    "PacketCommitment",
    "canonical_bytes",
    "commitment_hash",
    "project_commitment",
    "Phase",
    "PhaseGate",
    "PhaseViolation",
    "PHASE_ACTIONS",
    "EscrowLedger",
    "EvidenceObservation",
    "RevealResult",
    "LedgerError",
    "DuplicateCommitment",
    "verify_ledger",
]
