"""EVALUATOR-ONLY ground-truth access for the adversarial scientific-audit dataset.

This module is the ONLY sanctioned reader of ``data/private/``. It must run in
the trusted evaluator/scorer process and must NEVER be imported or called from
agent/investigator code. The public evidence loader (:mod:`.data`) does not
depend on this module, so an investigator holding only :mod:`.data` cannot
reach the answers.

Mirrors the CompoundCausal-32 convention: ``load_dataset`` there returns the
private gold as a second value that "NEVER [may be] exposed to agents", and the
RCAEval lane keeps ``heldout_ground_truth`` out of the public package surface.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parent / "data"
_PRIVATE_DIR = _DATA_DIR / "private"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_ground_truth() -> dict[str, Any]:
    """EVALUATOR-ONLY. Return per-claim answers, rationales, and required artifacts.

    Raises if the private file is missing, so a misconfigured evaluator fails
    loudly rather than silently scoring against nothing.
    """
    path = _PRIVATE_DIR / "ground_truth.json"
    if not path.exists():
        raise FileNotFoundError(f"evaluator-only ground truth not found: {path}")
    return _read_json(path)


def load_trap_annotations() -> dict[str, Any]:
    """EVALUATOR-ONLY. Return the per-artifact trap taxonomy."""
    path = _PRIVATE_DIR / "trap_annotations.json"
    if not path.exists():
        raise FileNotFoundError(f"evaluator-only trap annotations not found: {path}")
    return _read_json(path)


def answer_for(claim_id: str) -> dict[str, Any]:
    """EVALUATOR-ONLY. Return the ground-truth record for one claim."""
    for record in load_ground_truth()["answers"]:
        if record["claim_id"] == claim_id:
            return record
    raise KeyError(f"no ground truth for claim {claim_id!r}")


def answers() -> dict[str, str]:
    """EVALUATOR-ONLY. Return ``{claim_id: 'TRUE'/'FALSE'}``."""
    return {a["claim_id"]: a["answer"] for a in load_ground_truth()["answers"]}


def required_artifacts() -> dict[str, list[str]]:
    """EVALUATOR-ONLY. Return ``{claim_id: [artifact_id, ...]}``.

    The minimal decisive evidence a careful auditor needs to correctly resolve
    each claim. Used to verify the "no single source contains the full answer"
    property: no one source holds all required artifacts for all claims.
    """
    return {a["claim_id"]: list(a["required_artifacts"]) for a in load_ground_truth()["answers"]}


def score_submission(submission: dict[str, str]) -> dict[str, Any]:
    """EVALUATOR-ONLY. Score ``{claim_id: 'TRUE'/'FALSE'}`` against ground truth.

    Missing claims count as incorrect. Returns per-claim detail and accuracy.
    """
    expected = answers()
    per_claim: dict[str, Any] = {}
    correct = 0
    for claim_id, exp in expected.items():
        pred = submission.get(claim_id)
        ok = pred == exp
        correct += ok
        per_claim[claim_id] = {"expected": exp, "predicted": pred, "correct": ok}
    total = len(expected)
    return {
        "schema": "adversarial_audit/score/v1",
        "total": total,
        "correct": correct,
        "accuracy": (correct / total) if total else 0.0,
        "per_claim": per_claim,
        "note": "evaluator-only ground truth; no empirical arm superiority implied",
    }
