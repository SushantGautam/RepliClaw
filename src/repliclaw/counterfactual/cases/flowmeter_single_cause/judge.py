"""Judge for the flow-meter single-cause case -- the ONLY module that reads
the sealed ground truth (``oracle/oracle.json`` in the case directory).

The arm path (``data/``, ``case.py``) is structurally oracle-free; this
module is its sole reader (contract section 6).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Tuple

_HERE = Path(__file__).resolve().parent
_GROUND_TRUTH = _HERE / "oracle" / "oracle.json"


def judge_arm(case: Any, arm_id: str, target_output: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """Score the measured window total against the sealed ground truth.

    Returns ``(judgment, severity)`` where severity is ``"pass"`` when the
    measured total is within the ground-truth tolerance of the expected
    total, else ``"mismatch"``. Fields that name the sealed ground truth
    (expected total, tolerance, abs diff, cause set, per-arm expected
    outcomes) are present in the in-memory judgment for internal validation
    but are stripped from persisted artifacts by the case's
    ``public_judgment_drop``.
    """
    gt = json.loads(_GROUND_TRUTH.read_text(encoding="utf-8"))
    expected = float(gt["expected_total_liters"])
    measured = float(target_output["total_volume_liters"])
    tol = float(gt["tolerance_abs_liters"])
    abs_diff = abs(measured - expected)
    within = abs_diff <= tol
    severity = "pass" if within else "mismatch"
    judgment = {
        "case_sha256": case.case_sha256(),
        "arm_id": arm_id,
        "measurement": target_output.get("measurement"),
        "n_days": int(target_output["n_days"]),
        "measured_total_volume_liters": measured,
        # -- sealed ground-truth fields below (stripped from persistence) --
        "expected_total_liters": expected,
        "tolerance_abs_liters": tol,
        "abs_diff": round(abs_diff, 9),
        "true_cause": gt.get("true_cause"),
        "cause_set": gt.get("cause_set"),
        "injected_defect": gt.get("injected_defect"),
        "per_arm_expected_outcome": gt.get("per_arm_expected_outcome"),
        "oracle_schema": gt.get("schema"),
    }
    return judgment, severity
