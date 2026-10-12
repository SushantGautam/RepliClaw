"""Public evidence loader for the adversarial scientific-audit dataset.

This module is the ONLY sanctioned interface for investigators (agents) to
access the investigable claims and the evidence artifacts. It reads exclusively
from ``data/public/`` and NEVER exposes:

  * per-claim answers or rationales (``data/private/ground_truth.json``), or
  * the trap taxonomy (``data/private/trap_annotations.json``).

Ground truth and trap annotations are evaluator-only and live in
:mod:`repliclaw.benchmarks.adversarial_audit.ground_truth`. Importing this
module in a fully privileged agent process is NOT an isolation boundary; the
trusted host should hand investigators only the return values of the functions
here (mirroring the CompoundCausal-32 ``BenchmarkSession`` convention).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parent / "data"
_PUBLIC_DIR = _DATA_DIR / "public"

#: Fields that are evaluator-only and must never appear in investigator-facing
#: artifact records. The public data files do not carry them, but this guard
#: makes the boundary explicit and future-proof.
_EVALUATOR_ONLY_FIELDS = frozenset({"answer", "rationale", "trap_tags", "required_artifacts"})


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _strip_evaluator_fields(record: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``record`` with any evaluator-only fields removed."""
    return {k: v for k, v in record.items() if k not in _EVALUATOR_ONLY_FIELDS}


def load_claims() -> list[dict[str, Any]]:
    """Return the investigable claims (public questions, NO answers)."""
    return _read_json(_PUBLIC_DIR / "claims.json")["claims"]


def load_evidence() -> list[dict[str, Any]]:
    """Return ALL evidence artifacts (public). Trap tags are never included."""
    artifacts = _read_json(_PUBLIC_DIR / "evidence.json")["artifacts"]
    return [_strip_evaluator_fields(a) for a in artifacts]


def list_sources() -> list[dict[str, Any]]:
    """Return the named evidence sources (id, name, description)."""
    return _read_json(_PUBLIC_DIR / "evidence.json")["sources"]


def source_ids() -> list[str]:
    """Return the ordered list of source ids."""
    return [s["source_id"] for s in list_sources()]


def evidence_for_source(source_id: str) -> list[dict[str, Any]]:
    """Return only the evidence artifacts belonging to one source (a partition).

    This is what a single investigator is given when evidence is fragmented by
    source. No single source's partition is sufficient to correctly resolve all
    claims; the full answer requires cross-referencing across sources.
    """
    if source_id not in source_ids():
        raise ValueError(f"unknown source {source_id!r}")
    return [a for a in load_evidence() if a["source"] == source_id]


def load_dataset() -> dict[str, Any]:
    """Evaluator-side convenience: full PUBLIC dataset (claims + sources + artifacts).

    Public content only — never includes ground truth or trap annotations.
    """
    ev = _read_json(_PUBLIC_DIR / "evidence.json")
    cl = _read_json(_PUBLIC_DIR / "claims.json")
    return {
        "claims": cl["claims"],
        "sources": ev["sources"],
        "artifacts": [_strip_evaluator_fields(a) for a in ev["artifacts"]],
    }


def load_manifest() -> dict[str, Any]:
    """Return the public dataset manifest (provenance + ground-truth POINTER).

    The manifest carries only a pointer to the ground-truth file, never its
    content (matching the ``repliclaw.benchmark_case_manifest/v1`` convention).
    """
    return _read_json(_PUBLIC_DIR / "manifest.json")
