"""AgentRx failure taxonomy, pinned to upstream repo 7a18c79708e7671be15124460f4f7296107c2a55.

Canonical categories are the 10 metric-level names in
``agentrx/reports/analyze_metrics.py`` (``FAILURE_CASE_TO_CATEGORY``, lines 20-27),
cross-checked against the ``FailureCase`` enum in ``agentrx/judge/judge.py`` (L253-264).

``normalize_category`` is a verbatim copy of the upstream mapping logic from
``agentrx/reports/analyze_metrics.py:47-76`` — substring matching, identical
branch order, identical fallback. No mappings were invented here.
"""
from __future__ import annotations

import enum


class FailureCase(enum.IntEnum):
    """Canonical AgentRx failure categories, pinned to agentrx@7a18c797.

    Source: ``agentrx/judge/judge.py`` L253-264 (``FailureCase`` enum) and
    ``agentrx/reports/analyze_metrics.py`` L20-27 (``FAILURE_CASE_TO_CATEGORY``).
    Code 0 is judge-only: a wrong-prediction sentinel, never a ground-truth
    category (upstream treats a NO_ERROR_PREDICTED prediction as incorrect).
    """

    NO_ERROR_PREDICTED = 0
    INSTRUCTION_ADHERENCE_FAILURE = 1
    INVENTION_OF_NEW_INFORMATION = 2
    INVALID_INVOCATION = 3
    MISINTERPRETATION_OF_TOOL_OUTPUT = 4
    INTENT_PLAN_MISALIGNMENT = 5
    UNDERSPECIFIED_USER_INTENT = 6
    INTENT_NOT_SUPPORTED = 7
    GUARDRAILS_TRIGGERED = 8
    SYSTEM_FAILURE = 9
    INCONCLUSIVE = 10

    @property
    def label(self) -> str:
        return CATEGORY_LABELS[self.value]


#: Canonical metric-level labels. Verbatim from analyze_metrics.py L20-27
#: (pinned repo 7a18c797); code 0 label is the judge sentinel name.
CATEGORY_LABELS: dict[int, str] = {
    0: "NO_ERROR_PREDICTED",
    1: "Instruction Adherence Failure",
    2: "Invention of New Information",
    3: "Invalid Invocation",
    4: "Misinterpretation of Tool Output",
    5: "Intent Plan Misalignment",
    6: "Underspecified User Intent",
    7: "Intent Not Supported",
    8: "Guardrails Triggered",
    9: "System Failure",
    10: "Inconclusive",
}

#: Canonical label -> category code (GT categories only, excludes sentinel 0).
CATEGORY_TO_FAILURE_CASE: dict[str, int] = {label: code for code, label in CATEGORY_LABELS.items() if code != 0}


def normalize_category(category: str) -> str:
    """Normalize category string for matching.

    Verbatim copy of the upstream mapping logic, source:
    ``agentrx/reports/analyze_metrics.py:47-76`` (pinned repo 7a18c797).
    Do not add branches without re-deriving from the upstream file.
    """
    if not category:
        return "Unknown"

    cat_lower = category.strip().lower()

    # Map variations to standard names
    if "instruction" in cat_lower and "adherence" in cat_lower:
        return "Instruction Adherence Failure"
    elif "invention" in cat_lower or ("new" in cat_lower and "information" in cat_lower):
        return "Invention of New Information"
    elif "invalid" in cat_lower and "invocation" in cat_lower:
        return "Invalid Invocation"
    elif "misinterpretation" in cat_lower or "handoff" in cat_lower:
        return "Misinterpretation of Tool Output"
    elif "intent" in cat_lower and ("plan" in cat_lower or "misalignment" in cat_lower):
        return "Intent Plan Misalignment"
    elif "underspecified" in cat_lower or ("user" in cat_lower and "intent" in cat_lower and "not" not in cat_lower):
        return "Underspecified User Intent"
    elif "not supported" in cat_lower or ("intent" in cat_lower and "not" in cat_lower and "supported" in cat_lower):
        return "Intent Not Supported"
    elif "guardrail" in cat_lower:
        return "Guardrails Triggered"
    elif "system" in cat_lower and "failure" in cat_lower:
        return "System Failure"
    elif "inconclusive" in cat_lower:
        return "Inconclusive"
    else:
        return category.strip()


def category_code(category: str) -> int | None:
    """Canonical code (1-10) for a raw category string, or None if unrecognised."""
    return CATEGORY_TO_FAILURE_CASE.get(normalize_category(category))


__all__ = ["CATEGORY_LABELS", "CATEGORY_TO_FAILURE_CASE", "FailureCase", "category_code", "normalize_category"]
