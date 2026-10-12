"""COMPOUND (AND-interaction) counterfactual case: batch-assay drift audit.

CASE ID
-------
``drift_sign_and_v1`` -- genuinely distinct from ``policy_rag_v1`` (P08 hero),
``tox21_ar_agonist_v1`` (P06), and ``flowmeter_single_cause_v1``: different
domain, different frozen input, different measurement, and a TWO-cause
AND-interaction causal structure.

SYSTEM
------
A QC batch (B-2026-094, 32 samples; frozen in ``data/batch_assay.json``) is
read by an AX-550 instrument. The readout model is
``raw = k * c_true + b`` where ``b`` is the instrument bias, logged per
sample as ``reference_drift_counts`` (measured on an interleaved blank).
The pipeline under audit reports the batch mean concentration:
``c_i = (raw_i + sign * b_i) / k`` with ``k = 96.0`` counts/(umg/mL).

TWO LATENT CAUSES (sealed; see ``oracle/oracle.json`` -- judge-only)
--------------------------------------------------------------------
* Cause A, ``correction_sign_error``: the correction routine ADDS the blank
  drift (``sign = +1``) instead of subtracting it. When the logged drift is
  0, this bug is completely invisible in every output.
* Cause B, ``uncalibrated_instrument``: the instrument ran in its
  uncalibrated state, so the logged per-sample drift is NONZERO.

AND-INTERACTION (the falsifiable structure)
-------------------------------------------
The failure (wrong batch mean) manifests ONLY when BOTH causes are present
at once: nonzero drift AND the flipped correction sign (error = +2*b/k on
every sample). Each cause ALONE is latent and must be verified by actual
rerun to NOT reproduce the failure:
* only A (drift = 0): ``raw + 0 = raw`` -- indistinguishable from correct.
* only B (sign correct): ``raw - b`` -- exactly the correct bias removal.

ARMS (each arm fixes exactly ONE cause, except the both-fix sanity arm;
contract section 5 single-factor discipline)
--------------------------------------------
* ``I0_baseline``    : both causes present (as-run system) -- the failure.
* ``I1_fix_sign``    : fix A only (correct sign; instrument stays
  uncalibrated, drift nonzero) -- expected to PASS.
* ``I2_recalibrate`` : fix B only (recalibration removes the bias from the
  readout, logged drift becomes 0; sign bug remains but is latent) --
  expected to PASS.
* ``I3_fix_both``    : fix A and B (sanity control) -- expected to PASS.

HIDDEN FIELDS (documented per the lane's oracle-leakage rule)
------------------------------------------------------------
Visible artifacts (frozen data, per-arm ``config.json``,
``target_output.json``, ``stdout.log``, public ``judgment.json``, manifest)
NEVER contain: ``true_cause``, ``cause_set``, ``injected_defects``,
``expected_mean_concentration``, ``tolerance_abs_umg_ml``, ``abs_diff``,
``per_arm_expected_outcome``, or ``oracle_schema``. Those live only in
``oracle/oracle.json`` and are stripped by the case's
``public_judgment_drop`` before persistence (see ``_base.persist_arm``).

OFFLINE + DETERMINISTIC: pure arithmetic on frozen JSON; no LLM, no network,
0 real tokens. Same (case_sha256, config_sha256, seed) -> byte-identical
artifacts (see ``_base.replay``).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from repliclaw.counterfactual.cases._base import Case, engine_metadata, sha256_bytes

_HERE = Path(__file__).resolve().parent
_DATA_FILE = _HERE / "data" / "batch_assay.json"

_MEASUREMENT = "batch_concentration_mean/v1"
# Instrument gain: 96.0 counts per umg/mL (factory gain, constant across arms).
_K_COUNTS_PER_UMG_ML = 96.0

# Each arm differs from I0 in exactly ONE factor (I3 is the documented
# both-fix sanity arm).
_ARMS: Dict[str, Dict[str, Any]] = {
    "I0_baseline": {
        "correction_sign": "plus",
        "instrument_state": "uncalibrated",
        "intervention": "none (as-run system: sign bug + uncalibrated instrument)",
    },
    "I1_fix_sign": {
        "correction_sign": "minus",
        "instrument_state": "uncalibrated",
        "intervention": "fix correction routine to subtract blank drift (instrument uncalibrated)",
    },
    "I2_recalibrate": {
        "correction_sign": "plus",
        "instrument_state": "calibrated",
        "intervention": "recalibrate instrument: bias removed from readout, logged drift = 0",
    },
    "I3_fix_both": {
        "correction_sign": "minus",
        "instrument_state": "calibrated",
        "intervention": "fix correction sign AND recalibrate instrument (both-fix sanity arm)",
    },
}


class DriftSignAndCase(Case):
    """Frozen two-cause AND-interaction counterfactual case."""

    case_id = "drift_sign_and_v1"
    case_version = "v1"
    target_measurement_id = _MEASUREMENT
    # Judgment fields that name the sealed ground truth; stripped from all
    # persisted (investigator-visible) artifacts.
    public_judgment_drop = frozenset(
        {
            "expected_mean_concentration",
            "tolerance_abs_umg_ml",
            "abs_diff",
            "true_cause",
            "cause_set",
            "injected_defects",
            "per_arm_expected_outcome",
            "hidden_fields",
            "oracle_schema",
        }
    )

    def __init__(self) -> None:
        self._data = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
        self._samples: List[Dict[str, Any]] = list(self._data["samples"])
        self._batch_id: str = str(self._data["batch_id"])

    # -- identity ----------------------------------------------------------
    def case_sha256(self) -> str:
        """sha256 of the frozen batch_assay.json bytes (the immutable input)."""
        return sha256_bytes(_DATA_FILE.read_bytes())

    def arm_ids(self) -> List[str]:
        return list(_ARMS.keys())

    def effective_config(self, arm_id: str) -> Dict[str, Any]:
        if arm_id not in _ARMS:
            raise KeyError(arm_id)
        spec = _ARMS[arm_id]
        return {
            "arm_id": arm_id,
            "intervention": spec["intervention"],
            "correction_sign": spec["correction_sign"],
            "instrument_state": spec["instrument_state"],
            "k_counts_per_umg_ml": _K_COUNTS_PER_UMG_ML,
            "batch_id": self._batch_id,
            "n_samples": len(self._samples),
            "measurement": _MEASUREMENT,
            "case_sha256": self.case_sha256(),
        }

    # -- ARM (structurally independent of the sealed ground truth) ---------
    def measure_arm(self, arm_id: str, seed: int) -> Dict[str, Any]:
        """Run the batch pipeline under this arm's config.

        * ``instrument_state = "calibrated"``: recalibration physically
          removes the bias -- the effective raw readout is ``raw - drift``
          and the effective logged bias ``b`` is 0.
        * ``correction_sign``: ``"plus"`` (as-run bug) computes
          ``raw_eff + b``; ``"minus"`` (correct) computes ``raw_eff - b``.

        Pure function of the frozen data + the arm's factor overrides.
        """
        del seed  # recorded for parity with live targets; deterministic here
        spec = _ARMS[arm_id]
        sign = +1 if spec["correction_sign"] == "plus" else -1
        calibrated = spec["instrument_state"] == "calibrated"
        per_sample: List[Dict[str, Any]] = []
        total_bias = 0.0
        conc_sum = 0.0
        for s in self._samples:
            raw = float(s["raw_counts"])
            drift = float(s["reference_drift_counts"])
            raw_eff = raw - drift if calibrated else raw  # recalibration removes bias
            b = 0.0 if calibrated else drift
            total_bias += b
            corrected = raw_eff + sign * b
            conc = corrected / _K_COUNTS_PER_UMG_ML
            conc_sum += conc
            per_sample.append(
                {
                    "sample_id": s["sample_id"],
                    "raw_counts": raw,
                    "logged_bias_counts": b,
                    "corrected_counts": corrected,
                    "concentration_umg_ml": round(conc, 6),
                }
            )
        n = len(self._samples)
        return {
            "arm_id": arm_id,
            "measurement": _MEASUREMENT,
            "batch_id": self._batch_id,
            "n_samples": n,
            "total_logged_bias_counts": round(total_bias, 6),
            "mean_concentration_umg_ml": round(conc_sum / n, 6),
            "per_sample": per_sample,
        }

    # -- JUDGE (delegated; the ONLY reader of the sealed ground truth) -----
    def judge_arm(self, arm_id: str, target_output: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        from repliclaw.counterfactual.cases.drift_sign_and.judge import judge_arm

        return judge_arm(self, arm_id, target_output)

    def engine_metadata(self) -> Dict[str, str]:
        return engine_metadata("python", sys.version.split()[0], "")


def load_case() -> DriftSignAndCase:
    """Load the frozen drift-sign AND-interaction case."""
    return DriftSignAndCase()
