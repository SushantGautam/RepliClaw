"""P08 scorer tests — exact-number assertions + the oracle-gate safety property.

The load-bearing test (science judge 2026-10-08, BLOCKER 1 / Q12):
``test_incomplete_dir_oracle_never_read`` proves the oracle is opened only
AFTER the completeness gate passes.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from repliclaw import p08
from repliclaw.p08 import score as sc

ENV = {"max_tokens": 60000, "max_wall_s": 900.0, "max_agents": 3, "sha256": "e" * 64}
ENV_SHA = "e" * 64


def _fv(run_id: str, *, status: str = "completed", defect: str | None = None,
        target: str | None = None, verdict: str = "supported", tokens: int = 0,
        hyps: list[dict[str, Any]] | None = None, slots_granted: int = 0,
        slots_executed: int = 0, integrity: int = 0,
        envelope: str = ENV_SHA) -> dict[str, Any]:
    return {
        "schema": "p08.final_verdict/1",
        "arm": run_id.split("/")[0],
        "case_id": "policy_rag_v1",
        "run_id": run_id,
        "harness_seed": 20261010,
        "envelope_sha256": envelope,
        "n_agents": 3,
        "total_tokens": tokens,
        "wall_s": 0.0,
        "status": status,
        "verdict": verdict,
        "defect_class": defect,
        "target_artifact": target,
        "confidence": 0.5,
        "hypotheses": hyps or [],
        "counterfactual_slots_granted": slots_granted,
        "counterfactual_slots_executed": slots_executed,
        "integrity_rejections": integrity,
        "agent_verdicts": [],
    }


def _ledger(calls: list[dict[str, Any]], tokens: int) -> dict[str, Any]:
    return {
        "schema": "p08.budget_ledger/1",
        "envelope": ENV,
        "calls": calls,
        "totals": {
            "prompt_tokens": tokens // 2,
            "completion_tokens": tokens - tokens // 2,
            "total_tokens": tokens,
            "llm_calls": len(calls),
            "wall_s": 0.1 * len(calls),
        },
        "overflow_events": [],
    }


def _call(seq: int, tokens: int) -> dict[str, Any]:
    return {
        "seq": seq, "agent_id": "alpha", "prompt_tokens": tokens // 2,
        "completion_tokens": tokens - tokens // 2, "total_tokens": tokens,
        "wall_s": 0.1, "usage_present": True,
    }


def _write_run(root: Path, arm: str, run: str, *, status: str = "completed",
               defect: str | None = None, target: str | None = None,
               verdict: str = "supported", tokens: int = 100,
               hyps: list[dict[str, Any]] | None = None,
               slots_granted: int = 0, slots_executed: int = 0,
               integrity: int = 0, envelope: str = ENV_SHA,
               meta_envelope: str | None = None,
               cf_files: dict[str, dict[str, Any]] | None = None,
               omit: set[str] | None = None,
               usage_present: bool = True) -> Path:
    d = root / arm / run
    d.mkdir(parents=True, exist_ok=True)
    omit = omit or set()
    n = max(1, tokens // 50)
    calls = [_call(i + 1, tokens // n) for i in range(n)]
    if not usage_present:
        for c in calls:
            c["usage_present"] = False
    if "final_verdict.json" not in omit:
        (d / "final_verdict.json").write_text(json.dumps(_fv(
            f"{arm}/{run}", status=status, defect=defect, target=target,
            verdict=verdict, tokens=tokens, hyps=hyps, slots_granted=slots_granted,
            slots_executed=slots_executed, integrity=integrity, envelope=envelope)))
    if "budget_ledger.json" not in omit:
        (d / "budget_ledger.json").write_text(json.dumps(_ledger(calls, tokens)))
    if "traces.jsonl" not in omit:
        lines = [
            {"seq": 1, "ts": "2026-10-10T00:00:00Z", "agent_id": None,
             "type": "trace", "payload": {}},
            {"seq": 2, "ts": "2026-10-10T00:00:01Z", "agent_id": "alpha",
             "type": "verdict", "payload": {}},
        ]
        (d / "traces.jsonl").write_text("\n".join(json.dumps(ev) for ev in lines) + "\n")
    if "run_metadata.json" not in omit:
        (d / "run_metadata.json").write_text(json.dumps({
            "harness_seed": 20261010,
            "envelope_sha256": (meta_envelope or ENV_SHA),
            "tree_sha": "f" * 40,
        }))
    if cf_files:
        cfd = d / "counterfactuals"
        cfd.mkdir(exist_ok=True)
        for name, body in cf_files.items():
            (cfd / f"{name}.json").write_text(json.dumps(body))
    return d


def _hyps(*ids: str, attempted: bool = True, falsifiable: bool = True,
          outcome: str = "refuted") -> list[dict[str, Any]]:
    return [
        {"id": i, "statement": f"hyp {i}", "falsifiable": falsifiable,
         "attempted_falsification": attempted, "outcome": outcome,
         "counterfactual_slot": None}
        for i in ids
    ]


# ---------------------------------------------------------------------------
# 1. Exact M values on a synthetic run tree
# ---------------------------------------------------------------------------
def test_exact_metric_values(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    # S5: 3 runs. M1 = [1, 1, 0]; tokens 100/200/300; wall 1.0/2.0/4.0.
    _write_run(root, "S5", "run-01", defect="retrieval_omission", target="returns-policy",
               tokens=100, hyps=_hyps("H_R", "H_P"), slots_granted=1, slots_executed=1,
               cf_files={"I_R": {"verdict_changed": True, "hypothesis_falsified": False}})
    _write_run(root, "S5", "run-02", defect="retrieval_omission", target="returns-policy",
               tokens=200, hyps=_hyps("H_R", "H_P"))
    _write_run(root, "S5", "run-03", defect="policy_conflict", target="returns-policy",
               tokens=300, hyps=_hyps("H_R", "H_P", "H_J"))
    # S3: 3 runs, none correct.
    for i in (1, 2, 3):
        _write_run(root, "S3", f"run-0{i}", defect=None, target=None,
                   tokens=150, hyps=_hyps("H_R", "H_P"))
    # S0: 1 run, correct, no slots.
    _write_run(root, "S0", "run-01", defect="retrieval_omission", target="returns-policy",
               tokens=90, hyps=[])

    res = sc.score_runs(root, "policy_rag_v1")
    a = res["arms"]

    # M1 exact per-arm means.
    assert a["S5"]["M1"]["value"] == pytest.approx(2 / 3)
    assert a["S3"]["M1"]["value"] == pytest.approx(0.0)
    assert a["S0"]["M1"]["value"] == pytest.approx(1.0)
    # CI bounds are consistent: 0 <= ci <= 1 and lo <= hi.
    lo, hi = a["S5"]["M1"]["ci95"]
    assert 0.0 <= lo <= hi <= 1.0

    # M2 exact (per-run then per-arm mean).
    assert a["S5"]["M2"]["value"] == pytest.approx((1.0 + 1.0 + 1.0) / 3)
    assert a["S3"]["M2"]["value"] == pytest.approx(1.0)
    assert a["S0"]["M2"]["value"] is None  # no hypotheses registered

    # M3: S5 run-01 -> 1/1 = 1.0; run-02/03 granted 0 slots -> n/a (excluded).
    assert a["S5"]["M3"]["value"] == pytest.approx(1.0)
    assert a["S3"]["M3"]["value"] is None  # no slots by design

    # M11: only H_P is unsupported by the oracle. run-01/02 falsified H_P (refuted)
    # -> 1/2 each; run-03 falsified H_P and H_J -> 1/3. Mean = (1/2 + 1/2 + 1/3)/3.
    assert a["S5"]["M11"]["value"] == pytest.approx((0.5 + 0.5 + 1 / 3) / 3)

    # M5 / M6 / M9 / M8 / M7 / M10.
    assert a["S5"]["M5"]["mean"] == pytest.approx(200.0)
    assert a["S5"]["M5"]["min"] == pytest.approx(100.0)
    assert a["S5"]["M5"]["max"] == pytest.approx(300.0)
    assert a["S5"]["M6"]["value"] == pytest.approx(150.0)  # mean tokens over M1==1 runs
    assert a["S5"]["M6"]["n_correct"] == 2
    assert a["S3"]["M6"]["value"] is None
    # wall_s comes from the ledger totals (0.1 per call; calls = tokens//50).
    # S5: run-01 2 calls -> 0.2, run-02 4 -> 0.4, run-03 6 -> 0.6 (float noise).
    assert a["S5"]["M9"]["median"] == pytest.approx(0.4)
    assert a["S5"]["M9"]["iqr"][0] == pytest.approx(0.2)
    assert a["S5"]["M9"]["iqr"][1] == pytest.approx(0.6)
    assert a["S5"]["M8"]["mean"] == pytest.approx(0.0)
    assert a["S5"]["M7"]["value"] == pytest.approx(0.0)
    assert a["S5"]["M7"]["flag_S1"] is False
    assert a["S5"]["M10"]["value"] == pytest.approx(1.0)
    assert a["S5"]["M10"]["modal_verdict"] == "supported"

    # M4: no leakage.
    assert a["S5"]["M4"]["total_incidents"] == 0.0
    assert a["S5"]["M4"]["flag_S5"] is False

    # Parity: identical envelope, no overruns.
    assert res["parity"]["ok"] is True
    assert res["parity"]["identical_envelope_sha256"] is True

    # P1 difference CI exists (3 vs 3 runs) and is within [-1, 1].
    lo_d, hi_d = res["p1_decision"]["ci95"]
    assert -1.0 <= lo_d <= hi_d <= 1.0
    assert res["p1_decision"]["s5_m1_mean"] == pytest.approx(2 / 3)
    assert res["p1_decision"]["s3_m1_mean"] == pytest.approx(0.0)

    # Outputs exist.
    out = root / "scores"
    for name in ("scores.json", "per_run.csv", "scorecard.md", "run_manifest.json"):
        assert (out / name).exists(), name
    manifest = json.loads((out / "run_manifest.json").read_text())
    assert manifest["arms"]["S5"][0]["usage_present_ratio"] == 1.0
    scorecard = (out / "scorecard.md").read_text()
    assert "counterevidence-first" in scorecard


# ---------------------------------------------------------------------------
# 2. The safety property: incomplete tree => NO oracle read
# ---------------------------------------------------------------------------
def test_incomplete_dir_oracle_never_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "runs"
    _write_run(root, "S5", "run-01", defect="retrieval_omission", target="returns-policy")
    _write_run(root, "S3", "run-01", omit={"budget_ledger.json"})  # gap

    calls: list[str] = []

    def spy(*_a: Any, **_k: Any) -> dict[str, Any]:
        calls.append("oracle")
        return {}

    monkeypatch.setattr(sc, "load_oracle", spy)

    with pytest.raises(sc.ScoreError, match="incomplete"):
        sc.score_runs(root, "policy_rag_v1")

    assert calls == [], "oracle was read despite an incomplete run tree"
    manifest_path = root / "scores" / "run_manifest_incomplete.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text())
    assert manifest["oracle_read"] is False
    assert any("budget_ledger.json" in g for g in manifest["gaps"])
    # No scored outputs were written.
    assert not (root / "scores" / "scores.json").exists()


# ---------------------------------------------------------------------------
# 3. Bootstrap determinism (same seed -> identical CI across two invocations)
# ---------------------------------------------------------------------------
def test_bootstrap_determinism(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    for i in range(1, 7):
        defect = "retrieval_omission" if i % 2 else "policy_conflict"
        _write_run(root, "S5", f"run-{i:02d}", defect=defect, target="returns-policy",
                   tokens=100 + i)

    r1 = sc.score_runs(root, "policy_rag_v1")
    ci1 = r1["arms"]["S5"]["M1"]["ci95"]
    # Second full invocation, fresh process state, same seed.
    r2 = sc.score_runs(root, "policy_rag_v1")
    ci2 = r2["arms"]["S5"]["M1"]["ci95"]
    assert ci1 == ci2 == [ci1[0], ci1[1]]
    # Different seed -> (with 6 heterogeneous values) a different CI is expected;
    # we only require the mechanism is seed-sensitive.
    r3 = sc.score_runs(root, "policy_rag_v1", seed=20261020)
    assert r3["arms"]["S5"]["M1"]["ci95"] is not None


# ---------------------------------------------------------------------------
# 4. Envelope mismatch -> violation flag + parity broken
# ---------------------------------------------------------------------------
def test_envelope_mismatch_flag(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    # S5 run carries a DIFFERENT final-verdict envelope sha (cross-arm parity
    # broken) AND a mismatched run_metadata sha (per-run flag).
    _write_run(root, "S5", "run-01", defect="retrieval_omission", target="returns-policy",
               envelope="f" * 64, meta_envelope="e" * 64)
    _write_run(root, "S3", "run-01")

    res = sc.score_runs(root, "policy_rag_v1")
    assert res["parity"]["identical_envelope_sha256"] is False
    assert res["parity"]["ok"] is False
    csv_text = (root / "scores" / "per_run.csv").read_text()
    s5_line = next(row for row in csv_text.splitlines() if row.startswith("S5,"))
    assert s5_line.endswith("envelope_mismatch")


# ---------------------------------------------------------------------------
# 5. P02 replay self-test (judge checklist item 1)
# ---------------------------------------------------------------------------
def test_p02_replay_self_test_passes() -> None:
    res = sc.p02_replay_self_test()
    assert res["error"] is None, res["error"]
    assert res["case"] == "policy_rag_v1"
    assert res["replay_ok"] is True
    assert res["determinism_ok"] is True


# ---------------------------------------------------------------------------
# 6. invalid_usage runs are voided: excluded from primary metrics, reported
# ---------------------------------------------------------------------------
def test_invalid_usage_voided(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    _write_run(root, "S5", "run-01", defect="retrieval_omission", target="returns-policy",
               tokens=100)
    _write_run(root, "S5", "run-02", status="invalid_usage",
               defect="retrieval_omission", target="returns-policy", tokens=100)
    # aborted_budget also counted in M7.
    _write_run(root, "S5", "run-03", status="aborted_budget", tokens=60_001)

    res = sc.score_runs(root, "policy_rag_v1")
    a = res["arms"]["S5"]
    assert a["n_runs"] == 3
    assert a["n_valid"] == 1
    assert a["n_invalid_usage"] == 1
    assert a["n_aborted_budget"] == 1
    assert a["voided_runs"] == ["S5/run-02"]
    assert a["aborted_runs"] == ["S5/run-03"]
    # M1 pool = only the valid run -> degenerate CI [1.0, 1.0].
    assert a["M1"]["value"] == pytest.approx(1.0)
    assert a["M1"]["ci95"] == [1.0, 1.0]
    # M7 = 1/3 (aborted only), not >25%? 1/3 > 0.25 -> S1 flag TRUE.
    assert a["M7"]["value"] == pytest.approx(1 / 3)
    assert a["M7"]["flag_S1"] is True
    assert res["stopping_rules"]["S1"]["triggered"] is True
    # Overrun: run-03 tokens 60001 > 60000.
    assert "S5/run-03" in res["parity"]["overruns"]
    manifest = json.loads((root / "scores" / "run_manifest.json").read_text())
    assert manifest["arms"]["S5"][1]["status"] == "invalid_usage"


# ---------------------------------------------------------------------------
# 7. usage-present gate: <0.99 usage_present -> incomplete, oracle not read
# ---------------------------------------------------------------------------
def test_usage_below_threshold_is_incomplete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "runs"
    _write_run(root, "S5", "run-01", defect="retrieval_omission", target="returns-policy",
               usage_present=False)

    calls: list[str] = []
    monkeypatch.setattr(sc, "load_oracle", lambda *a, **k: calls.append("x") or {})

    with pytest.raises(sc.ScoreError, match="usage_present"):
        sc.score_runs(root, "policy_rag_v1")
    assert calls == []


def test_package_exports() -> None:
    assert callable(p08.score_runs)
    assert issubclass(p08.ScoreError, Exception)
