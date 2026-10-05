"""Offline tests for scripts/campaign.py (P08 live-window launch harness).

Covers the contract the live campaign relies on:
  1. the two-key live gate is honoured at campaign level (refusal, no run);
  2. the full 6-arm x N-run offline pipeline produces the scorer layout
     (<out>/<S-label>/run-NNN/{final_verdict,budget_ledger,traces,
     run_metadata}) and scores with identical envelope sha across arms;
  3. resume reuses completed run dirs (no re-launch);
  4. the 10.8M master token ceiling (default 10,800,000; configurable)
     stops further launches and exits 4, without scoring;
  5. a run refused at campaign level is never scored.

All tests use --client-factory fake (zero LLM, no live gate, deterministic).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "campaign.py"


def load_campaign():
    spec = importlib.util.spec_from_file_location("p08_campaign", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["p08_campaign"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def campaign():
    return load_campaign()


def run(campaign: Any, out: Path, **kw: Any) -> int:
    kw.setdefault("verbose", False)
    kw.setdefault("client_factory", "fake")
    return campaign.run_campaign(out_root=out, **kw)


def _arm_dirs(out: Path) -> list[str]:
    non_arms = {"staging", "scores"}
    return sorted(
        p.name for p in out.iterdir()
        if p.is_dir() and p.name not in non_arms
    )


def test_live_refusal_without_two_key(campaign: Any, tmp_path: Path,
                                       monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "c"
    monkeypatch.delenv("REPLICLAW_LLM_ALLOW_LIVE", raising=False)
    rc = run(campaign, out, client_factory="live", runs_per_arm=1, arms=["S5"])
    assert rc == campaign.EXIT_LIVE_REFUSAL
    assert not (out / "S5").exists(), "no run dir may be created on refusal"
    assert not (out / "scores").exists()


def test_full_offline_pipeline_produces_scorable_layout(
    campaign: Any, tmp_path: Path
) -> None:
    out = tmp_path / "c"
    rc = run(campaign, out, runs_per_arm=1)
    assert rc == 0
    assert _arm_dirs(out) == ["A1", "A3", "S0", "S3", "S4", "S5"]
    for label in _arm_dirs(out):
        run_dir = out / label / "run-001"
        for f in ("final_verdict.json", "budget_ledger.json",
                  "traces.jsonl", "run_metadata.json"):
            assert (run_dir / f).is_file(), f"{label}/run-001 missing {f}"
        assert not (run_dir / "run-01").exists(), "staging dir must be flattened"
    manifest = json.loads((out / "campaign_manifest.json").read_text())
    assert manifest["arms"] == {
        "S0": "single_agent", "S3": "adaptive_central",
        "S4": "open_sharing_swarm", "S5": "eess",
        "A1": "eess_no_escrow", "A3": "eess_random_select",
    }
    # scorer produced the full scorecard and every arm's envelope sha matches
    scores = out / "scores" / "scores.json"
    assert scores.is_file()
    scorecard = json.loads(scores.read_text())
    assert set(scorecard["parity"]["executor_parity"]) >= {"S5_S4", "S5_S3"}
    assert scorecard["parity"]["ok"] is True
    # no staging residue
    assert not (out / "staging").exists()


def test_resume_reuses_completed_runs(campaign: Any, tmp_path: Path) -> None:
    out = tmp_path / "c"
    assert run(campaign, out, runs_per_arm=2, arms=["S4"]) == 0
    before = {(out / "S4" / "run-001" / "final_verdict.json").read_text()}
    assert before, "run must exist after first pass"
    rc = run(campaign, out, runs_per_arm=2, arms=["S4"])
    assert rc == 0
    # the reused run-001 file is byte-identical (no re-launch), run-002 exists
    assert {(out / "S4" / "run-001" / "final_verdict.json").read_text()} == before
    assert (out / "S4" / "run-002" / "final_verdict.json").is_file()
    summary = json.loads((out / "campaign_summary.json").read_text())
    assert summary["total_runs"] == 2
    assert summary["missing_or_skipped"] == 0


def test_master_ceiling_stops_campaign(campaign: Any, tmp_path: Path) -> None:
    out = tmp_path / "c"
    # The ceiling check is `cumulative + 60k envelope > ceiling`, so
    # 60,300 lets exactly three fake runs launch (S0 x2 @ ~52 tok, S3/run-001
    # @ ~208 tok = 312 used) and then the FOURTH launch (312 + 60,000 =
    # 60,312 > 60,300) must be SKIPPED, not launched (code-judge B1: the
    # flagged run itself is skipped per prereg v1.1 §5.1).
    rc = run(campaign, out, runs_per_arm=2,
             master_token_ceiling=60_300, score=False)
    assert rc == campaign.EXIT_MASTER_CEILING
    summary = json.loads((out / "campaign_summary.json").read_text())
    assert summary["stopped_master_ceiling"] is True
    assert summary["completed_or_recorded"] == 3, \
        "exactly the 3 pre-ceiling runs may launch; the flagged run is skipped"
    assert summary["missing_or_skipped"] == 9
    assert not (out / "scores").exists(), "a ceiling-stopped campaign is not scored"
    manifest = json.loads((out / "campaign_manifest.json").read_text())
    s3 = manifest["runs"]["S3"]
    assert s3[0]["status"] in ("completed", "aborted_budget"), \
        "S3/run-001 launches before the ceiling trips"
    assert s3[1]["status"] == "skipped_master_ceiling", \
        "S3/run-002 is the run the check tripped on — it must be skipped"
    skipped = [
        e for runs in manifest["runs"].values() for e in runs
        if e["status"] == "skipped_master_ceiling"
    ]
    assert len(skipped) == 9, "all post-ceiling runs (incl. the flagged one) skipped"


def test_refused_run_is_never_scored(campaign: Any, tmp_path: Path,
                                     monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "c"
    monkeypatch.delenv("REPLICLAW_LLM_ALLOW_LIVE", raising=False)
    rc = campaign.run_campaign(
        out_root=out, case="policy_rag", case_id="policy_rag_v1",
        client_factory="live", runs_per_arm=1, arms=["S5"],
        verbose=False,
    )
    assert rc == campaign.EXIT_LIVE_REFUSAL
    assert not (out / "scores").exists()


def test_rerun_after_partial_flatten_recovers(campaign: Any, tmp_path: Path,
                                              monkeypatch: pytest.MonkeyPatch) -> None:
    """M1: crash mid-flatten leaves run_dir with a NON-EMPTY dir child
    (e.g. the RunStore at run-001/run/); the documented recovery is a
    plain re-run of the same command, which used to raise OSError
    (ENOTEMPTY) from os.replace over the directory child."""
    out = tmp_path / "c"
    run(campaign, out, runs_per_arm=1)
    run_dir = out / "S3" / "run-001"
    # Simulate a crash AFTER the inner run/ subdir was moved but BEFORE
    # final_verdict.json: remove the completion marker, leave the dir child.
    (run_dir / "final_verdict.json").unlink()
    assert (run_dir / "run").is_dir() and any((run_dir / "run").iterdir()), \
        "fixture: the partial-flatten state must contain a non-empty dir child"
    # Documented recovery: re-run the exact same command.
    rc = run(campaign, out, runs_per_arm=1)
    assert rc == 0
    assert (run_dir / "final_verdict.json").is_file()
    assert (run_dir / "budget_ledger.json").is_file()
    assert not (run_dir / "run-01").exists()


def test_unexpected_runner_exception_records_and_continues(
    campaign: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """m2: one run raising must not kill the remaining runs; it is
    recorded as error:<ExcName>, scoring is withheld, exit code 5."""
    out = tmp_path / "c"

    def _boom(_ns: Any) -> int:
        raise RuntimeError("boom (test)")

    monkeypatch.setattr(campaign._runner, "run_one_arm", _boom)
    rc = run(campaign, out, runs_per_arm=1, arms=["S3", "S0"], score=False)
    assert rc == campaign.EXIT_RUN_ERROR
    manifest = json.loads((out / "campaign_manifest.json").read_text())
    assert manifest["runs"]["S3"][0]["status"] == "error:RuntimeError"
    assert manifest["runs"]["S0"][0]["status"] == "error:RuntimeError", \
        "the campaign must have CONTINUED past the first erroring run"
    summary = json.loads((out / "campaign_summary.json").read_text())
    assert summary["errored"] == 2
    assert not (out / "scores").exists(), "errored runs are never scored"
