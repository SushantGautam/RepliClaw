"""AC02 / AC13 / AC16: cross-team verify() interface + CLI, reproducible
outputs under artifacts/."""
import json
from pathlib import Path

import pytest

from repliclaw import Claim, verify
from repliclaw.cli import build_parser, main

SUPPORTED_DATA = {
    "n": 400, "mean_treat": 6.0, "mean_ctrl": 5.0, "sd_treat": 1.0,
    "sd_ctrl": 1.0, "alpha": 0.05, "baseline_rr": 1.5,
    "events_treat": 300, "events_ctrl": 200, "tot_treat": 1000, "tot_ctrl": 1000,
}
MISLEADING_DATA = dict(SUPPORTED_DATA, events_treat=200)


def test_verify_from_plain_string(tmp_path):
    # A bare claim with no bundled data has nothing to compute on -> the
    # deterministic lenses abstain (INCONCLUSIVE), never a fabricated verdict.
    rep = verify("Treatment increases the event rate by ~50% (published RR=1.5) versus control.",
                 config={"backend": "deterministic", "run_root": str(tmp_path)})
    assert rep.verdict_label == "INCONCLUSIVE"
    assert rep.n_independent >= 3
    # Provenance-linked report written.
    assert Path(rep.report_path).exists()
    assert "RepliClaw Verification Report" in Path(rep.report_path).read_text()


def test_verify_from_dict_with_data_recovers_misleading(tmp_path):
    rep = verify(
        {"statement": "RR=1.5 vs control", "data": MISLEADING_DATA,
         "reference_truth": "refuted", "seeded_fault": "wrong_stat_test"},
        config={"backend": "deterministic", "run_root": str(tmp_path)},
    )
    assert rep.verdict_label == "REFUTED"
    assert rep.n_needs >= 1
    assert any(n["kind"] == "falsification" for n in rep.needs)
    d = rep.to_dict()
    assert d["verdict"] == "REFUTED" and 0.0 <= d["confidence"] <= 1.0


def test_verify_from_claim_object(tmp_path):
    claim = Claim(statement="RR=1.5 vs control", data=SUPPORTED_DATA)
    rep = verify(claim, config={"backend": "deterministic", "run_root": str(tmp_path)})
    assert rep.verdict_label == "SUPPORTED"
    assert rep.claim_id == claim.claim_id


def test_verify_isolated_runs_do_not_leak(tmp_path):
    a = verify("RR=1.5", config={"backend": "deterministic", "run_root": str(tmp_path)})
    b = verify("RR=1.5", config={"backend": "deterministic", "run_root": str(tmp_path)})
    assert a.run_dir != b.run_dir


def test_verify_artifacts_bundled(tmp_path):
    rep = verify(
        {"statement": "RR=1.5 vs control", "data": SUPPORTED_DATA},
        artifacts=[{"ref": "paper:1234", "rr": 1.5}],
        config={"backend": "deterministic", "run_root": str(tmp_path)},
    )
    assert rep.verdict_label == "SUPPORTED"


def test_verify_artifact_with_data_block(tmp_path):
    """A cross-team artifact that bundles a raw `data` block must be merged
    into the claim so the analytical lenses can actually compute on it (this
    is how `repliclaw verify --artifact file.json` feeds data)."""
    # Claim has NO top-level data; everything arrives via the artifact.
    rep = verify(
        {"statement": "Treatment increases the event rate by 50% (RR=1.5) vs control"},
        artifacts=[{"type": "raw_counts", "data": MISLEADING_DATA}],
        config={"backend": "deterministic", "run_root": str(tmp_path)},
    )
    # MISLEADING_DATA has raw RR=1.0 while the claim asserts RR=1.5 → the
    # falsifier refutes → a conflict the follow-up adjudicates → REFUTED.
    assert rep.verdict_label == "REFUTED"
    assert rep.n_evidence >= 3


def test_cli_verify(tmp_path, capsys):
    code = main([
        "verify",
        "--claim", "RR=1.5 vs control",
        "--data", json.dumps(SUPPORTED_DATA),
        "--backend", "deterministic",
        "--out", str(tmp_path),
    ])
    out = capsys.readouterr().out
    assert code == 0
    assert "VERDICT: SUPPORTED" in out
    assert "REPORT:" in out and "verify_report.md" in out


def test_cli_verify_json(tmp_path, capsys):
    code = main([
        "verify",
        "--claim", "RR=1.5 vs control",
        "--data", json.dumps(MISLEADING_DATA),
        "--backend", "deterministic",
        "--out", str(tmp_path),
        "--json",
    ])
    out = capsys.readouterr().out
    assert code == 0
    parsed = json.loads(out)
    assert parsed["verdict"] == "REFUTED"


def test_cli_benchmark(tmp_path, capsys):
    code = main(["benchmark", "--out", str(tmp_path), "--backend", "deterministic"])
    out = capsys.readouterr().out
    assert code == 0
    bench = tmp_path / "benchmark"
    assert (bench / "benchmark_report.md").exists()
    assert (bench / "benchmark_results.csv").exists()
    assert (bench / "benchmark_report.json").exists()
    assert "repl_claw" in out


def test_cli_unknown_backend_fails_cleanly(tmp_path):
    import pytest
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["verify", "--claim", "x", "--backend", "bogus"])


def test_llm_factory_wraps_config_not_client(monkeypatch, tmp_path):
    """_llm_factory must receive an LLMConfig (not a client) and each
    investigator gets a fresh client with a real LLMConfig — guards against
    the LLMClient(LLMClient) double-wrap that silently degraded LLM runs."""
    from repliclaw.investigators import LLMClient, LLMConfig, LLMInvestigator
    from repliclaw.models import InvestigatorConfig, InvestigatorRole
    from repliclaw.verify import make_investigator_factory

    monkeypatch.setenv("CUSTOM_SIMULACHAT_KEY", "test-key")
    factory = make_investigator_factory("llm")
    inv = factory(InvestigatorConfig(agent_id="x", role=InvestigatorRole.ANALYST))
    assert isinstance(inv, LLMInvestigator)
    assert isinstance(inv.client.cfg, LLMConfig)
    assert inv.client.cfg.api_key == "test-key"
    with pytest.raises(TypeError):
        LLMClient(inv.client)
