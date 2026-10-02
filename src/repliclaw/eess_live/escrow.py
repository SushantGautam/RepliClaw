"""Escrow layer for the live EESS arms: REAL escrow vs pass-through (A1).

Prereg §3 defines A1 (``eess_no_escrow``) as *identical to S5 with the
escrow replaced by an in-memory pass-through*: no integrity check, no
relevance scoping, and peers see RAW, unfiltered artifacts (the full
committed packets, not just verified/published projections). This module is
the single seam that implements that single-factor change — the arm's run
loop is written ONCE against this interface, so A1 and S5 differ ONLY in
which escrow object they get (prereg: "implement as an option, not a copy").

- :class:`EscrowedEscrow`  — the REAL :class:`EscrowLedger` (commit -> reveal
  gate -> verified reveal -> publish-only-after-verification). Integrity
  rejections (reveal mismatch) are counted. Peers only ever see *published,
  verified* evidence plus public commitment projections.
- :class:`PassThroughEscrow` — the ``EscrowDisabled`` stub (prereg Q10-a):
  commits are stored in memory, there is NO phase gate and NO integrity
  check (every "reveal" passes), and the shared view is the RAW, unfiltered
  set of committed packets + every executed arm's raw artifacts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..escrow import (
    EscrowLedger,
    EvidenceObservation,
    PredictionPacket,
    RevealResult,
)


@dataclass
class RevealOutcome:
    """Arm-level result of one agent's reveal (escrow or pass-through)."""

    agent_id: str
    packet_id: str
    status: str  # "verified" | "mismatch"
    integrity_rejected: bool = False


