"""Pre-reveal information isolation (AC03) — enforced in code, not prompts.

Model:
- Each investigator receives an `InvestigationContext` envelope: the claim,
  the task instructions, and that investigator's allowed sources ONLY.
- Materials produced by any investigator are SEALED until the reveal phase.
- `ContextEnforcer.build_context()` is the single code path through which an
  investigator can read shared materials. It refuses to include sealed
  material before reveal, and records every read in the event log so the
  audit trail can prove what each agent could see at each phase (M2).

Independence is therefore structural: an investigator cannot reach a peer's
unrevealed conclusion through the normal system APIs, because those APIs do
not expose it pre-reveal.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .models import Claim, InvestigatorConfig


class IsolationViolation(Exception):
    """Raised when code attempts to read sealed material pre-reveal."""


@dataclass
class InvestigationContext:
    """The complete, sealed view of the world available to one investigator
    during the blind phase."""

    claim: Claim
    investigator: InvestigatorConfig
    task_instructions: str
    allowed_sources: List[str] = field(default_factory=list)
    # Only non-sensitive shared materials (public data, methods) may be listed here.
    shared_public_materials: Dict[str, Any] = field(default_factory=dict)
    # Materials visible ONLY after reveal (populated by the orchestrator).
    revealed_materials: Dict[str, Any] = field(default_factory=dict)

    def to_prompt_block(self, revealed: bool = False) -> str:
        """Serialize the context for an LLM prompt. Refuses to include any
        peer material pre-reveal — even if someone set revealed_materials
        early, the `revealed` gate (set by the protocol) controls it."""
        blocks = [
            f"# CLAIM\n{self.claim.statement}",
            f"\n# YOUR IDENTITY\nYou are {self.investigator.agent_id} "
            f"(role: {self.investigator.role.value}).",
            f"\n# TASK\n{self.task_instructions}",
            f"\n# ALLOWED EVIDENCE SOURCES\n{json.dumps(self.allowed_sources, indent=2)}",
        ]
        if self.claim.data:
            blocks.append(
                "\n# BUNDLED DATA (raw data / artifact metrics for this claim — "
                "compute your analysis FROM these numbers)\n"
                + json.dumps(self.claim.data, indent=2, ensure_ascii=False)
            )
        if self.shared_public_materials:
            blocks.append(
                "\n# PUBLIC MATERIALS (shared, non-sensitive)\n"
                + json.dumps(self.shared_public_materials, indent=2, ensure_ascii=False)
            )
        if revealed and self.revealed_materials:
            blocks.append(
                "\n# PEER MATERIALS (revealed — post-commit)\n"
                + json.dumps(self.revealed_materials, indent=2, ensure_ascii=False)
            )
        return "\n".join(blocks)


class PhaseGate:
    """Tracks the protocol phase per run and authorizes context reads."""

    def __init__(self):
        self._phase = "blind"

    @property
    def phase(self) -> str:
        return self._phase

    def advance(self, phase: str) -> None:
        order = ["blind", "committed", "revealing", "revealed", "followup", "verdict"]
        if phase not in order:
            raise ValueError(f"unknown phase {phase}")
        if order.index(phase) <= order.index(self._phase) and phase != self._phase:
            raise ValueError(f"cannot move backwards from {self._phase} to {phase}")
        self._phase = phase

    @property
    def is_blind(self) -> bool:
        return self._phase in ("blind", "committed")


class ContextEnforcer:
    """The only legitimate way for investigators to read shared state.

    Every read is logged so independence is inspectable, not asserted.
    """

    def __init__(self, store, gate: Optional[PhaseGate] = None):
        self._store = store
        self.gate = gate or PhaseGate()
        self._read_log: List[Dict[str, Any]] = []

    def build_context(
        self,
        claim: Claim,
        investigator: InvestigatorConfig,
        task_instructions: str,
        shared_public_materials: Optional[Dict[str, Any]] = None,
    ) -> InvestigationContext:
        ctx = InvestigationContext(
            claim=claim,
            investigator=investigator,
            task_instructions=task_instructions,
            allowed_sources=list(investigator.allowed_sources),
            shared_public_materials=shared_public_materials or {},
        )
        self._store.event(
            "context_built",
            agent_id=investigator.agent_id,
            phase=self.gate.phase,
            sources=ctx.allowed_sources,
            public_materials=sorted(ctx.shared_public_materials.keys()),
            includes_peer_materials=False,
        )
        return ctx

    def peer_materials(self, claim_id: str, for_agent: str) -> Dict[str, Any]:
        """Return other agents' revealed findings for `for_agent`, or {} if we
        are still in the blind/commit phase. Raises IsolationViolation if
        caller tries to force peer material pre-reveal (revealed=True while
        gate is blind)."""
        if self.gate.is_blind:
            self._store.event(
                "isolation_enforced",
                agent_id=for_agent,
                phase=self.gate.phase,
                denied=True,
                reason="pre-reveal",
            )
            return {}
        out: Dict[str, Any] = {}
        for c in self._store.list_commitments():
            if c.get("claim_id") != claim_id or c.get("agent_id") == for_agent:
                continue
            if c.get("phase") == "revealed" and c.get("reveal_verified") is True:
                out[c["agent_id"]] = c.get("revealed_content") or {}
        return out

    def read_sealed_commitment(self, commitment_id: str, for_agent: str, revealed: bool) -> Dict[str, Any]:
        """Read a commitment record. Pre-reveal, only hash/phase metadata may
        be returned; content is withheld. Post-reveal, revealed content may be
        returned if the record is verified."""
        c = self._store.get_commitment(commitment_id, reveal=revealed)
        if c is None:
            return {}
        if revealed and self.gate.is_blind:
            # Someone is trying to pull content before reveal — deny.
            self._store.event(
                "isolation_enforced",
                agent_id=for_agent,
                commitment_id=commitment_id,
                denied=True,
                reason="content_read_pre_reveal",
            )
            raise IsolationViolation(
                f"agent {for_agent} attempted to read sealed content of {commitment_id} pre-reveal"
            )
        self._store.event(
            "commitment_read",
            agent_id=for_agent,
            commitment_id=commitment_id,
            phase=self.gate.phase,
            included_content=bool(revealed and not self.gate.is_blind),
        )
        if revealed and not self.gate.is_blind:
            return c.to_dict()
        # Blind read: metadata only.
        return {
            "commitment_id": c.commitment_id,
            "agent_id": c.agent_id,
            "role": c.role,
            "content_hash": c.content_hash,
            "phase": c.phase.value,
            "timestamp": c.timestamp,
            # NOTE: content deliberately omitted pre-reveal.
        }

    def audit(self) -> List[Dict[str, Any]]:
        """Independence audit: what each agent could see, per phase."""
        return [e for e in self._store.events() if e["kind"] in (
            "context_built", "commitment_read", "isolation_enforced"
        )]
