"""Offline tests for scripts/r2_preflight.py (R-2 token-floor extraction).

Covers the contract docs/experiments/R2_TOKEN_FLOOR_PREFLIGHT_PROTOCOL.md
relies on:
  1. happy path: 3-arm run tree -> floor_r2.json with schema
     p08.token_floor_r2/1, correct arms dict, verdict OK;
  2. a floor > 60% of the 60k per-arm ceiling -> verdict CHECK;
  3. a zero-token arm -> hard fail (non-zero exit, no output written);
  4. a missing arm -> hard fail (non-zero exit, no output written).

Fixtures use the REAL field names from the runner writers
(src/repliclaw/comparators/runner.py): budget_ledger.json ``totals``
(total_tokens / llm_calls / wall_s) and run_metadata.json
(status / arm / harness_seed / tree_sha / a9_defect_instruction_sha256).
Zero LLM calls anywhere.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "r2_preflight.py"

ARMS = ("open_sharing_swarm", "adaptive_central", "single_agent")
SEED = 20261010
PIN = "deadbeef" * 5


def load_r2():
    spec = importlib.util.spec_from_file_location("r2_preflight", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["r2_preflight"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def r2():
    return load_r2()


def _ledger(tokens: int, llm_calls: int = 1, wall_s: float = 1.0) -> dict[str, Any]:
    # Real budget_ledger.json shape (runner.py _write_offline_artifacts /
    # _write_live_strategy_artifacts).
    return {
        "schema": "p08.budget_ledger/1",
        "envelope": {"max_agents": 4, "max_tokens": 60000,
                     "max_wall_s": 900.0, "sha256": "x" * 64},
        "calls": [{
            "seq": 1, "agent_id": None,
            "prompt_tokens": tokens, "completion_tokens": 0,
            "total_tokens": tokens, "wall_s": wall_s,
            "usage_present": True,
        }],
        "totals": {
            "prompt_tokens": tokens, "completion_tokens": 0,
            "total_tokens": tokens, "llm_calls": llm_calls,
            "wall_s": wall_s,
        },
        "overflow_events": [],
    }


def _meta(arm: str, status: str = "completed",
          harness_seed: int = SEED) -> dict[str, Any]:
    # Real run_metadata.json fields (runner.py run_one_arm).
    return {
        "schema": "p08.run_metadata/1",
        "arm": arm,
        "arm_key": arm,
        "case_id": "policy_rag_v1",
        "run_id": f"{arm}/run-01",
        "harness_seed": harness_seed,
        "status": status,
        "tree_sha": "c0e92ea02c2bff03b743bfe338ce98f03fcb554b",
        "a9_defect_instruction_sha256": "5c7192eb7f8d770a038dfe361a039402d7068dc879d21a6e2ff1ca55465996e7",
        "wall_s": 0.02,
    }


def _make_run_tree(run_dir: Path, tokens: dict[str, int],
                   status: dict[str, str] | None = None) -> None:
    status = status or {}
    for arm in ARMS:
        run01 = run_dir / arm / "run-01"
        run01.mkdir(parents=True)
        (run01 / "budget_ledger.json").write_text(
            json.dumps(_ledger(tokens[arm])), encoding="utf-8")
        (run01 / "run_metadata.json").write_text(
            json.dumps(_meta(arm, status.get(arm, "completed"))),
            encoding="utf-8")


def _run_cli(r2: Any, run_dir: Path, out: Path,
             capsys: pytest.CaptureFixture[str]) -> int:
    rc = r2.main(["--run-dir", str(run_dir), "--output", str(out),
                  "--pin", PIN, "--case", "policy_rag_v1"])
    return rc


def test_happy_path_schema_and_verdict_ok(r2: Any, tmp_path: Path,
                                          capsys: pytest.CaptureFixture[str]) -> None:
    run_dir = tmp_path / "run"
    # All arms well under 60% of 60k (36k).
    _make_run_tree(run_dir, {"open_sharing_swarm": 1358,
                             "adaptive_central": 2000,
                             "single_agent": 900})
    out = tmp_path / "floor_r2.json"
    rc = _run_cli(r2, run_dir, out, capsys)
    assert rc == 0
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert text.endswith("\n")  # trailing newline
    rec = json.loads(text)

    assert rec["schema"] == "p08.token_floor_r2/1"
    assert rec["pin"] == PIN
    assert rec["harness_seed"] == SEED
    assert rec["case_id"] == "policy_rag_v1"
    assert "date" in rec and "T" in rec["date"]
    assert set(rec["arms"]) == {
        "S4_open_sharing_swarm", "S3_adaptive_central", "S0_single_agent"}
    assert rec["arms"]["S4_open_sharing_swarm"] == {
        "tokens": 1358, "wall_s": 1.0, "llm_calls": 1, "status": "completed"}
    assert rec["arms"]["S3_adaptive_central"]["tokens"] == 2000
    assert rec["arms"]["S0_single_agent"]["tokens"] == 900

    head = rec["headroom"]
    assert head["per_arm_ceiling"] == 60000
    assert head["master_ceiling"] == 10800000
    assert head["max_arm_usage_fraction"] == pytest.approx(2000 / 60000)
    assert head["verdict"] == "OK"


def test_over_60_percent_floor_verdict_check(r2: Any, tmp_path: Path,
                                             capsys: pytest.CaptureFixture[str]) -> None:
    run_dir = tmp_path / "run"
    # S4 at 40k = 66.7% of the 60k ceiling -> CHECK.
    _make_run_tree(run_dir, {"open_sharing_swarm": 40000,
                             "adaptive_central": 2000,
                             "single_agent": 900})
    out = tmp_path / "floor_r2.json"
    rc = _run_cli(r2, run_dir, out, capsys)
    assert rc == 0
    rec = json.loads(out.read_text(encoding="utf-8"))
    assert rec["headroom"]["verdict"] == "CHECK"
    assert rec["headroom"]["max_arm_usage_fraction"] == pytest.approx(40000 / 60000)


def test_zero_token_arm_hard_fails(r2: Any, tmp_path: Path,
                                   capsys: pytest.CaptureFixture[str]) -> None:
    run_dir = tmp_path / "run"
    _make_run_tree(run_dir, {"open_sharing_swarm": 1358,
                             "adaptive_central": 0,
                             "single_agent": 900})
    out = tmp_path / "floor_r2.json"
    rc = _run_cli(r2, run_dir, out, capsys)
    assert rc != 0
    assert not out.exists()
    err = capsys.readouterr().err
    assert "adaptive_central" in err and "total_tokens" in err


def test_missing_arm_hard_fails(r2: Any, tmp_path: Path,
                                capsys: pytest.CaptureFixture[str]) -> None:
    run_dir = tmp_path / "run"
    _make_run_tree(run_dir, {"open_sharing_swarm": 1358,
                             "adaptive_central": 2000,
                             "single_agent": 900})
    # Remove the S0 arm entirely.
    import shutil
    shutil.rmtree(run_dir / "single_agent")
    out = tmp_path / "floor_r2.json"
    rc = _run_cli(r2, run_dir, out, capsys)
    assert rc != 0
    assert not out.exists()
    assert "single_agent" in capsys.readouterr().err


def test_invalid_status_hard_fails(r2: Any, tmp_path: Path,
                                   capsys: pytest.CaptureFixture[str]) -> None:
    run_dir = tmp_path / "run"
    _make_run_tree(run_dir, {"open_sharing_swarm": 1358,
                             "adaptive_central": 2000,
                             "single_agent": 900},
                   status={"single_agent": "invalid_usage"})
    out = tmp_path / "floor_r2.json"
    rc = _run_cli(r2, run_dir, out, capsys)
    assert rc != 0
    assert not out.exists()
    assert "invalid_usage" in capsys.readouterr().err


def test_aborted_budget_status_accepted(r2: Any, tmp_path: Path,
                                        capsys: pytest.CaptureFixture[str]) -> None:
    run_dir = tmp_path / "run"
    # S0 may legitimately abort at the envelope (protocol stopping rule).
    _make_run_tree(run_dir, {"open_sharing_swarm": 1358,
                             "adaptive_central": 2000,
                             "single_agent": 60000},
                   status={"single_agent": "aborted_budget"})
    out = tmp_path / "floor_r2.json"
    rc = _run_cli(r2, run_dir, out, capsys)
    assert rc == 0
    rec = json.loads(out.read_text(encoding="utf-8"))
    assert rec["arms"]["S0_single_agent"]["status"] == "aborted_budget"
    # 60000/60000 = 1.0 > 0.60 -> CHECK.
    assert rec["headroom"]["verdict"] == "CHECK"
    assert rec["headroom"]["max_arm_usage_fraction"] == pytest.approx(1.0)
