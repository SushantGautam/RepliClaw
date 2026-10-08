"""P07 — the EESS vertical slice: escrow -> reveal -> local choice -> real run.

Public surface (the judge's bar-2/3 machinery):

- :func:`derive_discriminability` — the ONLY place scientific discriminability
  is computed, and ONLY from published evidence (never the oracle, never a
  test arm). Feeds each agent's local policy so its choice is *derived*.
- :func:`run_slice` — the COMMIT -> REVEAL -> EXECUTE -> RESOLVE lifecycle
  driven by the decentralized need market; returns a :class:`SliceReport`.
- :class:`SliceResult` / :class:`SliceReport` — frozen, serializable records.
- :func:`verify_run` — independent re-execution (P02 replay semantics).
"""
from __future__ import annotations

from repliclaw.slice.derive import (
    ARM_BY_HYP,
    ARM_TESTED_HYP,
    BASELINE_ARM,
    COMPETING_ARM,
    derive_discriminability,
)
from repliclaw.slice.orchestrate import (
    CASE_ID,
    HYP_BY_AGENT,
    SliceReport,
    SliceResult,
    arm_of_need,
    build_agents,
    build_evidence,
    build_predictions,
    evaluate_predictions,
    evidence_view,
    make_executor,
    make_need,
    run_slice,
    stop_reason,
    verify_run,
)

__all__ = [
    "ARM_BY_HYP",
    "ARM_TESTED_HYP",
    "BASELINE_ARM",
    "CASE_ID",
    "COMPETING_ARM",
    "HYP_BY_AGENT",
    "SliceReport",
    "SliceResult",
    "arm_of_need",
    "build_agents",
    "build_evidence",
    "build_predictions",
    "derive_discriminability",
    "evaluate_predictions",
    "evidence_view",
    "make_executor",
    "make_need",
    "run_slice",
    "stop_reason",
    "verify_run",
]
