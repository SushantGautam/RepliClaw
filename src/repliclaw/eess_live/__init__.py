"""Live-LLM EESS arms (P08): the S5 canonical lifecycle driven through a real
LLM client interface, with per-call budget accounting and the P08 artifact set.

Public surface:

- :class:`LiveEESSOrchestrator` / :class:`LiveRunResult` — one arm's live
  lifecycle (COMMIT -> REVEAL -> EXECUTE -> RESOLVE + post-evidence verdicts).
- :class:`EESSLiveS5Arm` / :class:`EESSLiveA1Arm` / :class:`EESSLiveA3Arm`
  and :func:`live_arm_registry` — the three ``ComparatorArm`` adapters
  (escrow seam x policy seam) keyed by the preregistered registry keys
  (v1.1 §3.1: ``eess`` / ``eess_no_escrow`` / ``eess_random_select``).
- :class:`LiveBudgetLedger` / :class:`LiveCall` — per-LLM-call
  ``p08.budget_ledger/1`` accounting.
- :class:`FakeLLMClient` — the ONLY fake model in the codebase; offline
  tests and the token-floor script use it (no network, no API key).

The escrow seam (:class:`EscrowedEscrow` vs :class:`PassThroughEscrow`) and
the policy seam (``LocalEigPolicy`` vs ``RandomPolicy``) are the ONLY
differences between the arms — everything else is shared code.

Heavy submodules are imported lazily by callers (the ``comparators`` package
must not pull the slice/simpleaudit stack transitively).
"""
from __future__ import annotations

from .accounting import LiveBudgetLedger, LiveCall
from .arm import (
    EESSLiveA1Arm,
    EESSLiveA3Arm,
    EESSLiveArm,
    EESSLiveS5Arm,
    live_arm_registry,
)
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
from .orchestrator import AGENT_IDS, CASE_ID, LiveEESSOrchestrator, LiveRunResult

__all__ = [
    "AGENT_IDS",
    "CASE_ID",
    "COMMIT_MARKER",
    "EESSLiveA1Arm",
    "EESSLiveA3Arm",
    "EESSLiveArm",
    "EESSLiveS5Arm",
    "EscrowedEscrow",
    "FakeLLMClient",
    "InvalidUsageError",
    "LiveBudgetLedger",
    "LiveCall",
    "LiveEESSOrchestrator",
    "LiveEscrow",
    "LiveRunResult",
    "PassThroughEscrow",
    "RevealOutcome",
    "UsageSnapshot",
    "VERDICT_MARKER",
    "live_arm_registry",
    "usage_delta",
    "usage_present",
    "usage_snapshot",
]
