"""Judge for the Tox21 AR-agonist case -- the ONLY module that reads the
sealed ground truth (``oracle/oracle.json`` in the case directory).

Keeping the ground-truth read in its own module (rather than in
:meth:`case.Tox21ArAgonistCase.judge_arm`) makes the arm path
(structurally) oracle-free: the arm source file contains no reference to the
ground-truth file, and a test asserts this module is the sole reader.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Tuple

_HERE = Path(__file__).resolve().parent
_GROUND_TRUTH = _HERE / "oracle" / "oracle.json"


def judge_arm(case: Any, arm_id: str, target_output: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """Score a measured arm against the sealed ground-truth expected shift.

    Parameters
    ----------
    case:
        The case instance (used only for ``case_sha256()``).
    arm_id:
        The arm identifier (key in the ground truth's
        ``expected_arm_outcomes``).
    target_output:
        The arm's measured output (must contain ``mean_delta_logp``).

    Returns
    -------
    (judgment, severity) where severity is ``"pass"`` when the measured mean
    shift is within the ground-truth tolerance of the expected shift, else
    ``"mismatch"``.
    """
    ground_truth = json.loads(_GROUND_TRUTH.read_text(encoding="utf-8"))
    expected = float(ground_truth["expected_arm_outcomes"][arm_id]["mean_delta_logp"])
    measured = float(target_output["mean_delta_logp"])
    tol = float(ground_truth["tolerance_abs_delta_logp"])
    abs_diff = abs(measured - expected)
    within = abs_diff <= tol
    severity = "pass" if within else "mismatch"
    judgment = {
        "case_sha256": case.case_sha256(),
        "arm_id": arm_id,
        "measurement": target_output.get("measurement"),
        "n_molecules": int(target_output["n_molecules"]),
        "measured_mean_delta_logp": measured,
        "expected_mean_delta_logp": expected,
        "abs_diff": round(abs_diff, 9),
        "tolerance_abs_delta_logp": tol,
        "within_tolerance": within,
        "severity": severity,
        "oracle_schema": ground_truth.get("schema"),
    }
    return judgment, severity
