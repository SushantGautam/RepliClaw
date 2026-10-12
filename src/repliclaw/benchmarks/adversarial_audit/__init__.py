"""Adversarial scientific-audit dataset (RX-441 formulation audit).

A self-contained, hand-authored dataset of investigable research claims plus
fragmented, trap-laden evidence artifacts. It tests whether an auditor can
reach the correct conclusions by careful, independent, cross-referencing
analysis under fragmentation, conflict, and deception — as opposed to naive
global aggregation or over-reliance on a single (misleading) source.

Public (investigator-facing) surface — import from this package:
  * :func:`load_claims`, :func:`load_evidence`, :func:`list_sources`,
    :func:`source_ids`, :func:`evidence_for_source`, :func:`load_dataset`,
    :func:`load_manifest`.

EVALUATOR-ONLY surface — NOT exported here. Evaluators import the module
directly (``from repliclaw.benchmarks.adversarial_audit import ground_truth``)
and must run it in the trusted scorer process, never in agent code:
  * ``ground_truth.load_ground_truth``, ``ground_truth.score_submission``,
    ``ground_truth.load_trap_annotations``, and friends.

This is a fictional domain; no real compounds, companies, or studies.
"""
from .data import (
    evidence_for_source,
    list_sources,
    load_claims,
    load_dataset,
    load_evidence,
    load_manifest,
    source_ids,
)

__all__ = [
    "evidence_for_source",
    "list_sources",
    "load_claims",
    "load_dataset",
    "load_evidence",
    "load_manifest",
    "source_ids",
]
