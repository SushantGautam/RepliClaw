"""Phase gate for the evidence-escrow lifecycle (EESS ticket P03).

Phases form a strict forward chain: ``COMMIT -> REVEAL -> EXECUTE -> RESOLVE``.
The gate is PER-RUN: one forward transition at a time, every transition
recorded as a ``phase_transition`` event by the ledger (contract §2). Out-of
order actions raise :class:`PhaseViolation`.
"""
from __future__ import annotations

from enum import IntEnum
from typing import Dict


class Phase(IntEnum):
    """Ordered escrow phases (strict forward chain)."""

    COMMIT = 0
    REVEAL = 1
    EXECUTE = 2
    RESOLVE = 3


# Actions permitted in each phase (the allow-list; anything else violates).
PHASE_ACTIONS: Dict[Phase, frozenset[str]] = {
    Phase.COMMIT: frozenset({"commit"}),
    Phase.REVEAL: frozenset({"reveal"}),
    Phase.EXECUTE: frozenset({"publish_evidence"}),
    Phase.RESOLVE: frozenset({"publish_evidence"}),
}


class PhaseViolation(RuntimeError):
    """Raised when an action is not legal in the current phase."""

    def __init__(self, agent_id: str, action: str, phase: Phase) -> None:
        self.agent_id = agent_id
        self.action = action
        self.phase = phase
        super().__init__(
            f"agent {agent_id!r}: action {action!r} not allowed in phase {phase.name}"
        )


class PhaseGate:
    """Monotonic, single-runner phase state machine (per run/case).

    The gate tracks only the current phase; the *ledger* persists each
    transition as a ``phase_transition`` event, so a crashed writer can be
    reconstructed from the event log and the gate re-derived.
    """

    def __init__(self, phase: Phase = Phase.COMMIT) -> None:
        self._phase = phase

    @property
    def phase(self) -> Phase:
        return self._phase

    def assert_can(self, agent_id: str, action: str) -> None:
        """Raise :class:`PhaseViolation` if ``action`` is illegal now."""
        if action not in PHASE_ACTIONS[self._phase]:
            raise PhaseViolation(agent_id, action, self._phase)

    def advance(self) -> Phase:
        """One forward transition; RESOLVE is terminal."""
        if self._phase is Phase.RESOLVE:
            raise PhaseViolation("gate", "advance", self._phase)
        self._phase = Phase(self._phase.value + 1)
        return self._phase

    def set_from_history(self, history: "list[Phase]") -> None:
        """Rebuild the gate from a persisted phase-transition history.

        Used when reconstructing a ledger from disk after a crash: the event
        log is the source of truth, and the gate is a pure function of it.
        """
        if not history:
            self._phase = Phase.COMMIT
            return
        prev = Phase.COMMIT
        for ph in history:
            if ph.value != prev.value + 1:
                raise PhaseViolation("history", f"jump {prev.name} -> {ph.name}", prev)
            prev = ph
        self._phase = prev


__all__ = ["Phase", "PhaseGate", "PhaseViolation", "PHASE_ACTIONS"]
