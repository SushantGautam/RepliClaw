"""Provenance capture/verify tests.

Offline and deterministic: a disposable git repo is created under the
program scratch dir (never the RepliClaw worktrees) with fixed author
identity and timestamp. No network.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from repliclaw.benchmarks.common.provenance import (
    PROVENANCE_FILENAME,
    ProvenanceError,
    RepoPin,
    capture_provenance,
    package_pins,
    read_provenance,
    sha256_file,
    verify_provenance,
)

GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "prov-test",
    "GIT_AUTHOR_EMAIL": "prov-test@example.com",
    "GIT_COMMITTER_NAME": "prov-test",
    "GIT_COMMITTER_EMAIL": "prov-test@example.com",
    "GIT_AUTHOR_DATE": "2026-10-09T10:00:00 +0000",
    "GIT_COMMITTER_DATE": "2026-10-09T10:00:00 +0000",
}


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], env=GIT_ENV, check=True, capture_output=True)


@pytest.fixture()
def repos(tmp_path: Path):
    """Two disposable git repos (main + upstream) and a dataset file."""
    main = tmp_path / "main"
    upstream = tmp_path / "upstream"
    for r in (main, upstream):
        r.mkdir(parents=True)
        _git(r, "init", "-q", "-b", "main")
    (main / "a.txt").write_text("main content")
    _git(main, "add", "a.txt")
    _git(main, "commit", "-q", "-m", "main commit")
    main_sha = subprocess.run(["git", "-C", str(main), "rev-parse", "HEAD"],
                              env=GIT_ENV, capture_output=True, text=True, check=True).stdout.strip()

    (upstream / "b.txt").write_text("upstream content")
    _git(upstream, "add", "b.txt")
    _git(upstream, "commit", "-q", "-m", "upstream commit")
    upstream_sha = subprocess.run(["git", "-C", str(upstream), "rev-parse", "HEAD"],
                                  env=GIT_ENV, capture_output=True, text=True, check=True).stdout.strip()

    dataset = tmp_path / "dataset.json"
    dataset.write_text('{"x": 1}\n')
    return main, main_sha, upstream, upstream_sha, dataset


def test_capture_pins_git_shas_and_dataset_hash(repos):
    main, main_sha, upstream, upstream_sha, dataset = repos
    run_dir = main / "runs" / "r1"
    record = capture_provenance(
        run_dir,
        run_id="case::arm::seed0",
        upstream=[RepoPin(name="up", path=upstream, url="https://example.org/up.git")],
        dataset_files={"data/case.json": dataset},
        repo=main,
        dependency_names=["pytest"],
        captured_at="2026-10-09T10:00:00Z",
    )
    assert record.repliclaw_git_sha == main_sha
    assert record.repliclaw_dirty is False
    assert record.upstream_repos["up"].sha == upstream_sha
    assert record.upstream_repos["up"].url == "https://example.org/up.git"
    assert record.dataset_sha256s["data/case.json"] == sha256_file(dataset)
    assert record.dependency_pins.get("pytest")  # pytest is in the venv
    assert record.captured_at == "2026-10-09T10:00:00Z"

    on_disk = json.loads((run_dir / PROVENANCE_FILENAME).read_text(encoding="utf-8"))
    assert on_disk["schema"] == "repliclaw.provenance/v1"
    assert on_disk["repliclaw_git_sha"] == main_sha


def test_capture_dirty_tree_flag(repos):
    main, main_sha, *_ = repos
    (main / "dirty.txt").write_text("uncommitted")
    record = capture_provenance(main / "runs" / "r2", run_id="case::arm::seed1", repo=main,
                                captured_at="2026-10-09T10:00:00Z")
    assert record.repliclaw_dirty is True


def test_capture_fails_loud_without_git_head(repos, tmp_path):
    with pytest.raises(ProvenanceError, match="fail-loud"):
        capture_provenance(tmp_path / "no_git", run_id="x::y::seed0", repo=tmp_path)


def test_capture_rejects_missing_dataset_file(repos, tmp_path):
    main, *_ = repos
    with pytest.raises(ProvenanceError, match="missing"):
        capture_provenance(tmp_path / "run", run_id="x::y::seed0", repo=main,
                           dataset_files={"data/none.json": tmp_path / "none.json"})


def test_verify_passes_when_untouched(repos):
    main, main_sha, upstream, upstream_sha, dataset = repos
    run_dir = main / "runs" / "r3"
    capture_provenance(
        run_dir, "case::arm::seed2",
        upstream=[RepoPin(name="up", path=upstream)],
        dataset_files={"data/case.json": dataset},
        repo=main,
        captured_at="2026-10-09T10:00:00Z",
    )
    assert verify_provenance(run_dir, dataset_files={"data/case.json": dataset},
                             expected_repliclaw_sha=main_sha) == []


def test_verify_detects_dataset_drift(repos):
    main, main_sha, _up, _sha, dataset = repos
    run_dir = main / "runs" / "r4"
    capture_provenance(run_dir, "case::arm::seed3", dataset_files={"data/case.json": dataset},
                       repo=main, captured_at="2026-10-09T10:00:00Z")
    dataset.write_text('{"x": 999}\n')  # drift after capture
    issues = verify_provenance(run_dir, dataset_files={"data/case.json": dataset})
    assert len(issues) == 1
    assert "sha256 drift" in issues[0]


def test_verify_detects_missing_dataset(repos):
    main, *_ = repos
    run_dir = main / "runs" / "r5"
    capture_provenance(run_dir, "case::arm::seed4", dataset_files={"data/case.json": main / "a.txt"},
                       repo=main, captured_at="2026-10-09T10:00:00Z")
    issues = verify_provenance(run_dir, dataset_files={"data/case.json": main / "does_not_exist.json"})
    assert any("missing" in i for i in issues)


def test_verify_detects_unrecorded_dataset(repos):
    main, *_ = repos
    run_dir = main / "runs" / "r6"
    capture_provenance(run_dir, "case::arm::seed5", repo=main, captured_at="2026-10-09T10:00:00Z")
    issues = verify_provenance(run_dir, dataset_files={"data/extra.json": main / "a.txt"})
    assert any("no hash recorded" in i for i in issues)


def test_verify_detects_wrong_repliclaw_sha(repos):
    main, _sha, _up, _upsha, _ds = repos
    run_dir = main / "runs" / "r7"
    capture_provenance(run_dir, "case::arm::seed6", repo=main, captured_at="2026-10-09T10:00:00Z")
    issues = verify_provenance(run_dir, expected_repliclaw_sha="f" * 40)
    assert any("repliclaw git sha mismatch" in i for i in issues)


def test_verify_detects_tampered_file(tmp_path):
    (tmp_path / "run").mkdir()
    (tmp_path / "run" / PROVENANCE_FILENAME).write_text(json.dumps({"schema": "repliclaw.provenance/v1"}))
    issues = verify_provenance(tmp_path / "run")
    assert any(i.startswith("schema:") for i in issues)


def test_read_provenance_missing_file(tmp_path):
    with pytest.raises(ProvenanceError, match="no provenance"):
        read_provenance(tmp_path)


def test_package_pins_includes_common_deps():
    pins = package_pins(["pytest"])
    assert pins.get("pytest")
