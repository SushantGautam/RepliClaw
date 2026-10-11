#!/usr/bin/env python3
"""One-shot: freeze the sealed oracle for the drift-sign AND case.

Run ONCE to compute the expected batch mean concentration (the bias-removed
truth: mean of (raw_i - drift_i)/k over the frozen 32 samples) and write
``oracle.json``. The oracle is then the sealed ground truth that ONLY
``judge.py`` reads.

The frozen expected value is what a HEALTHY pipeline (correct sign AND
calibrated instrument) reports -- it is identical across the I1/I2/I3 arms
by construction of the case (see case.py docstring).
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent  # the case's oracle/ directory
CASE = HERE.parent
DATA = CASE / "data" / "batch_assay.json"
OUT = HERE / "oracle.json"

K = 96.0


def main() -> int:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    samples = data["samples"]
    concs = [(s["raw_counts"] - s["reference_drift_counts"]) / K for s in samples]
    expected = round(sum(concs) / len(concs), 6)
    buggy = round(sum((s["raw_counts"] + s["reference_drift_counts"]) / K for s in samples) / len(samples), 6)
    oracle = {
        "schema": "repliclaw.sealed_oracle/v1",
        "case": "drift_sign_and_v1",
        "interaction_type": "two_cause_and",
        "true_cause": "correction_sign_error AND uncalibrated_instrument",
        "cause_set": ["correction_sign_error", "uncalibrated_instrument"],
        "injected_defects": [
            {
                "id": "correction_sign_error",
                "description": "Correction routine ADDS the logged blank drift instead of subtracting it; invisible whenever the logged drift is 0.",
            },
            {
                "id": "uncalibrated_instrument",
                "description": "Instrument ran uncalibrated, so per-sample logged drift is nonzero.",
            },
        ],
        "expected_mean_concentration": expected,
        "tolerance_abs_umg_ml": 0.05,
        "per_arm_expected_outcome": {
            "I0_baseline": "fail",
            "I1_fix_sign": "pass",
            "I2_recalibrate": "pass",
            "I3_fix_both": "pass",
        },
        "hidden_fields": [
            "true_cause",
            "cause_set",
            "injected_defects",
            "expected_mean_concentration",
            "tolerance_abs_umg_ml",
            "abs_diff",
            "per_arm_expected_outcome",
            "oracle_schema",
        ],
        "note": (
            "Frozen 2026-10-12 from the frozen batch_assay.json (32 samples, "
            "k = 96.0 counts/(umg/mL)). Expected mean = mean_i (raw_i - drift_i)/k "
            f"= {expected} umg/mL; as-run buggy mean (sign flipped, drift present) "
            f"= {buggy} umg/mL (deviation {round(abs(buggy - expected), 6)} umg/mL). "
            "The judge (judge.py) is the ONLY reader; these fields are stripped "
            "from all persisted investigator-visible artifacts via the case's "
            "public_judgment_drop."
        ),
    }
    OUT.write_text(json.dumps(oracle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("wrote", OUT)
    print(f"expected (healthy) mean = {expected} umg/mL")
    print(f"buggy (as-run) mean     = {buggy} umg/mL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
