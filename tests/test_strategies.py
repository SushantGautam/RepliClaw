"""AC09: all five coordination baselines run under one shared task interface
and produce comparable results. Also asserts the headline differentiator
(RepliClaw recovers misleading evidence; strong-single-agent baselines do not)."""
import json
from pathlib import Path

from repliclaw.investigators import DeterministicInvestigator
from repliclaw.models import Claim
from repliclaw.strategies import STRATEGY_RUNNERS, run_strategy

FIX = Path(__file__).resolve().parent / "fixtures"


def load_claim(name):
    fx = json.loads((FIX / f"{name}.json").read_text())
    c = fx["claim"]
    return Claim(claim_id=f"claim-{name}", statement=c["statement"],
                 domain=c.get("domain", "general"), data=c.get("data"),
                 reference_truth=c.get("reference_truth"),
                 seeded_fault=c.get("seeded_fault")), fx["truth"]


def make_inv(cfg):
    return DeterministicInvestigator(cfg)


def test_all_five_baselines_registered():
    assert set(STRATEGY_RUNNERS) == {
        "single_agent", "fixed_dag", "isolated_vote", "open_debate", "repl_claw",
    }


def test_each_baseline_runs_and_returns_common_schema(tmp_path):
    claim, truth = load_claim("clean_supported")
    for strat in STRATEGY_RUNNERS:
        res = run_strategy(strat, claim, make_inv, tmp_path / strat)
        d = res.to_dict()
        # Common comparable schema.
        for key in ("strategy", "claim_id", "verdict", "n_evidence",
                    "n_agents", "usage", "wall_clock_s"):
            assert key in d, f"{strat} missing {key}"
        assert d["strategy"] == strat
        assert d["verdict"]["label"] in ("SUPPORTED", "REFUTED", "INCONCLUSIVE")
        assert d["n_evidence"] >= 1
        assert res.errors == []


def test_unknown_strategy_rejected(tmp_path):
    claim, _ = load_claim("clean_supported")
    import pytest
    with pytest.raises(ValueError):
        run_strategy("not_a_strategy", claim, make_inv, tmp_path)


def test_baselines_match_on_clean_supported(tmp_path):
    """On the easy supported case every strategy should call it SUPPORTED."""
    claim, _ = load_claim("clean_supported")
    for strat in STRATEGY_RUNNERS:
        res = run_strategy(strat, claim, make_inv, tmp_path / strat)
        assert res.verdict.label.value == "SUPPORTED", strat


def test_repl_claw_recovers_misleading_but_strong_singles_false_accept(tmp_path):
    """Headline differentiator (AC12): on the misleading fixture, single-agent
    and fixed-DAG baselines are fooled (false accept -> SUPPORTED), while
    RepliClaw's blind commit/reveal + falsifier follow-up recovers to REFUTED.
    This is the evidence that the decentralized behavior is not equivalent to
    a fixed DAG (AC17)."""
    claim, truth = load_claim("misleading_wrong_test")
    assert truth == "refuted"
    # Strong-single baselines false-accept.
    for strat in ("single_agent", "fixed_dag"):
        res = run_strategy(strat, claim, make_inv, tmp_path / strat)
        assert res.verdict.label.value == "SUPPORTED", f"{strat} should be fooled"
    # RepliClaw recovers.
    res = run_strategy("repl_claw", claim, make_inv, tmp_path / "repl")
    assert res.verdict.label.value == "REFUTED"


def test_usage_and_latency_logged_for_every_strategy(tmp_path):
    """AC11: comparable resource usage must be logged for every baseline."""
    claim, _ = load_claim("clean_supported")
    for strat in STRATEGY_RUNNERS:
        res = run_strategy(strat, claim, make_inv, tmp_path / strat)
        assert res.usage is not None
        assert res.wall_clock_s >= 0.0
        assert res.usage.to_dict()  # serializable
