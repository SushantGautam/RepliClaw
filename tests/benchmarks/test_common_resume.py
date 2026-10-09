"""Idempotency and atomicity tests for the resumable run-state contract.

Offline, deterministic: fixed timestamps are not needed because the state
file's clocks are not part of any asserted invariant — only transitions,
payloads, and file shape are asserted.
"""
from __future__ import annotations

import json

import pytest

from repliclaw.benchmarks.common.records import RunRecord, TokenUsage
from repliclaw.benchmarks.common.resume import (
    RUN_STATE_FILENAME,
    RUN_STATE_SCHEMA,
    RunAlreadyFinished,
    RunState,
    RunStateError,
    StateConflict,
    run_id_for,
)


def make_record(seed: int = 0, wall: float = 12.0) -> RunRecord:
    return RunRecord(
        run_id=run_id_for("case_a", "arm_b", seed),
        arm="arm_b",
        case="case_a",
        seed=seed,
        model="m",
        provider="p",
        started_at="2026-10-09T10:00:00Z",
        finished_at="2026-10-09T10:01:00Z",
        status="completed",
        token_usage=TokenUsage(input=100, output=10, cached=None, total=110, usage_present=True),
        wall_s=wall,
    )


def test_fresh_begin_finish_cycle(tmp_path):
    state = RunState(tmp_path, "case_a::arm_b::seed0")
    assert not state.exists and not state.is_finished
    state.begin()
    assert state.is_running and state.attempts == 1
    rec = state.mark_finished(make_record())
    assert state.is_finished and rec.state == "finished"
    assert state.record() == make_record()


def test_begin_is_idempotent_and_bumps_attempts(tmp_path):
    state = RunState(tmp_path, "case_a::arm_b::seed0")
    state.begin()
    state.begin()
    state.begin()
    assert state.attempts == 3
    assert state.is_running


def test_finished_run_cannot_be_reopened(tmp_path):
    state = RunState(tmp_path, "case_a::arm_b::seed0")
    state.begin()
    state.mark_finished(make_record())
    with pytest.raises(RunAlreadyFinished):
        state.begin()


def test_mark_finished_is_idempotent_for_same_record(tmp_path):
    state = RunState(tmp_path, "case_a::arm_b::seed0")
    state.begin()
    state.mark_finished(make_record())
    # A crashed driver retrying finish with the identical record: no-op.
    result = state.mark_finished(make_record())
    assert result.record_sha256 is not None
    assert state.attempts == 1  # finish does not bump attempts


def test_mark_finished_conflicts_on_different_record(tmp_path):
    state = RunState(tmp_path, "case_a::arm_b::seed0")
    state.begin()
    state.mark_finished(make_record(wall=12.0))
    with pytest.raises(StateConflict, match="different record"):
        state.mark_finished(make_record(wall=99.0))
    # The original record survives the rejected write.
    assert state.record().wall_s == 12.0


def test_finish_without_begin_rejected(tmp_path):
    state = RunState(tmp_path, "case_a::arm_b::seed0")
    with pytest.raises(RunStateError, match="begin"):
        state.mark_finished(make_record())


def test_record_run_id_mismatch_rejected(tmp_path):
    state = RunState(tmp_path, "case_a::arm_b::seed0")
    state.begin()
    with pytest.raises(RunStateError, match="record run_id"):
        state.mark_finished(make_record(seed=5))


def test_state_is_persisted_and_reloaded(tmp_path):
    rid = "case_a::arm_b::seed0"
    a = RunState(tmp_path, rid)
    a.begin()
    a.mark_finished(make_record())
    b = RunState(tmp_path, rid)  # fresh handle, same directory
    assert b.is_finished
    assert b.record() == make_record()


def test_state_file_rejects_foreign_run_id(tmp_path):
    RunState(tmp_path, "case_a::arm_b::seed0").begin()
    with pytest.raises(RunStateError, match="belongs to run"):
        RunState(tmp_path, "other::case::seed1")


def test_no_tmp_file_left_after_write(tmp_path):
    RunState(tmp_path, "case_a::arm_b::seed0").begin()
    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == []
    assert (tmp_path / RUN_STATE_FILENAME).is_file()


def test_state_file_shape_and_canonical_keys(tmp_path):
    state = RunState(tmp_path, "case_a::arm_b::seed0")
    state.begin()
    state.mark_finished(make_record())
    raw = json.loads((tmp_path / RUN_STATE_FILENAME).read_text(encoding="utf-8"))
    assert raw["schema"] == RUN_STATE_SCHEMA
    assert raw["state"] == "finished"
    assert raw["run_id"] == "case_a::arm_b::seed0"
    assert raw["record"]["schema"] == "repliclaw.run_record/v1"
    assert raw["record_sha256"] and len(raw["record_sha256"]) == 64
    # record payload round-trips back to a valid RunRecord
    assert RunRecord.from_dict(raw["record"]).validate().ok


def test_corrupt_state_file_raises(tmp_path):
    (tmp_path / RUN_STATE_FILENAME).write_text("{not json")
    with pytest.raises(RunStateError, match="corrupt"):
        RunState(tmp_path, "case_a::arm_b::seed0")


def test_two_run_dirs_are_independent(tmp_path):
    s0 = RunState(tmp_path / "seed0", "case_a::arm_b::seed0")
    s1 = RunState(tmp_path / "seed1", "case_a::arm_b::seed1")
    s0.begin()
    s0.mark_finished(make_record(0))
    assert not s1.exists
    s1.begin()
    assert s1.is_running
    s1.mark_finished(make_record(1))
    assert s1.record().run_id == "case_a::arm_b::seed1"


def test_resume_driver_skips_finished_run(tmp_path):
    """The exact pattern a lane driver uses: skip finished, resume running."""
    rid = "case_a::arm_b::seed0"
    s = RunState(tmp_path, rid)
    s.begin()
    s.mark_finished(make_record())

    # Second driver invocation:
    s2 = RunState(tmp_path, rid)
    if s2.is_finished:
        record = s2.record()
    else:
        s2.begin()
        raise AssertionError("driver should have seen a finished run")
    assert record.seed == 0


def test_run_id_for_shape():
    assert run_id_for("case_a", "arm_b", 7) == "case_a::arm_b::seed7"
    assert run_id_for("case_a", "arm_b", 0) == "case_a::arm_b::seed0"
