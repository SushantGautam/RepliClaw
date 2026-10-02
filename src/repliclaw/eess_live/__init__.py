"""Live-LLM EESS arms (P08): the S5 lifecycle driven through a real client
interface, with per-call budget accounting and the P08 artifact set.

Public surface:

- :class:`LiveEESSOrchestrator` / :class:`LiveRunResult` — one arm's live
  lifecycle (COMMIT -> REVEAL -> EXECUTE -> RESOLVE + post-evidence verdicts).
- :class:`EESSLiveS5Arm` / :class:`EESSNoEscrowArm` / :class:`EESSRandomSelectArm`
  — the three ``ComparatorArm`` adapters (escrow seam x policy seam).
- :class:`LiveBudgetLedger` — per-LLM-call ``p08.budget_ledger/1`` accounting.
- :class:`FakeLLMClient` — the ONLY fake model in the codebase; offline tests
  and the token-floor script use it (no network, no API key).

The escrow seam (:class:`EscrowedEscrow` vs :class:`PassThroughEscrow`) and
the policy seam (``LocalEigPolicy`` vs ``RandomPolicy``) are the ONLY
differences between the arms — everything else is shared code.

Heavy submodules are imported lazily by callers (the ``comparators`` package
must not pull the slice/simpleaudit stack transitively).
"""
from __future__ import annotations

from .accounting import LiveBudgetLedger, LiveCall
from .budget_calls import (
    InvalidUsageError,
    UsageSnapshot,
    usage_delta,
    usage_present,
    usage_snapshot,
)
from .escrow import (
    EscrowedEscrow,
    LiveEscrow,
    PassThroughEscrow,
    RevealOutcome,
)
from .fake import COMMIT_MARKER, VERDICT_MARKER, FakeLLMClient

__all__ = [
    "COMMIT_MARKER",
    "InvalidUsageError",
    "LiveBudgetLedger",
    "LiveCall",
    "LiveEscrow",
    "UsageSnapshot",
    "VERDICT_MARKER",
    "EscrowedEscrow",
    "PassThroughEscrow",
    "RevealOutcome",
    "FakeLLMClient",
    "usage_delta",
    "usage_present",
    "usage_snapshot",
]
