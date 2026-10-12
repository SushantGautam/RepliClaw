"""Pre-reveal isolation guard for partitioned evidence (indepinfo Part A).

Boundary model
--------------
- The runner (orchestrator) holds the full :class:`Evidence` and the
  :class:`EscrowLedger`; it never hands either to an investigator.
- Each investigator receives exactly one :class:`InvestigatorView`, bound to
  ``(agent_id, source_id)``. The view is the ONLY read path for that
  investigator:

  * ``my_partition()`` / ``read_partition(source_id)`` — cross-partition
    reads raise :class:`IsolationViolation` (always, in every phase: the
    evidence partitioning IS the experimental condition).
  * ``read_packet(agent_id, packet_id)`` — ANY packet read before the
    REVEAL phase raises :class:`IsolationViolation` (cross-agent AND
    self); after reveal, only packets that were actually revealed (published
    by the ledger) are readable — reveal is the disclosure boundary.
  * ``commit(packet)`` — the only commit path; enforces that the packet
    belongs to this investigator and this case, and that its
    ``prior_evidence_snapshot_sha256`` equals the hash of THIS view's own
    partition (a packet hashed from any aggregate/global vector is
    rejected).

Sealing itself is NOT reimplemented here: commits go straight through
:class:`repliclaw.escrow.EscrowLedger`.
"""
from __future__ import annotations

import json
from typing import Optional

from repliclaw.escrow import EscrowLedger, PacketCommitment, Phase, PredictionPacket

from .evidence import Evidence, EvidencePartition, partition_for_source


class IsolationViolation(RuntimeError):
    """Raised on any attempt to cross the evidence/packet isolation boundary."""


class PartitionVault:
    """Runner-side holder of the full evidence + ledger; issues views.

    The vault is the single place that can see all sources. Investigators
    never receive the vault — only their :class:`InvestigatorView`.
    """

    def __init__(self, evidence: Evidence, ledger: EscrowLedger, case_id: str) -> None:
        if case_id != evidence.case_id:
            raise ValueError(
                f"case_id {case_id!r} does not match evidence.case_id {evidence.case_id!r}"
            )
        self.evidence = evidence
        self.ledger = ledger
        self.case_id = case_id

    @property
    def phase(self) -> Phase:
        return self.ledger.gate.phase

    def view_for(self, agent_id: str, source_id: str) -> "InvestigatorView":
        """Issue the view for one investigator (fails fast on bad source)."""
        partition_for_source(self.evidence, source_id)
        return InvestigatorView(self, agent_id, source_id)

    def open_reveal(self) -> None:
        """COMMIT -> REVEAL boundary (delegates to the escrow ledger)."""
        self.ledger.open_reveal(self.case_id)


class InvestigatorView:
    """The ONLY evidence/packet read path for one investigator."""

    def __init__(self, vault: PartitionVault, agent_id: str, source_id: str) -> None:
        self._vault = vault
        self.agent_id = agent_id
        self.source_id = source_id

    @property
    def case_id(self) -> str:
        return self._vault.case_id

    @property
    def case_brief(self) -> str:
        """Shared task description (not evidence; safe for all investigators)."""
        return self._vault.evidence.case_brief

    @property
    def phase(self) -> Phase:
        return self._vault.phase

    # -- evidence ----------------------------------------------------------
    def my_partition(self) -> EvidencePartition:
        """This investigator's own partition (the only one it may see)."""
        return partition_for_source(self._vault.evidence, self.source_id)

    def read_partition(self, source_id: str) -> EvidencePartition:
        """Read a partition. Cross-partition reads are ALWAYS blocked."""
        if source_id != self.source_id:
            raise IsolationViolation(
                f"investigator {self.agent_id!r} attempted to read partition "
                f"{source_id!r}; only its own partition {self.source_id!r} is accessible"
            )
        return self.my_partition()

    # -- packets -----------------------------------------------------------
    def read_packet(self, agent_id: str, packet_id: str) -> Optional[PredictionPacket]:
        """Read a packet. Pre-reveal: blocked for everyone (including self).

        Post-reveal: only packets that were actually revealed (published by
        the ledger) are readable — reveal is the disclosure boundary.
        """
        if self._vault.phase is Phase.COMMIT:
            raise IsolationViolation(
                f"investigator {self.agent_id!r} attempted to read packet "
                f"{packet_id!r} (agent {agent_id!r}) before the REVEAL phase"
            )
        revealed = (
            self._vault.ledger.root / "revealed" / self.case_id / f"{packet_id}.json"
        )
        if not revealed.exists():
            raise IsolationViolation(
                f"packet {packet_id!r} (agent {agent_id!r}) is not revealed; "
                "only revealed packets are readable"
            )
        return PredictionPacket.model_validate(
            json.loads(revealed.read_text(encoding="utf-8"))
        )

    # -- commit ------------------------------------------------------------
    def commit(self, packet: PredictionPacket) -> PacketCommitment:
        """Commit this investigator's packet through the escrow ledger.

        Enforces, before touching the ledger:
        - the packet belongs to this investigator and this case;
        - ``prior_evidence_snapshot_sha256`` equals the hash of THIS view's
          own partition (rejects packets hashed from aggregates/globals).
        """
        if packet.agent_id != self.agent_id:
            raise IsolationViolation(
                f"packet agent_id {packet.agent_id!r} != view agent_id {self.agent_id!r}"
            )
        if packet.case_id != self.case_id:
            raise IsolationViolation(
                f"packet case_id {packet.case_id!r} != case {self.case_id!r}"
            )
        expected = self.my_partition().snapshot_sha256
        if packet.prior_evidence_snapshot_sha256 != expected:
            raise IsolationViolation(
                f"packet {packet.packet_id!r} prior_evidence_snapshot_sha256 does not "
                f"match this investigator's own partition hash; the packet was "
                "apparently computed from evidence outside its partition"
            )
        return self._vault.ledger.commit(self.agent_id, packet)


__all__ = ["IsolationViolation", "InvestigatorView", "PartitionVault"]
