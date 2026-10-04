"""Shared, registered defect-adjudication instruction block (PREREG v1.2 A9.2.1).

This module is the SINGLE canonical, role-agnostic defect-diagnosis contract
for the P08 controlled case. The ``DEFECT_ADJUDICATION_INSTRUCTION`` text is
byte-identical wherever it is embedded:

  * the strategy-arm finding prompt (``LLMInvestigator.run``, investigators.py)
    — arms S0/S3/S4;
  * the S5 ``RESOLVE`` post-evidence prompt (eess_live/orchestrator.py) — the
    escrow arm.

Both hosts wrap it in their own clearly marked
``# DEFECT DIAGNOSIS (required)`` section header (A9.2.1 / C6: an independent,
role-agnostic clause appended AFTER the numeric role-method section, so the
numeric framing (Cohen's d / t-test / RR on fields this RAG case lacks) cannot
dilute or suppress the defect answer).

Registration (A9.2.1 / C1):
  * field contract — ``defect_class`` enum
    ``retrieval_omission | policy_conflict | judge_stale | generation_error |
    data_error | none``; ``target_artifact`` = the name of the system component
    to fix, or null when ``defect_class`` is ``none``;
  * grounding — diagnose from the PROVIDED evidence/analysis only, and answer
    the defect question even when the primary numeric method found
    insufficient data (pick exactly one ``defect_class``).

The taxonomy is a MENU given equally to every arm — a pre-registered
vocabulary, not the answer (A9.4.3 disclosure). The oracle remains readable
only by the scorer.

This module is a LEAF (no project imports) so both ``investigators`` and
``eess_live.orchestrator`` can import it without cycles. The A4 oracle-leak
guard list and helper stay defined in eess_live/orchestrator.py
(``EVIDENCE_FORBIDDEN_SUBSTRINGS``) and are applied to BOTH prompt hosts
(A9.2.1: the strategy finding prompt gains the guard as a NEW guard — the
menu values are not in that field-name list, so the taxonomy cannot trip it).

Provenance (A9.2.6 / N-1): ``defect_instruction_sha256()`` is recorded in each
arm's ``run_metadata.json`` as ``a9_defect_instruction_sha256`` and asserted
stable / byte-identical across hosts by the A9.3d / C9 tests.
"""
from __future__ import annotations

import hashlib

# ---------------------------------------------------------------------------
# The canonical, registered instruction text (A9.2.1 / C1).
#
# DO NOT edit this string in place: it is a registered, sha-pinned contract.
# Any change requires a new registered version + a re-pinned sha256 (a prereg
# amendment), NOT a silent edit. The S5 RESOLVE prompt and the strategy
# finding prompt MUST embed this exact text (byte-identity asserted by the
# A9.3d / C9 tests).
# ---------------------------------------------------------------------------
DEFECT_ADJUDICATION_INSTRUCTION = (
    "In ADDITION to your numeric verdict, answer this required defect-diagnosis "
    "question. It is independent of your primary analysis and applies to every "
    "role, whether or not the bundled data was sufficient for the primary "
    "numeric method above (this case's data has no mean_*/events_* fields, so "
    "that method legitimately returns insufficient data — the defect question "
    "is still answerable from the provided evidence and must still be answered). "
    "Diagnose the observed failure of the system under test, grounded ONLY in "
    "the evidence provided to you — do not assume any ground truth, seeded "
    "fault, or oracle that is not shown. Emit exactly these two extra JSON "
    "fields:\n"
    '  "defect_class": exactly ONE of retrieval_omission | policy_conflict | '
    "judge_stale | generation_error | data_error | none (use none only if the "
    "system output is correct / no defect is observed);\n"
    '  "target_artifact": the name of the system component to fix (e.g. '
    "'retrieval'), or null when defect_class is 'none'.\n"
    "Pick exactly one defect_class from the list even when the primary numeric "
    "analysis found insufficient data, and keep the diagnosis grounded strictly "
    "in the provided evidence — never in hidden ground truth or the sealed "
    "oracle."
)


# The registered defect taxonomy (A9.2.1 / C1). Public adjudication vocabulary
# — a MENU given equally to every arm, not the answer. Kept as an explicit set
# so tests (and the scorer's canary) can reference the exact menu without
# re-parsing the instruction text.
DEFECT_TAXONOMY = frozenset(
    {
        "retrieval_omission",
        "policy_conflict",
        "judge_stale",
        "generation_error",
        "data_error",
        "none",
    }
)


def defect_instruction_sha256() -> str:
    """SHA-256 (hex) of the exact ``DEFECT_ADJUDICATION_INSTRUCTION`` text.

    Recorded in run metadata as ``a9_defect_instruction_sha256`` (A9.2.6 / N-1
    fold-in) so a run tree pins the exact adjudication contract it executed
    under, and asserted byte-stable by the A9.3d / C9 tests.
    """
    return hashlib.sha256(DEFECT_ADJUDICATION_INSTRUCTION.encode("utf-8")).hexdigest()


__all__ = [
    "DEFECT_ADJUDICATION_INSTRUCTION",
    "DEFECT_TAXONOMY",
    "defect_instruction_sha256",
]
