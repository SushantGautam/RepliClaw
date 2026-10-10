"""Tests for the V3 telemetry sandbox (addendum §3: OBS tools, leak guards,
diagnosis commit, budgets). See ``src/repliclaw/experiments/v3/telemetry.py``.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from repliclaw.experiments.v3 import telemetry as tel
from repliclaw.experiments.v3.telemetry import FROZEN_PILOT_IDS as FROZEN
from repliclaw.experiments.v3.telemetry import (
    DiagnosisAlreadyCommitted,
    LeakDetectedError,
    PilotCaseRegistry,
    TelemetrySandbox,
    ToolBudgetExhausted,
    UnknownServiceError,
    service_level_success,
)

REPO = Path(__file__).resolve().parents[2]
PILOT = REPO / ".artifacts" / "rcaeval" / "pilot"
FAKE_UPSTREAM_ID = sorted(FROZEN)[0]  # upstream id the fake case dir stands in for
SENTINEL = "SENTINEL-ROOT-CAUSE-CONTENT-DO-NOT-LEAK"


def _real_registry() -> PilotCaseRegistry:
    return PilotCaseRegistry()


def _build_fake_case(root: Path, *, with_logs: bool = True, with_traces: bool = True) -> Path:
    """Build a synthetic metrics-only-or-more pilot-shaped case dir.

    13 fake services, one metric per service; ``svc04_s1`` spikes after onset
    (faulty window only) so it is the unique top anomaly. Also includes a
    constant column that must be dropped by the anomaly math.
    """
    case = root / sorted(FROZEN)[0]  # registry maps RCA-P-01 -> this dir
    case.mkdir(parents=True, exist_ok=True)
    onset = 1_000_000
    n = 800  # covers normal [onset-600, onset) and faulty [onset, onset+600)
    t = np.arange(onset - 600, onset + 200)
    rng = np.random.default_rng(7)
    data: dict[str, np.ndarray] = {"time": t}
    for i in range(13):
        base = 10.0 + rng.normal(0.0, 0.5, size=n)
        col = f"svc{i:02d}_s1"
        if i == 4:
            base = base.copy()
            # t[600] == onset, so [600:] is exactly the faulty window (t >= onset)
            base[600:] += 50.0
        data[col] = base
    data["svc00_const"] = np.full(n, 3.14)
    df = pd.DataFrame(data)
    df.to_parquet(case / "metrics.parquet")
    (case / "inject_time.txt").write_text(f"{onset}\n")
    if with_logs:
        log_ts = np.array([onset - 100, onset, onset + 99])
        pd.DataFrame(
            {
                "timestamp": log_ts,
                "container_name": ["svc04", "svc00", "svc04"],
                "message": ["svc04 slow", "svc00 ok", "svc04 slower"],
            }
        ).to_parquet(case / "logs.parquet")
    if with_traces:
        pd.DataFrame(
            {
                "time": ["00:00"],
                "traceID": ["abc"],
                "spanID": ["def"],
                "serviceName": ["svc04"],
                "methodName": [None],
                "operationName": ["svc04/op"],
                "parentSpanID": [None],
                "startTimeMillis": [onset * 1000],
                "startTime": [onset * 1_000_000],
                "duration": [50_000],
                "statusCode": [0],
            }
        ).to_parquet(case / "traces.parquet")
    return case


def _fake_sandbox(tmp_path: Path, **kwargs) -> TelemetrySandbox:
    case = _build_fake_case(tmp_path)
    registry = PilotCaseRegistry(data_root=case.parent)
    # first opaque id maps to first sorted frozen id -> our fake dir name
    return TelemetrySandbox(registry, "RCA-P-01", **kwargs)


# ---------------------------------------------------------------------------
# mapping determinism + opacity
# ---------------------------------------------------------------------------
def test_registry_mapping_deterministic() -> None:
    r1, r2 = _real_registry(), _real_registry()
    assert r1.opaque_ids() == r2.opaque_ids()
    assert r1.opaque_ids() == tuple(f"RCA-P-{i:02d}" for i in range(1, 11))
    for opaque in r1.opaque_ids():
        assert r1.case_dir(opaque) == r2.case_dir(opaque)


def test_registry_opaque_ids_disjoint_from_upstream_ids() -> None:
    registry = _real_registry()
    for opaque in registry.opaque_ids():
        assert opaque not in set(FROZEN)
        for upstream in FROZEN:
            assert upstream not in opaque


def test_registry_tampered_roster_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        tel,
        "FROZEN_PILOT_IDS",
        tuple(sorted(set(FROZEN) - {"re1ob_cartservice_cpu_1"})),
    )
    with pytest.raises(ValueError, match="sha256"):
        PilotCaseRegistry()


def test_registry_unknown_opaque_id_raises() -> None:
    registry = _real_registry()
    with pytest.raises(tel.UnknownCaseIdError):
        registry.case_dir("RCA-P-99")
    with pytest.raises(tel.UnknownCaseIdError):
        TelemetrySandbox(registry, "RCA-P-99")


# ---------------------------------------------------------------------------
# leak guards
# ---------------------------------------------------------------------------
def test_sanitize_raises_on_upstream_id(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    sandbox = _fake_sandbox(tmp_path)

    def fake_payload(_k: int) -> dict[str, object]:
        return {"rows": [{"service": "svc00", "metric": FAKE_UPSTREAM_ID, "score": 1.0}]}

    monkeypatch.setattr(sandbox, "_top_anomalies_payload", fake_payload)
    with pytest.raises(LeakDetectedError):
        sandbox.top_anomalies()


def test_sanitize_raises_on_label_text(tmp_path: Path) -> None:
    sandbox = _fake_sandbox(tmp_path)
    sandbox._invoked = {}
    with pytest.raises(LeakDetectedError, match="root_cause"):
        sandbox._sanitize({"message": "see root_cause service label"})


def test_forbidden_literals_cover_all_frozen_pilot_ids(tmp_path: Path) -> None:
    """The sanitizer's forbidden set must contain every frozen pilot upstream
    case id and both label literals, so a leak in ANY agent-facing payload
    (tool result, call log, commit confirmation) is blocked."""
    forbidden = tel._forbidden_literals()
    for lit in tel.FORBIDDEN_LABEL_LITERALS:
        assert lit in forbidden
    for case_id in FROZEN:
        assert case_id in forbidden, f"frozen pilot id missing from forbidden set: {case_id}"
    # The root_cause.txt filename is blocked via the 'root_cause' literal.
    assert "root_cause" in forbidden
    # Case-insensitive match: an upper-cased echo of a frozen id is caught too.
    sandbox = _fake_sandbox(tmp_path)
    with pytest.raises(LeakDetectedError):
        sandbox._sanitize({"echo": FROZEN[0].upper()})


def test_root_cause_txt_never_opened(tmp_path: Path) -> None:
    case = _build_fake_case(tmp_path)
    (case / "root_cause.txt").write_text(SENTINEL)

    def tracked_opener(path: Path, mode: str):
        if path.name == "root_cause.txt":
            raise AssertionError("sandbox opened root_cause.txt")
        return open(path, mode)

    registry = PilotCaseRegistry(data_root=case.parent)
    sandbox = TelemetrySandbox(registry, "RCA-P-01", opener=tracked_opener)
    outputs = [
        sandbox.system_context(),
        sandbox.top_anomalies(),
        sandbox.service_metrics("svc04"),
        sandbox.service_logs("svc04"),
        sandbox.service_traces("svc04"),
        sandbox.submit_diagnosis(["svc04", "svc00"]),
    ]
    assert all(SENTINEL not in str(out) for out in outputs)
    assert all(p.name != "root_cause.txt" for p in sandbox.files_opened)


def test_root_cause_open_attempt_raises(tmp_path: Path) -> None:
    sandbox = _fake_sandbox(tmp_path)
    with pytest.raises(LeakDetectedError, match="root_cause.txt"):
        sandbox._open(Path("anything") / "root_cause.txt")


# ---------------------------------------------------------------------------
# anomaly math (synthetic spike)
# ---------------------------------------------------------------------------
def test_top_anomalies_ranks_synthetic_spike_first(tmp_path: Path) -> None:
    sandbox = _fake_sandbox(tmp_path)
    out = sandbox.top_anomalies(k=20)
    rows = out["rows"]
    # 13 service metrics + 1 constant = 14 columns; constant dropped -> 13 rows.
    assert len(rows) == 13
    assert rows[0]["service"] == "svc04"
    assert rows[0]["metric"] == "svc04_s1"
    assert rows[0]["score"] > 1.0
    # deterministic: two fresh sandboxes, identical output
    sandbox2 = _fake_sandbox(tmp_path, opener=open)
    assert sandbox2.top_anomalies(k=20)["rows"] == rows
    # the constant column was dropped
    assert all(r["metric"] != "svc00_const" for r in rows)


def test_top_anomalies_deterministic_and_capped(tmp_path: Path) -> None:
    s1 = _fake_sandbox(tmp_path).top_anomalies(k=5)
    s2 = _fake_sandbox(tmp_path).top_anomalies(k=5)
    assert s1 == s2
    assert all(r["score"] <= tel.SCORE_CAP for r in s1["rows"])


# ---------------------------------------------------------------------------
# system context + service tools
# ---------------------------------------------------------------------------
def test_system_context_shapes(tmp_path: Path) -> None:
    sandbox = _fake_sandbox(tmp_path)
    ctx = sandbox.system_context()
    assert len(ctx["services"]) == 13
    # svc00_const belongs to svc00; svc04 has exactly svc04_s1
    assert ctx["per_service_metric_count"]["svc04"] == 1
    assert ctx["per_service_metric_count"]["svc00"] == 2
    assert ctx["has_logs"] is True and ctx["has_traces"] is True
    assert ctx["anomaly_onset"] == 1_000_000


def test_service_tools_and_availability(tmp_path: Path) -> None:
    sandbox = _fake_sandbox(tmp_path)
    m = sandbox.service_metrics("svc04")
    assert {r["metric"] for r in m["rows"]} == {"svc04_s1"}
    spiked = m["rows"][0]
    assert spiked["faulty_max"] > spiked["normal_max"]
    assert spiked["z_peak"] > 0

    logs = sandbox.service_logs("svc04")
    assert logs["available"] is True and logs["count"] == 2
    assert all("root_cause" not in r["msg"].lower() for r in logs["rows"])

    traces = sandbox.service_traces("svc04")
    assert traces["available"] is True and traces["count"] == 1
    assert traces["rows"][0]["duration_ms"] == pytest.approx(50.0)
    assert traces["rows"][0]["status"] == 0

    # normalization: hyphen/upper-case input matches the same service
    assert sandbox.service_logs("SVC04")["count"] == 2


def test_missing_logs_traces_reports_unavailable(tmp_path: Path) -> None:
    case = _build_fake_case(tmp_path, with_logs=False, with_traces=False)
    registry = PilotCaseRegistry(data_root=case.parent)
    sandbox = TelemetrySandbox(registry, "RCA-P-01")
    assert sandbox.system_context()["has_logs"] is False
    out = sandbox.service_logs("svc04")
    assert out == {"available": False, "message": "no logs available"}
    out = sandbox.service_traces("svc04")
    assert out == {"available": False, "message": "no traces available"}


# ---------------------------------------------------------------------------
# diagnosis commit
# ---------------------------------------------------------------------------
def test_submit_diagnosis_semantics(tmp_path: Path) -> None:
    sandbox = _fake_sandbox(tmp_path)
    conf = sandbox.submit_diagnosis(["Svc04", "svc00", "svc-01"])
    assert conf["committed"] is True
    assert conf["ranking"] == ["svc04", "svc00", "svc01"]
    expected = hashlib.sha256("svc04\nsvc00\nsvc01".encode()).hexdigest()
    assert conf["ranking_sha256"] == expected
    # stable across normalizations
    sandbox2 = _fake_sandbox(tmp_path)
    assert sandbox2.submit_diagnosis(["svc04", "SVC00", "svc01"])["ranking_sha256"] == expected
    with pytest.raises(DiagnosisAlreadyCommitted):
        sandbox.submit_diagnosis(["svc04"])


def test_submit_diagnosis_validates_inventory(tmp_path: Path) -> None:
    sandbox = _fake_sandbox(tmp_path)
    with pytest.raises(UnknownServiceError):
        sandbox.submit_diagnosis(["no-such-service"])
    with pytest.raises(UnknownServiceError):
        sandbox.submit_diagnosis([])


# ---------------------------------------------------------------------------
# tool budget
# ---------------------------------------------------------------------------
def test_tool_budget_total_exhaustion(tmp_path: Path) -> None:
    sandbox = _fake_sandbox(tmp_path)
    for _ in range(tel.MAX_TOOL_CALLS):
        sandbox.system_context()
    assert len(sandbox.call_log) == tel.MAX_TOOL_CALLS
    with pytest.raises(ToolBudgetExhausted, match="total"):
        sandbox.system_context()


def test_tool_budget_logs_traces_per_tool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tel, "MAX_TOOL_CALLS", 1000)  # isolate the per-tool caps
    sandbox = _fake_sandbox(tmp_path)
    for _ in range(tel.MAX_LOGS_CALLS):
        sandbox.service_logs("svc04")
    with pytest.raises(ToolBudgetExhausted, match="service_logs"):
        sandbox.service_logs("svc04")
    for _ in range(tel.MAX_TRACES_CALLS):
        sandbox.service_traces("svc04")
    with pytest.raises(ToolBudgetExhausted, match="service_traces"):
        sandbox.service_traces("svc04")
    # other tools still work within the total budget
    sandbox.top_anomalies()
    assert {e["tool"] for e in sandbox.call_log} == {"service_logs", "service_traces", "top_anomalies"}


def test_call_log_shape(tmp_path: Path) -> None:
    sandbox = _fake_sandbox(tmp_path)
    sandbox.top_anomalies(k=3)
    entry = sandbox.call_log[-1]
    assert set(entry) == {"tool", "args", "wall_ms", "payload_bytes"}
    assert entry["args"] == {"k": 3}
    assert entry["payload_bytes"] > 0
    assert entry["wall_ms"] >= 0


# ---------------------------------------------------------------------------
# service-level success (official coarse semantics)
# ---------------------------------------------------------------------------
def test_service_level_success_cases() -> None:
    assert service_level_success(["a", "b", "c", "d", "e"], "a", k=5)  # hit at 1
    assert service_level_success(["a", "b", "c", "d", "e"], "e", k=5)  # hit at 5
    assert not service_level_success(["a", "b", "c", "d", "e", "f"], "f", k=5)  # miss at 6
    assert service_level_success(["a", "b", "c", "d", "e", "f"], "f", k=6)
    # normalization
    assert service_level_success(["Front-End"], "frontend", k=5)
    assert not service_level_success(["frontend"], "front-end-extra", k=5)


# ---------------------------------------------------------------------------
# smoke test on the real downloaded pilot data (skipif absent)
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not (PILOT / "re2ob_currencyservice_delay_1" / "metrics.parquet").is_file(),
                    reason="pilot telemetry not downloaded")
def test_smoke_real_currency_case() -> None:
    registry = _real_registry()
    # sorted frozen ids: re2ob_currencyservice_delay_1 is the 6th
    opaque = registry.opaque_ids()[5]
    sandbox = TelemetrySandbox(registry, opaque)
    out = sandbox.top_anomalies(k=20)
    rows = out["rows"]
    assert len(rows) == 20
    assert len({(r["service"], r["metric"]) for r in rows}) == 20
    assert all(r["score"] > 0 for r in rows)
    scores = [r["score"] for r in rows]
    assert scores == sorted(scores, reverse=True)
    m = sandbox.service_metrics("currencyservice")
    assert m["rows"], "currencyservice should have metrics"
    assert all(r["metric"].startswith("currencyservice_") for r in m["rows"])
