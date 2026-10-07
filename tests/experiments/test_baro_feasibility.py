"""Gate the G3 pilot BARO feasibility artifact (frozen spec §3 "BARO").

Skipped unless scripts/baro_pilot_feasibility.py has produced
.artifacts/rcaeval/pilot/baro_feasibility.json (BARO is a one-off feasibility
pass, not part of the default test run).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ARTIFACT = (
    Path(__file__).resolve().parents[2]
    / ".artifacts" / "rcaeval" / "pilot" / "baro_feasibility.json"
)

pytestmark = pytest.mark.skipif(
    not ARTIFACT.exists(),
    reason="baro_feasibility.json not present; run scripts/baro_pilot_feasibility.py first",
)


def _load() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_in_range_flag_true() -> None:
    data = _load()
    assert data["in_range_0.4_0.85"] is True


def test_four_per_case_entries_with_top5() -> None:
    data = _load()
    per_case = data["per_case"]
    assert len(per_case) == 4
    for case, entry in per_case.items():
        assert len(entry["top5"]) == 5, case
        assert isinstance(entry["hit"], bool), case


def test_metric_within_range() -> None:
    data = _load()
    metric = data["avg_at_5_cpu"]
    assert metric is not None
    assert 0.4 <= metric <= 0.85
