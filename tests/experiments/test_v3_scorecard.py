"""Self-check for the V3 comparative scorecard on the synthetic fixture.

No LLM calls: the fixture under ``fixtures/scorecard_fixture/`` is static
JSON mimicking the real artifact layouts (telemetry pilot ``status.json``
runs and P08 ``final_verdict.json`` runs). Proves the metrics compute and
that observational vs executable-counterfactual rows stay separated.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from repliclaw.experiments.v3 import scorecard as sc  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "scorecard_fixture"


def _scorecard() -> dict:
    truth = sc.load_truth(FIXTURE / "truth.json")
    dirs = sc.discover_run_dirs([FIXTURE])
    assert len(dirs) == 6, f"expected 6 run dirs, found {len(dirs)}"
    runs = [r for r in (sc.parse_run_dir(d, truth) for d in dirs) if r]
    return sc.build_scorecard(runs)


def test_classes_are_disjoint_and_merge_is_refused():
    card = _scorecard()
    assert set(card["evidence_classes"]) == {sc.CLASS_OBS, sc.CLASS_EXEC}
    assert card["merged_aggregate"] is None
    assert "REFUSED" in card["refusal"].upper() or "never merged" in card["refusal"]
    obs = card["evidence_classes"][sc.CLASS_OBS]
    exc = card["evidence_classes"][sc.CLASS_EXEC]
    with pytest.raises(sc.ScorecardRefusalError):
        sc.merge_class_summaries(obs, exc)
    # every run of one class stays inside that class's aggregate
    assert obs["runs"] == 4
    assert exc["runs"] == 2


def test_observational_metrics():
    card = _scorecard()
    obs = card["evidence_classes"][sc.CLASS_OBS]["arms"]

    de = obs["D-E-TELEM"]
    assert de["runs"] == 2 and de["completions"] == 2
    assert de["identification"]["scored_runs"] == 2
    assert de["identification"]["top1_hits"] == 1
    assert de["identification"]["top1_rate"] == 0.5
    # ranked-5 submission can never equal a 1-element GT set
    assert de["identification"]["exact_set_matches"] == 0
    # jaccards: case1 = 1/5, case2 = 2/5 -> mean 0.3
    assert de["identification"]["mean_jaccard"] == pytest.approx(0.3)
    # consensus on both runs, one of them wrong -> false consensus 1/2
    fc = de["false_consensus"]
    assert fc["consensus_runs"] == 2
    assert fc["false_consensus_runs"] == 1
    assert fc["false_consensus_rate"] == 0.5
    # interventions are N/A for observational runs
    assert de["verified_interventions"]["na"] is True
    assert de["verified_interventions"]["reason"].startswith("observational")
    # cost: 1000 + 1200 tokens; 1 correct completion at 1000 tokens
    assert de["cost"]["total_tokens"] == 2200
    assert de["cost"]["tokens_per_correct_completion"] == 1000.0
    assert de["premature_stops"]["count"] == 0
    assert de["failures"] == {
        "non_completion": 0, "budget_exhaustion": 0,
        "crashes": 0, "protocol_violations": 0,
    }

    ceq = obs["C-EQ-TELEM"]
    assert ceq["completions"] == 0
    assert ceq["premature_stops"]["count"] == 2
    assert ceq["premature_stops"]["reasons"] == {"aborted_budget": 1, "crashed": 1}
    assert ceq["failures"]["non_completion"] == 2
    assert ceq["failures"]["budget_exhaustion"] == 1
    assert ceq["failures"]["crashes"] == 1
    assert ceq["failures"]["protocol_violations"] == 1
    # non-completions must never vanish from the aggregate
    assert ceq["runs"] == 2
    assert ceq["identification"]["top1_rate"] is None  # nothing scored


def test_executable_metrics():
    card = _scorecard()
    exc = card["evidence_classes"][sc.CLASS_EXEC]["arms"]

    ceq = exc["C-EQ"]
    assert ceq["identification"]["top1_rate"] == 1.0
    assert ceq["identification"]["exact_set_matches"] == 1
    assert ceq["identification"]["mean_jaccard"] == 1.0
    iv = ceq["verified_interventions"]
    assert iv["na"] is False
    assert iv["executed"] == 1 and iv["verified"] == 1
    assert iv["verified_fraction"] == 1.0 and iv["flipped"] == 1
    assert ceq["false_consensus"]["false_consensus_runs"] == 0
    assert ceq["cost"]["total_tokens"] == 2500

    de = exc["D-E"]
    assert de["identification"]["top1_rate"] == 0.0
    assert de["identification"]["mean_jaccard"] == 0.0
    assert de["verified_interventions"]["verified_fraction"] == 0.0
    # two agents agreed, final target wrong -> false consensus
    assert de["false_consensus"]["false_consensus_runs"] == 1


def test_case_level_pairs_within_class():
    card = _scorecard()
    obs_pairs = card["evidence_classes"][sc.CLASS_OBS]["case_pairs"]
    # one row per (case, arm, seed); case ids only, arms per class
    arms = {p["arm"] for p in obs_pairs}
    assert arms == {"D-E-TELEM", "C-EQ-TELEM"}
    by_case = {p["case"] for p in obs_pairs}
    assert by_case == {"fx-case-1", "fx-case-2"}
    exec_pairs = card["evidence_classes"][sc.CLASS_EXEC]["case_pairs"]
    assert {p["arm"] for p in exec_pairs} == {"C-EQ", "D-E"}


def test_score_json_truth_fallback_without_truth_file():
    d = FIXTURE / "obs" / "round1" / "fx-case-1" / "seed0" / "D-E-TELEM"
    rec = sc.parse_run_dir(d, truth=None)
    assert rec is not None
    assert rec.truth_source == "score.json"
    assert rec.gt_set == frozenset({"cartservice"})
    assert rec.top1_hit is True


def test_generic_fallback_run_json(tmp_path: Path):
    run_dir = tmp_path / "compound_case" / "X-A" / "run-01"
    run_dir.mkdir(parents=True)
    (run_dir / "run.json").write_text(json.dumps({
        "arm": "X-A",
        "case_id": "cx-1",
        "evidence_class": "executable_counterfactual",
        "status": "completed",
        "submitted_ranking": ["cartservice", "currencyservice"],
        "cause_set": ["cartservice", "currencyservice"],
        "tokens_total": 500,
        "llm_calls": 7,
        "wall_s": 10.0,
        "escrowed": True,
        "agent_top1s": [],
        "agent_verdicts": ["supported", "supported"],
        "intervention_stats": {"claimed": 2, "executed": 2, "verified": 1, "flipped": 1},
    }), encoding="utf-8")
    rec = sc.parse_run_dir(run_dir, truth=None)
    assert rec is not None and rec.evidence_class == sc.CLASS_EXEC
    # exact cause-set match: {cartservice, currencyservice} == GT
    assert rec.exact_set_match is True
    assert rec.top1_hit is True
    assert rec.interventions["verified_fraction"] == 0.5

    with pytest.raises(ValueError):
        bad = json.loads((run_dir / "run.json").read_text())
        bad["evidence_class"] = "causal"
        (run_dir / "run.json").write_text(json.dumps(bad), encoding="utf-8")
        sc.parse_run_dir(run_dir, truth=None)


def test_markdown_keeps_classes_separate():
    card = _scorecard()
    md = sc.render_markdown(card)
    assert "## observational" in md
    assert "## executable_counterfactual" in md
    assert "REFUSED" in md
    # no aggregate row spans both classes: each arm name appears only once
    # per its own section (both sections render their own header row only)
    assert md.count("claim_strength") == 0  # not leaked into the table
    assert "| D-E-TELEM |" in md and "| C-EQ |" in md
    obs_block = md.split("## executable_counterfactual")[0]
    assert "| C-EQ |" not in obs_block  # executable arm never in obs section


def test_cli(tmp_path: Path):
    out_json = tmp_path / "scorecard.json"
    out_md = tmp_path / "scorecard.md"
    rc = sc.main([str(FIXTURE),
                  "--truth", str(FIXTURE / "truth.json"),
                  "--json", str(out_json), "--md", str(out_md)])
    assert rc == 0
    card = json.loads(out_json.read_text())
    assert card["schema"] == sc.SCHEMA
    assert card["total_runs"] == 6
    assert out_md.read_text().startswith("# Arm-vs-arm scorecard")
