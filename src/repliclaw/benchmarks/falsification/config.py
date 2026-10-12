"""Matched per-claim envelope for the 4-arm falsification comparison.

The scientific question is whether INDEPENDENT EVIDENCE ESCROW (each
investigator sees only its own source, seals a prediction before disclosure,
then reveals and aggregates) helps under fragmented, contradictory, and
deceptive evidence — versus pooled analysis.

For the comparison to be valid, every arm must be matched on:
  * the UNION of evidence available (the escrowed arm's investigators see a
    partition each but collectively all sources; the pooled arms see all);
  * the TOTAL token envelope per claim (summed across an arm's investigators);
  * the TOTAL allowed "experiments" (LLM calls, which bound tool calls);
  * the model, temperature, and seed handling.

This module is the single source of truth for those caps. The unit of
analysis is PER CLAIM: each claim is one "case" for the escrow mechanism, and
every arm processes the same claim under the same envelope.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MatchedCaps:
    """The matched per-claim envelope, identical for all four arms.

    ``total_tokens`` and ``total_calls`` are the ARM-LEVEL totals. A team arm
    with ``n_team`` investigators splits them evenly (``tokens_per_investigator``
    and ``calls_per_investigator``); a single-agent arm uses the full totals.
    Because every tool call consumes one LLM call (turn), ``total_calls`` is a
    hard upper bound on the total number of tool calls any arm may make.
    """

    # Arm-level totals (per claim).
    total_tokens: int = 16000
    total_calls: int = 16
    max_tokens_per_call: int = 1024
    wall_s: float = 300.0

    # Team size for the team arms (escrowed_independent, open_sharing).
    n_team: int = 4

    # open_sharing is two-phase (initial + finalize-after-sharing); the
    # per-phase split keeps the per-investigator total equal to the escrowed
    # arm's per-investigator budget.
    open_sharing_phase_calls: int = 2
    open_sharing_phase_tokens: int = 2000

    # Per-investigator caps for the team arms (derived, kept explicit so the
    # matching is auditable and asserted in tests).
    tokens_per_investigator: int = 4000
    calls_per_investigator: int = 4
    wall_s_per_investigator: float = 75.0

    # Model / sampling (identical for every arm).
    model: str = "default"
    temperature: float = 0.2

    def __post_init__(self) -> None:
        # The team split must exactly reconstruct the arm-level totals, so a
        # team arm and a single-agent arm spend the same envelope.
        if self.tokens_per_investigator * self.n_team != self.total_tokens:
            raise ValueError(
                f"tokens_per_investigator ({self.tokens_per_investigator}) x "
                f"n_team ({self.n_team}) != total_tokens ({self.total_tokens})"
            )
        if self.calls_per_investigator * self.n_team != self.total_calls:
            raise ValueError(
                f"calls_per_investigator ({self.calls_per_investigator}) x "
                f"n_team ({self.n_team}) != total_calls ({self.total_calls})"
            )
        if (
            self.open_sharing_phase_calls * 2 != self.calls_per_investigator
            or self.open_sharing_phase_tokens * 2 != self.tokens_per_investigator
        ):
            raise ValueError(
                "open_sharing two-phase split must equal the per-investigator budget"
            )

    def team_investigator_caps(self) -> dict:
        """Per-investigator caps for a team-arm member (escrowed / open_sharing)."""
        return {
            "max_turns": self.calls_per_investigator,
            "token_budget": self.tokens_per_investigator,
            "max_tokens_per_call": self.max_tokens_per_call,
            "wall_deadline_s": self.wall_s_per_investigator,
        }

    def single_agent_caps(self) -> dict:
        """Caps for a single-agent arm (central_adaptive / single_investigator)."""
        return {
            "max_turns": self.total_calls,
            "token_budget": self.total_tokens,
            "max_tokens_per_call": self.max_tokens_per_call,
            "wall_deadline_s": self.wall_s,
        }

    def open_sharing_phase_caps(self) -> dict:
        """Per-phase caps for an open_sharing investigator (each of 2 phases)."""
        return {
            "max_turns": self.open_sharing_phase_calls,
            "token_budget": self.open_sharing_phase_tokens,
            "max_tokens_per_call": self.max_tokens_per_call,
            "wall_deadline_s": self.wall_s_per_investigator / 2,
        }

    def as_dict(self) -> dict:
        return {
            "total_tokens": self.total_tokens,
            "total_calls": self.total_calls,
            "max_tokens_per_call": self.max_tokens_per_call,
            "wall_s": self.wall_s,
            "n_team": self.n_team,
            "tokens_per_investigator": self.tokens_per_investigator,
            "calls_per_investigator": self.calls_per_investigator,
            "wall_s_per_investigator": self.wall_s_per_investigator,
            "open_sharing_phase_calls": self.open_sharing_phase_calls,
            "open_sharing_phase_tokens": self.open_sharing_phase_tokens,
            "model": self.model,
            "temperature": self.temperature,
        }


    @classmethod
    def scaled_to_total_tokens(
        cls,
        total_tokens: int,
        *,
        n_team: int = 4,
        total_calls: int = 16,
        calls_per_investigator: int = 4,
    ) -> "MatchedCaps":
        """Build a matched envelope from an arm-level ``total_tokens``.

        Scales the per-investigator token split so the team arm still
        reconstructs the arm-level total (``tokens_per_investigator * n_team
        == total_tokens``). ``total_tokens`` must be divisible by ``n_team * 2``
        so the open_sharing two-phase split is integral. Call and wall-clock
        caps are unchanged (the token budget, not the call budget, is what
        starves partitioned investigators in practice).
        """
        if total_tokens % (n_team * 2) != 0:
            raise ValueError(
                f"total_tokens ({total_tokens}) must be divisible by "
                f"{n_team * 2} for an integral per-investigator / two-phase split"
            )
        tpi = total_tokens // n_team
        return cls(
            total_tokens=total_tokens,
            total_calls=total_calls,
            n_team=n_team,
            tokens_per_investigator=tpi,
            calls_per_investigator=calls_per_investigator,
            open_sharing_phase_tokens=tpi // 2,
            open_sharing_phase_calls=calls_per_investigator // 2,
        )


#: The default matched envelope used by the runner and the CLI.
DEFAULT_CAPS = MatchedCaps()

__all__ = ["MatchedCaps", "DEFAULT_CAPS"]
