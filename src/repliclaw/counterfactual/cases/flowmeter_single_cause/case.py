"""SINGLE-CAUSE counterfactual case: flow meter totalization audit.

CASE ID
-------
``flowmeter_single_cause_v1`` -- genuinely distinct from the frozen
``policy_rag_v1`` (P08 hero) and ``tox21_ar_agonist_v1`` (P06) cases:
different domain, different frozen input, different measurement, different
causal structure (exactly ONE latent cause).

SYSTEM
------
An inline flow meter (FT-7731) logs a daily pulse count for 14 days
(frozen in ``data/meter_window.json``). The pipeline under audit converts
pulse counts to total volume with the meter's calibration factor and reports
the window total.

LATENT CAUSE (sealed; see ``oracle/oracle.json`` -- judge-only)
---------------------------------------------------------------
The meter shipped with a STALE FIRMWARE CALIBRATION: the as-shipped config
converts at 0.0472 L/count while the correct factor is 0.05 L/count.
That is the EXACTLY ONE latent cause: fixing it (and it alone) makes the
pipeline report the true window total.

ARMS (each perturbs exactly ONE factor; contract section 5)
-----------------------------------------------------------
* ``I0_baseline``        : as-shipped config (stale calibration, dropped
  events not accounted). The failure arm.
* ``I1_fix_calibration`` : restore the correct 0.05 L/count calibration.
  THE causal fix -- expected to pass.
* ``I2_account_dropped`` : enable accounting of the meter's logged
  dropped-event counter. A plausible-but-WRONG fix: the frozen window's
  dropped-event counter is 0 on every day, so this intervention is a
  genuine no-op on this data and the total stays wrong (a non-cause
  control that must still fail).

HIDDEN FIELDS (documented per the lane's oracle-leakage rule)
------------------------------------------------------------
The investigator-visible artifacts (per-arm ``config.json``,
``target_output.json``, ``stdout.log``, public ``judgment.json``, and the
manifest) contain the frozen data, the arm config, and the measured
outputs -- but NEVER: ``true_cause``, ``cause_set``, ``injected_defect``,
``expected_total_liters``, ``tolerance_abs_liters``, ``abs_diff``,
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
_DATA_FILE = _HERE / "data" / "meter_window.json"

_MEASUREMENT = "pulse_count_volume_total/v1"

# As-shipped (buggy) factor vs. the correct factor documented in the
# firmware 3.4.1 release note. I0 uses the shipped value; I1 restores the
# correct one. Each arm differs from I0 in EXACTLY one factor.
_CAL_SHIPPED = 0.0472
_CAL_CORRECT = 0.05

_ARMS: Dict[str, Dict[str, Any]] = {
    "I0_baseline": {
        "calibration_l_per_count": _CAL_SHIPPED,
        "account_for_dropped": False,
        "intervention": "none (as-shipped meter config)",
    },
    "I1_fix_calibration": {
        "calibration_l_per_count": _CAL_CORRECT,
        "account_for_dropped": False,
        "intervention": "restore firmware 3.4.1 pulse calibration",
    },
    "I2_account_dropped": {
        "calibration_l_per_count": _CAL_SHIPPED,
        "account_for_dropped": True,
        "intervention": "account for logged dropped pulse events (counter is 0 all window)",
    },
}


class FlowmeterSingleCauseCase(Case):
    """Frozen single-cause flow-meter totalization counterfactual case."""

    case_id = "flowmeter_single_cause_v1"
    case_version = "v1"
    target_measurement_id = _MEASUREMENT
    # Judgment fields that name the sealed ground truth; stripped from all
    # persisted (investigator-visible) artifacts.
    public_judgment_drop = frozenset(
        {
            "expected_total_liters",
            "tolerance_abs_liters",
            "abs_diff",
            "true_cause",
            "cause_set",
            "injected_defect",
            "per_arm_expected_outcome",
            "hidden_fields",
            "oracle_schema",
        }
    )

    def __init__(self) -> None:
        self._data = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
        self._days: List[Dict[str, Any]] = list(self._data["days"])
        self._meter_id: str = str(self._data["meter_id"])

    # -- identity ----------------------------------------------------------
    def case_sha256(self) -> str:
        """sha256 of the frozen meter_window.json bytes (the immutable input)."""
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
            "calibration_l_per_count": spec["calibration_l_per_count"],
            "account_for_dropped": spec["account_for_dropped"],
            "meter_id": self._meter_id,
            "n_days": len(self._days),
            "measurement": _MEASUREMENT,
            "case_sha256": self.case_sha256(),
        }

    # -- ARM (structurally independent of the sealed ground truth) ---------
    def measure_arm(self, arm_id: str, seed: int) -> Dict[str, Any]:
        """Total the frozen window under this arm's single-factor config.

        Pure function of the frozen data + the arm's one-factor override.
        ``seed`` is recorded for parity with live targets; deterministic here.
        """
        del seed
        spec = _ARMS[arm_id]
        cal = float(spec["calibration_l_per_count"])
        account = bool(spec["account_for_dropped"])
        per_day: List[Dict[str, Any]] = []
        total_counts = 0
        total_dropped = 0
        for d in self._days:
            counts = int(d["pulse_counts"])
            dropped = int(d["dropped_events"]) if account else 0
            total_counts += counts
            total_dropped += dropped
            per_day.append(
                {
                    "day": d["day"],
                    "pulse_counts": counts,
                    "counted_dropped": dropped,
                    "volume_liters": round(cal * (counts + dropped), 6),
                }
            )
        total_volume = sum(p["volume_liters"] for p in per_day)
        return {
            "arm_id": arm_id,
            "measurement": _MEASUREMENT,
            "meter_id": self._meter_id,
            "n_days": len(self._days),
            "total_pulse_counts": total_counts,
            "total_counted_dropped_events": total_dropped,
            "total_volume_liters": round(total_volume, 6),
            "per_day": per_day,
        }

    # -- JUDGE (delegated; the ONLY reader of the sealed ground truth) -----
    def judge_arm(self, arm_id: str, target_output: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        from repliclaw.counterfactual.cases.flowmeter_single_cause.judge import judge_arm

        return judge_arm(self, arm_id, target_output)

    def engine_metadata(self) -> Dict[str, str]:
        return engine_metadata("python", sys.version.split()[0], "")


def load_case() -> FlowmeterSingleCauseCase:
    """Load the frozen flow-meter single-cause case."""
    return FlowmeterSingleCauseCase()
