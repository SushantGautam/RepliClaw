"""Tests for the AgentRx read-only loader: counts, joins, hash verification.

All tests run against the pinned dataset at ``stg2-worktrees/agentrx-data``
when present; tamper tests use tmp copies so the pinned files are never mutated.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from repliclaw.benchmarks.agentrx.loader import (
    PINNED_FILES,
    PINNED_REPO_SHA,
    DatasetHashMismatchError,
    load_agentrx_eval_set,
)

DATA_DIR = Path("/Users/sushantgautam/Documents/stg2-worktrees/agentrx-data")

pytestmark = pytest.mark.skipif(not DATA_DIR.is_dir(), reason="pinned agentrx-data not present")


def _copy_dataset(tmp_path: Path) -> Path:
    target = tmp_path / "agentrx-data"
    shutil.copytree(DATA_DIR, target)
    return target


@pytest.fixture(scope="module")
def eval_set():
    return load_agentrx_eval_set(DATA_DIR)


def test_pinned_sha_is_40_hex():
    assert len(PINNED_REPO_SHA) == 40
    int(PINNED_REPO_SHA, 16)


def test_eval_set_counts(eval_set):
    assert len(eval_set.cases) == 73
    assert sum(1 for c in eval_set.cases if c.domain == "tau_retail") == 29
    assert sum(1 for c in eval_set.cases if c.domain == "magentic_one") == 44
    assert sum(len(c.failures) for c in eval_set.cases) == 334
    assert len(eval_set.unannotated_magentic_ids) == 14
    assert "14" in eval_set.notes and "EXCLUDED" in eval_set.notes


def test_case_structure_and_root_cause(eval_set):
    for c in eval_set.cases:
        assert 1 <= c.root_cause.category_code <= 10
        rc = next(f for f in c.failures if f.failure_id == c.root_cause.failure_id)
        assert rc.step_number == c.root_cause.step_number
        assert rc.failure_category == c.root_cause.category
        assert c.trajectory_length == len(c.steps) == len({s.index for s in c.steps})
        assert c.instruction


def test_tau_prefix_drift_join(eval_set):
    """tau raw ids are tau_retail_<n>; case ids are the unprefixed annotated ids."""
    tau = [c for c in eval_set.cases if c.domain == "tau_retail"]
    assert all(c.case_id.isdigit() for c in tau)
    assert all(c.raw_trajectory_id == f"tau_retail_{c.case_id}" for c in tau)
    mag = [c for c in eval_set.cases if c.domain == "magentic_one"]
    # UUID-like ids match raw ids directly (mixed 36-char UUID and 64-char hex forms)
    assert all(c.raw_trajectory_id == c.case_id for c in mag)
    assert {len(c.case_id) for c in mag} <= {36, 64}


def test_data_hashes_match_pinned(eval_set):
    assert eval_set.data_hashes == {name: PINNED_FILES[name][0] for name in PINNED_FILES}


def test_hash_mismatch_fails_loud(tmp_path):
    target = _copy_dataset(tmp_path)
    # tamper: flip one byte in the middle of a pinned jsonl line
    path = target / "tau_retail.jsonl"
    raw = path.read_bytes()
    tampered = raw[:100] + b"X" + raw[101:]
    path.write_bytes(tampered)
    with pytest.raises(DatasetHashMismatchError, match="tau_retail.jsonl"):
        load_agentrx_eval_set(target)


def test_missing_file_fails_loud(tmp_path):
    target = _copy_dataset(tmp_path)
    (target / "magentic_dataset.jsonl").unlink()
    with pytest.raises(DatasetHashMismatchError, match="missing"):
        load_agentrx_eval_set(target)


def test_unannotated_magentic_ids_excluded(eval_set):
    assert not any(c.case_id in eval_set.unannotated_magentic_ids for c in eval_set.cases)