class LiveEscrow:
    """Interface the live run loop drives (escrow_mode seam)."""

    mode: str = "escrow"

    # lifecycle (mirrors the escrow phase gate) ------------------------------
    def open(self, case_id: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def begin_reveal(self, case_id: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def enter_execute(self) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def resolve(self) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    # commit / reveal -------------------------------------------------------
    def commit(self, agent_id: str, packet: PredictionPacket) -> None:  # pragma: no cover
        raise NotImplementedError

    def reveal(self, agent_id: str, packet: PredictionPacket) -> RevealOutcome:
        raise NotImplementedError  # pragma: no cover

    def read_private_before_reveal(self, agent_id: str, packet_id: str) -> Any:
        """Pre-reveal private read — the escrow MUST refuse this (the gate
        that makes commitments genuinely pre-outcome)."""
        raise NotImplementedError  # pragma: no cover

    # evidence ---------------------------------------------------------------
    def publish_evidence(self, observation: EvidenceObservation) -> None:  # pragma: no cover
        raise NotImplementedError

    def evidence(self) -> List[Dict[str, Any]]:  # pragma: no cover - interface
        raise NotImplementedError

    def raw_artifacts(self) -> Dict[str, Any]:
        """What peers see. Escrow: only verified, published evidence.
        Pass-through: RAW, unfiltered packets + artifacts (no scoping)."""
        raise NotImplementedError  # pragma: no cover

    # accounting -------------------------------------------------------------
    @property
    def integrity_rejections(self) -> int:  # pragma: no cover - interface
        raise NotImplementedError


class EscrowedEscrow(LiveEscrow):
    """The REAL escrow ledger, driven by the live arm (S5)."""

    mode = "escrow"

    def __init__(self, root, worker_id: str = "live-orchestrator") -> None:
        self.ledger = EscrowLedger(root, worker_id=worker_id)
        self._rejections = 0
        self._case_id: Optional[str] = None

    def open(self, case_id: str) -> None:
        self._case_id = case_id

    def begin_reveal(self, case_id: str) -> None:
        # COMMIT -> REVEAL boundary (ledger gate); per-agent reveal() now legal.
        self.ledger.open_reveal(case_id)

    def enter_execute(self) -> None:
        # REVEAL -> EXECUTE boundary (ledger gate).
        self.ledger.enter_execute()

    # -- commit/reveal -------------------------------------------------------
    def commit(self, agent_id: str, packet: PredictionPacket) -> None:
        self.ledger.commit(agent_id, packet)

    def reveal(self, agent_id: str, packet: PredictionPacket) -> RevealOutcome:
        res: RevealResult = self.ledger.reveal(agent_id, packet)
        rejected = res.status != "verified"
        if rejected:
            self._rejections += 1
        return RevealOutcome(
            agent_id=agent_id,
            packet_id=packet.packet_id,
            status=res.status,
            integrity_rejected=rejected,
        )

    def read_private_before_reveal(self, agent_id: str, packet_id: str) -> Any:
        """Delegates to the ledger's GATED private read; in the COMMIT phase
        this raises :class:`PhaseViolation` — that IS the pre-outcome gate."""
        return self.ledger.load_private_packet(agent_id, packet_id)

    # -- evidence -------------------------------------------------------------
    def publish_evidence(self, observation: EvidenceObservation) -> None:
        self.ledger.publish_evidence(observation)

    def evidence(self) -> List[Dict[str, Any]]:
        return self.ledger.evidence()

    def resolve(self) -> None:
        self.ledger.resolve()

    def raw_artifacts(self) -> Dict[str, Any]:
        # Escrow relevance scoping: peers see ONLY verified, published
        # observations (never raw unverified artifacts, never other agents'
        # sealed packets pre-reveal).
        return {"observations": self.ledger.evidence()}

    @property
    def integrity_rejections(self) -> int:
        return self._rejections

    @property
    def events(self) -> List[Dict[str, Any]]:
        return self.ledger.events()


class PassThroughEscrow(LiveEscrow):
    """The ``EscrowDisabled`` stub (A1): no gate, no integrity check.

    Peers see the RAW, unfiltered artifacts: every agent's FULL committed
    packet (statement/prediction/refutation bytes — the very thing escrow
    would keep sealed) plus every executed arm's raw output. There is no
    relevance scoping and no integrity verification, so
    :attr:`integrity_rejections` is always 0 by construction.
    """

    mode = "pass_through"

    def __init__(self) -> None:
        self._packets: Dict[str, PredictionPacket] = {}
        self._evidence: List[Dict[str, Any]] = []
        self._raw_runs: List[Dict[str, Any]] = []

    def open(self, case_id: str) -> None:  # no-op: no phases in pass-through
        return None

    def begin_reveal(self, case_id: str) -> None:  # no-op
        return None

    def enter_execute(self) -> None:  # no-op
        return None

    def commit(self, agent_id: str, packet: PredictionPacket) -> None:
        # Stored unfiltered; immediately visible to every peer (no seal).
        self._packets[packet.packet_id] = packet

    def reveal(self, agent_id: str, packet: PredictionPacket) -> RevealOutcome:
        # No integrity check: a pass-through never rejects. (Even a
        # doctored packet "reveals" cleanly — that is the ablation point.)
        return RevealOutcome(agent_id=agent_id, packet_id=packet.packet_id, status="verified")

    def read_private_before_reveal(self, agent_id: str, packet_id: str) -> Any:
        # No gate: the raw packet is readable at any time by anyone.
        return self._packets.get(packet_id)

    def publish_evidence(self, observation: EvidenceObservation) -> None:
        rec = observation.model_dump(mode="json")
        self._evidence.append(rec)
        self._raw_runs.append(
            {
                "intervention_id": rec.get("data", {}).get("intervention_id"),
                "target_output": rec.get("data", {}).get("target_output"),
                "severity": rec.get("data", {}).get("severity"),
            }
        )

    def evidence(self) -> List[Dict[str, Any]]:
        return list(self._evidence)

    def resolve(self) -> None:  # no-op
        return None

    def raw_artifacts(self) -> Dict[str, Any]:
        # UNFILTERED: raw committed packet bytes + raw arm artifacts, all
        # peers, no integrity check, no relevance scoping (prereg A1 row).
        return {
            "raw_packets": [p.to_dict() for p in self._packets.values()],
            "observations": self._evidence,
            "raw_runs": self._raw_runs,
        }

    @property
    def integrity_rejections(self) -> int:
        return 0

    @property
    def events(self) -> List[Dict[str, Any]]:
        return []


__all__ = [
    "LiveEscrow",
    "RevealOutcome",
    "EscrowedEscrow",
    "PassThroughEscrow",
]
