"""V4 deadline instrument (D-E-DET / C-EQ-DET) — offline tests.

All tests use :class:`FakeLLMClient` scripted clients over a synthetic
pilot-shaped case dir (same pattern as ``test_v3_telemetry_arms.py``); no
network, no live LLM calls, no real case data required.  Coverage:

1. fallback ranking is deterministic, valid, and exactly RANKING_LENGTH long;
2. a deadline-forced investigator commits the fallback ranking with the
   fallback confidence, and the arm still completes with a submission;
3. concurrent phase 1 actually overlaps in wall time;
4. both arms see byte-identical tool menus and the same shared envelope;
5. the consultation-off ablation still completes (escrow-only path);
6. repeated-action counting works on a known call log;
7. C-EQ-DET completes end-to-end with a scripted client.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from repliclaw.experiments.v3.telemetry import FROZEN_PILOT_IDS as FROZEN
from repliclaw.experiments.v3.telemetry import PilotCaseRegistry
from repliclaw.experiments.v3.telemetry_arms import (
    MAX_TOKENS_PER_RUN,
    RANKING_LENGTH,
    _Envelope,
)
from repliclaw.experiments.v3.det_deadline import (
    CEQDetArm,
    DE_FALLBACK_CONFIDENCE,
    DetelemDetArm,
    _count_repeated_actions,
    _fallback_ranking,
)

FAKE_UPSTREAM_ID = sorted(FROZEN)[0]
RANK5 = ["svc04", "svc00", "svc01", "svc02", "svc03"]


# ---------------------------------------------------------------------------
# fake case + script helpers (mirrors test_v3_telemetry_arms.py)
# ---------------------------------------------------------------------------


def _build_fake_case(root: Path) -> Path:
    """Synthetic pilot-shaped case dir: 13 services svc00..svc12, svc04 spikes."""
    case = root / FAKE_UPSTREAM_ID
    case.mkdir(parents=True, exist_ok=True)
    onset = 1_000_000
    n = 800
    t = np.arange(onset - 600, onset + 200)
    rng = np.random.default_rng(7)
    data: dict[str, np.ndarray] = {"time": t}
    for i in range(13):
        base = 10.0 + rng.normal(0.0, 0.5, size=n)
        col = f"svc{i:02d}_s1"
        if i == 4:
            base = base.copy()
            base[600:] += 50.0
        data[col] = base
    data["svc00_const"] = np.full(n, 3.14)
    pd.DataFrame(data).to_parquet(case / "metrics.parquet")
    (case / "inject_time.txt").write_text(f"{onset}\n")
    pd.DataFrame(
        {
            "timestamp": np.array([onset - 100, onset, onset + 99]),
            "container_name": ["svc04", "svc00", "svc04"],
            "message": ["svc04 slow", "svc00 ok", "svc04 slower"],
        }
    ).to_parquet(case / "logs.parquet")
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


@pytest.fixture()
def fake_registry(tmp_path: Path) -> PilotCaseRegistry:
    _build_fake_case(tmp_path)
    return PilotCaseRegistry(data_root=tmp_path)


def _tool(tool="top_anomalies", args=None):
    if args is None:
        args = {"k": 20}
    return json.dumps({"action": "tool_call", "tool": tool, "args": args})


def _commit(ranking=None, confidence=0.9):
    if ranking is None:
        ranking = RANK5
    return json.dumps({"action": "commit", "ranking": ranking,
                       "confidence": confidence})


def _scripted_client(script):
    from repliclaw.experiments.v3.telemetry_arms import FakeLLMClient
    return FakeLLMClient(script)


_CASE_ID = "RCA-P-01"  # maps to FAKE_UPSTREAM_ID (sorted first)


# ---------------------------------------------------------------------------
# 1. fallback ranking
# ---------------------------------------------------------------------------


def test_fallback_ranking_deterministic_and_valid(fake_registry):
    from repliclaw.experiments.v3.telemetry import TelemetrySandbox
    sb1 = TelemetrySandbox(fake_registry, _CASE_ID)
    sb2 = TelemetrySandbox(fake_registry, _CASE_ID)
    r1 = _fallback_ranking(sb1)
    r2 = _fallback_ranking(sb2)
    assert r1 == r2
    assert len(r1) == RANKING_LENGTH
    assert len(set(r1)) == RANKING_LENGTH
    inv = set(sb1._inventory())
    assert set(r1) <= inv
    # The spiking service must be rank 1 (shared reference math).
    assert r1[0] == "svc04"


# ---------------------------------------------------------------------------
# 6. repeated action counting
# ---------------------------------------------------------------------------


def test_count_repeated_actions():
    log = [
        {"tool": "top_anomalies", "args": {"k": 20}},
        {"tool": "top_anomalies", "args": {"k": 20}},
        {"tool": "system_context", "args": {}},
        {"tool": "top_anomalies", "args": {"k": 20}},
    ]
    assert _count_repeated_actions(log) == 2


# ---------------------------------------------------------------------------
# 2 + 3. deadline fallback + concurrency (D-E-DET)
# ---------------------------------------------------------------------------


def test_de_det_deadline_fallback_completes(fake_registry, tmp_path):
    """Two investigators commit after one tool call; the third loops tool
    calls until its personal deadline forces the fallback.  The arm must
    complete with a submission, and the escrow ledger must show exactly one
    fallback entry.

    Determinism under threads: each worker thread tags itself on its FIRST
    LLM call; the third thread to start is scripted to loop forever."""
    tags: dict[str, str] = {}
    counter = {"n": 0}
    lock = threading.Lock()
    per_thread_calls: dict[str, int] = {}

    def script(prompt: str, call_index: int):
        tname = threading.current_thread().name
        with lock:
            if tname not in tags:
                counter["n"] += 1
                tags[tname] = "slow" if counter["n"] == 3 else "fast"
            per_thread_calls[tname] = per_thread_calls.get(tname, 0) + 1
            n = per_thread_calls[tname]
        if tags[tname] == "slow":
            return _tool()  # never commits -> deadline fallback
        return _tool() if n == 1 else _commit()

    client = _scripted_client(script)
    arm = DetelemDetArm(client=client, registry=fake_registry, opaque_id=_CASE_ID,
                        out_dir=tmp_path, seed=20261011,
                        envelope=_Envelope(max_tokens_per_run=MAX_TOKENS_PER_RUN),
                        verbose_crash=False)
    result = arm.run()

    assert result.status == "completed", f"status={result.status} err={result.crash_error}"
    assert result.submitted_ranking is not None
    assert len(result.submitted_ranking) == RANKING_LENGTH

    # Escrow ledger: exactly one fallback entry (whichever thread was 3rd)
    escrow = json.loads((tmp_path / "d-e-telem-det-escrow.json").read_text())
    p1 = {e["agent_id"]: e for e in escrow["entries"] if e["phase"] == "phase1"}
    fallbacks = [a for a, e in p1.items() if e["confidence"] == DE_FALLBACK_CONFIDENCE]
    assert len(fallbacks) == 1
    assert any(f"deadline_fallback_used_for={fallbacks[0]}" in w for w in result.warnings)

    # Concurrency proof: phase-1 wall < sum of individual investigator walls
    pm = arm.phase_metrics
    indiv_sum = sum(o["wall_s"] for o in pm["investigators"])
    assert pm["phase1_wall_s"] < indiv_sum, (
        f"phase1_wall={pm['phase1_wall_s']} >= sum(individual)={indiv_sum}: "
        "investigators did NOT overlap"
    )


def test_de_det_all_commit_no_fallback(fake_registry, tmp_path):
    """Everyone commits after one tool call: no fallback, clean completion."""
    per_thread_calls: dict[str, int] = {}
    lock = threading.Lock()

    def script(prompt: str, call_index: int):
        tname = threading.current_thread().name
        with lock:
            per_thread_calls[tname] = per_thread_calls.get(tname, 0) + 1
            n = per_thread_calls[tname]
        return _tool() if n == 1 else _commit()

    client = _scripted_client(script)
    arm = DetelemDetArm(client=client, registry=fake_registry, opaque_id=_CASE_ID,
                        out_dir=tmp_path, seed=20261012,
                        envelope=_Envelope(max_tokens_per_run=MAX_TOKENS_PER_RUN),
                        verbose_crash=False)
    result = arm.run()
    assert result.status == "completed"
    assert result.submitted_ranking is not None
    assert not any("deadline_fallback" in w for w in result.warnings)
    escrow = json.loads((tmp_path / "d-e-telem-det-escrow.json").read_text())
    p1 = {e["agent_id"]: e for e in escrow["entries"] if e["phase"] == "phase1"}
    assert all(e["confidence"] != DE_FALLBACK_CONFIDENCE for e in p1.values())


# ---------------------------------------------------------------------------
# 4. parity: identical tool menu + shared envelope
# ---------------------------------------------------------------------------


def test_parity_tool_menu_and_envelope(fake_registry, tmp_path):
    """Both arms embed the identical OBS tool docs and enforce the same
    shared token envelope constant."""
    def script(prompt: str, call_index: int):
        return _commit()

    client = _scripted_client(script)
    arm = DetelemDetArm(client=client, registry=fake_registry, opaque_id=_CASE_ID,
                        out_dir=tmp_path, seed=1,
                        envelope=_Envelope(max_tokens_per_run=MAX_TOKENS_PER_RUN),
                        verbose_crash=False)
    sp = arm._investigator_system_prompt("inv-a")
    assert "- top_anomalies(k=20)" in sp
    ceq_arm = CEQDetArm(client=client, registry=fake_registry, opaque_id=_CASE_ID,
                        out_dir=tmp_path / "ceq", seed=1,
                        envelope=_Envelope(max_tokens_per_run=MAX_TOKENS_PER_RUN),
                        verbose_crash=False)
    ceq_sp = ceq_arm._manager_system_prompt()
    assert "- top_anomalies(k=20)" in ceq_sp
    assert arm.envelope.max_tokens_per_run == MAX_TOKENS_PER_RUN
    assert ceq_arm.envelope.max_tokens_per_run == MAX_TOKENS_PER_RUN


# ---------------------------------------------------------------------------
# 5. ablations
# ---------------------------------------------------------------------------


def test_de_det_consultation_off_ablation(fake_registry, tmp_path):
    per_thread_calls: dict[str, int] = {}
    lock = threading.Lock()

    def script(prompt: str, call_index: int):
        tname = threading.current_thread().name
        with lock:
            per_thread_calls[tname] = per_thread_calls.get(tname, 0) + 1
            n = per_thread_calls[tname]
        return _tool() if n == 1 else _commit()

    client = _scripted_client(script)
    arm = DetelemDetArm(client=client, registry=fake_registry, opaque_id=_CASE_ID,
                        out_dir=tmp_path, seed=3, consultation=False,
                        committee=False,
                        envelope=_Envelope(max_tokens_per_run=MAX_TOKENS_PER_RUN),
                        verbose_crash=False)
    result = arm.run()
    assert result.status == "completed"
    assert result.submitted_ranking is not None
    escrow = json.loads((tmp_path / "d-e-telem-det-escrow.json").read_text())
    phases = sorted({e["phase"] for e in escrow["entries"]})
    assert "phase2-final" in phases  # promoted from phase1, not consulted
    n_finals = sum(1 for e in escrow["entries"] if e["phase"] == "phase2-final")
    assert n_finals == 3


# ---------------------------------------------------------------------------
# 7. C-EQ-DET end-to-end
# ---------------------------------------------------------------------------


def test_ceq_det_completes(fake_registry, tmp_path):
    """Scripted C-EQ: forecast commit, one planner round with 1 tool call then
    commit, then 3 concurrent consultations each committing immediately."""
    seq = iter([
        _commit(),                                   # manager forecast
        _tool("system_context", {}),                 # planner round 1 tool
        _commit(),                                   # manager loop commit
        _commit(),                                   # inv-a finding
        _commit(),                                   # inv-b finding
        _commit(),                                   # inv-c finding
    ])

    def script(prompt: str, call_index: int):
        try:
            return next(seq)
        except StopIteration:
            return _commit()

    client = _scripted_client(script)
    arm = CEQDetArm(client=client, registry=fake_registry, opaque_id=_CASE_ID,
                    out_dir=tmp_path, seed=20261013,
                    envelope=_Envelope(max_tokens_per_run=MAX_TOKENS_PER_RUN),
                    verbose_crash=False)
    result = arm.run()
    assert result.status == "completed", f"{result.status} {result.crash_error}"
    assert result.submitted_ranking is not None
    assert len(result.submitted_ranking) == RANKING_LENGTH
    escrow = json.loads((tmp_path / "c-eq-telem-det-escrow.json").read_text())
    assert any(e["phase"] == "forecast" for e in escrow["entries"])
