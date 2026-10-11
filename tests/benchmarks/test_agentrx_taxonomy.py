"""Tests for the AgentRx taxonomy: 10 canonical categories + normalize_category."""
from __future__ import annotations

from repliclaw.benchmarks.agentrx.taxonomy import (
    CATEGORY_LABELS,
    CATEGORY_TO_FAILURE_CASE,
    FailureCase,
    category_code,
    normalize_category,
)

#: All 11 distinct failure_category strings observed in the pinned dataset
#: (29 tau_retail + 44 magentic_one annotated files, 334 failure instances).
OBSERVED_ANNOTATION_STRINGS = [
    "Instruction Adherence Failure",  # tau (6)
    "Misinterpretation of Tool Output",  # tau (8) / magentic (23)
    "Invalid Invocation",  # tau (4) / magentic (1)
    "Underspecified User Intent",  # tau (10)
    "Intent Plan Misalignment",  # tau (8) / magentic (19)
    "Intent Not Supported",  # tau (2)
    "System Failure",  # tau (1) / magentic (1)
    "Instruction/Plan Adherence Failure",  # magentic (197)
    "Invention of new information",  # magentic (8, lowercase 'n')
    "Intent not supported",  # magentic (22, lowercase)
    "Guardrails Triggered",  # magentic (24)
]


def test_ten_canonical_categories_plus_sentinel():
    assert len(list(FailureCase)) == 11  # 10 GT categories + NO_ERROR_PREDICTED sentinel
    assert FailureCase.NO_ERROR_PREDICTED == 0
    assert len(CATEGORY_TO_FAILURE_CASE) == 10
    assert set(CATEGORY_TO_FAILURE_CASE.values()) == set(range(1, 11))


def test_canonical_labels_pinned():
    assert CATEGORY_LABELS[1] == "Instruction Adherence Failure"
    assert CATEGORY_LABELS[2] == "Invention of New Information"
    assert CATEGORY_LABELS[3] == "Invalid Invocation"
    assert CATEGORY_LABELS[4] == "Misinterpretation of Tool Output"
    assert CATEGORY_LABELS[5] == "Intent Plan Misalignment"
    assert CATEGORY_LABELS[6] == "Underspecified User Intent"
    assert CATEGORY_LABELS[7] == "Intent Not Supported"
    assert CATEGORY_LABELS[8] == "Guardrails Triggered"
    assert CATEGORY_LABELS[9] == "System Failure"
    assert CATEGORY_LABELS[10] == "Inconclusive"


def test_all_11_observed_strings_normalize():
    assert len(OBSERVED_ANNOTATION_STRINGS) == 11
    for s in OBSERVED_ANNOTATION_STRINGS:
        normalized = normalize_category(s)
        assert normalized in CATEGORY_TO_FAILURE_CASE, s
        assert category_code(s) is not None


def test_normalization_targets():
    assert normalize_category("Instruction/Plan Adherence Failure") == "Instruction Adherence Failure"
    assert normalize_category("Invention of new information") == "Invention of New Information"
    assert normalize_category("Intent not supported") == "Intent Not Supported"
    assert normalize_category("Instruction Adherence Failure") == "Instruction Adherence Failure"
    assert category_code("Instruction/Plan Adherence Failure") == 1
    assert category_code("Guardrails Triggered") == 8
    assert category_code("Inconclusive") == 10


def test_empty_and_unknown_strings():
    # upstream semantics: falsy (empty) -> "Unknown"; whitespace-only is
    # non-falsy, so it falls through the branches and returns the stripped string
    assert normalize_category("") == "Unknown"
    assert normalize_category("   ") == ""
    assert category_code("") is None
    assert normalize_category("totally unknown label") == "totally unknown label"
    assert category_code("totally unknown label") is None
