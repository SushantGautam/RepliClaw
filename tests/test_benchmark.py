"""M6 benchmark (AC10/AC11/AC18): known-answer tasks, seeded faults, all
AC11 metrics computed from actual runs, no fabricated values."""
from pathlib import Path

from repliclaw.benchmark import (
    correctness_metrics,
    load_fixtures,
    recovery_metrics,
    run_benchmark,
)
from repliclaw.investigators import DeterministicInvestigator
from repliclaw.models import Claim
from repliclaw.strategies import run_strategy


def make_inv(cfg):
    return DeterministicInvestigator(cfg)


def test_at_least_three_seeded_fault_modes():
    fixtures = load_fixtures()
    faults = {fx.get("seeded_fault") for fx in fixtures if fx.get("seeded_fault")}
    assert len(faults) >= 3, faults
    # Known-answer: every fixture has an objective truth label.
    for fx in fixtures:
        assert fx["truth"] in ("supported", "refuted")


def test_benchmark_computes_all_ac11_metrics(tmp_path):
    rep = run_benchmark(tmp_path / "bench", make_inv)
    for strat in rep["strategies"]:
        m = rep["per_strategy"][strat]
        for section in ("correctness", "recovery", "diversity", "resources"):
            assert section in m, f"{strat} missing {section}"
        c = m["correctness"]
        for k in ("correctness", "false_accept_rate", "false_reject_rate", "inconclusive_rate"):
            assert 0.0 <= c[k] <= 1.0
    # Error correlation proxy is present.
    assert "pairwise_avg" in rep["error_correlation"]
    # All six tasks x five strategies produced rows.
    assert len(rep["rows"]) == rep["n_tasks"] * rep["n_strategies"]
    # Output artifacts exist.
    for f in ("benchmark_results.csv", "benchmark_report.json", "benchmark_report.md"):
        assert (tmp_path / "bench" / f).exists()


def test_benchmark_is_deterministic_across_reruns(tmp_path):
    """AC11/AC18: the harness is reproducible. Re-running into the same out dir
    must not change the measured columns (regression guard for the needs.jsonl
    append-accumulation bug that once inflated n_needs on dirty _work/)."""
    out = tmp_path / "bench"
    run_benchmark(out, make_inv)
    first = [
        (line.split(",")[:15])  # everything except trailing wall_clock_s
        for line in (out / "benchmark_results.csv").read_text(encoding="utf-8").splitlines()[1:]
        if line.strip()
    ]
    run_benchmark(out, make_inv)  # same out dir, second run
    second = [
        (line.split(",")[:15])
        for line in (out / "benchmark_results.csv").read_text(encoding="utf-8").splitlines()[1:]
        if line.strip()
    ]
    assert first == second, "benchmark columns changed across re-runs (needs/evidence accumulation)"
    # n_needs (col index 12) must never exceed 1 per repl_claw row.
    for row in second:
        if row[0] == "repl_claw":
            assert int(row[12]) <= 1, f"n_needs accumulated: {row}"


def test_no_fabricated_values_metrics_are_bounded(tmp_path):
    """AC18: reported metrics are derived, bounded, and internally consistent."""
    rep = run_benchmark(tmp_path / "bench", make_inv)
    for strat, m in rep["per_strategy"].items():
        c = m["correctness"]
        # Counts must be consistent with rates and n_tasks.
        assert c["n_correct"] + c["n_false_accept"] + c["n_false_reject"] + c["n_inconclusive"] == c["n_tasks"]
        # Rate is rounded to 4dp; allow that rounding.
        assert abs(c["correctness"] - c["n_correct"] / c["n_tasks"]) < 1e-4 + 1e-9
        assert abs(c["false_accept_rate"] - c["n_false_accept"] / c["n_tasks"]) < 1e-4 + 1e-9
        assert abs(c["false_reject_rate"] - c["n_false_reject"] / c["n_tasks"]) < 1e-4 + 1e-9


def test_repl_claw_recovers_all_faulted_tasks():
    """AC12: RepliClaw must recover every seeded-fault refuted task."""
    fixtures = load_fixtures()
    n_rec = 0
    n_faulted = 0
    for i, fx in enumerate(fixtures):
        c = fx["claim"]
        claim = Claim(claim_id=f"claim-{fx['id']}", statement=c["statement"],
                      domain=c.get("domain", "general"), data=c.get("data"),
                      reference_truth=c.get("reference_truth"), seeded_fault=c.get("seeded_fault"))
        if fx.get("seeded_fault") and fx["truth"] == "refuted":
            n_faulted += 1
            res = run_strategy("repl_claw", claim, make_inv, Path(f"/tmp/rc-rec-{i}"))
            assert res.verdict.label.value == "REFUTED", f"{fx['id']} not recovered"
            n_rec += 1
    assert n_faulted >= 3
    assert n_rec == n_faulted


def test_metric_helpers():
    rows = [
        {"label": "SUPPORTED", "truth": "supported"},
        {"label": "REFUTED", "truth": "supported"},   # false reject
        {"label": "SUPPORTED", "truth": "refuted"},   # false accept
        {"label": "INCONCLUSIVE", "truth": "refuted"},# abstain
    ]
    m = correctness_metrics(rows)
    assert m["n_false_accept"] == 1
    assert m["n_false_reject"] == 1
    assert m["n_inconclusive"] == 1
    assert m["n_correct"] == 1
    r = recovery_metrics([
        {"label": "REFUTED", "truth": "refuted", "seeded_fault": "leakage"},
        {"label": "SUPPORTED", "truth": "refuted", "seeded_fault": "leakage"},
    ])
    assert r["recovery_rate"] == 0.5
