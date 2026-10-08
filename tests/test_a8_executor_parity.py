"""A8 (RC-1) executor-parity tests — PREREG-2026-10 v1.2 amendment A8.

The science judge's NOT-APPROVE (round 1, items S7/S9, RC-1) found the P1
estimand (S5 vs S4) compared a live-LLM arm against a deterministic one — an
invalid like-for-like comparison. A8 makes ALL SIX primary arms run the SAME
live-LLM executor (S0/S3/S4 join S5/A1/A3 on the live path with an
``LLMInvestigator`` factory), adds honest agent accounting (RC-3), and a scorer
guard that refuses to emit a P1/RQ2 decision when a pair mixes executors
(A8.3.1). These tests pin that behavior:

* ``test_a8_all_six_primary_arms_are_live`` — the runner's live routing covers
  S0/S3/S4/S5/A1/A3 (``LIVE_KEYS`` contains all six arm keys).
* ``test_a8_p1_pair_same_executor_fake_clients`` — S5 and S4 (FakeLLMClient)
  on the same case/envelope record identical model / offline_arm=false /
  harness_seed / envelope_sha256.
* ``test_a8_scorer_refuses_mixed_executor_p1`` — a mixed-executor P1 pair
  yields the degraded ``executor_parity_violation`` and NO
  SUPPORTED/FALSIFIED/NOT_SUPPORTED decision (and, control: a matched pair
  proceeds to the normal branch).
* ``test_a8_agent_accounting_honest`` — a 4-distinct-agent S3 run records 4 in
  the BudgetRecord (not clamped to the declared 3), completes without a
  mid-run abort, and the parity report's declared-vs-observed classification
  flags an observed count that exceeds the cap.
* ``test_a8_fake_llmclient_parity_all_six_arms`` — all six arms complete on the
  fake client and are byte-identical (volatile keys stripped) across two runs
  — the §9 amendment gate item.

All runs use the in-process CLI (``main``) with the FakeLLMClient; no live LLM
API key, no network.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from repliclaw.comparators import runner
from repliclaw.comparators.arms import ArmSpec
from repliclaw.comparators.budget import BudgetEnvelope, BudgetLedger
from repliclaw.comparators.managers import AdaptiveCentralManager
from repliclaw.investigators import DeterministicInvestigator
from repliclaw.models import Claim
from repliclaw.p08 import score as sc

FIX = Path(__file__).resolve().parent / "fixtures"

# All six primary arms (CLI labels) — the A8 live set.
SIX_ARMS = ["S0", "S3", "S4", "S5", "A1", "A3"]
# Registry keys for the three newly-live strategy arms.
LIVE_STRATEGY_KEYS = ["single_agent", "adaptive_central", "open_sharing_swarm"]

# Volatile fields stripped before the deterministic-rerun comparison
# (mirrors test_p08_runner_cli.STRIP_KEYS).
STRIP_KEYS = {
    "start_ts",
    "end_ts",
    "wall_s",
    "ts",
    "published_at",
    "proposed_at",
    "committed_at",
    "created_at",
}


def _run_cli(
    arm: str,
    case: str,
    *extra: str,
    monkeypatch: pytest.MonkeyPatch,
    out: Path,
) -> int:
    monkeypatch.delenv("REPLICLAW_LLM_ALLOW_LIVE", raising=False)
    return runner.main(["--arm", arm, "--case", case, "--out", str(out), *extra])


def _strip(o: Any) -> Any:
    if isinstance(o, dict):
        return {k: _strip(v) for k, v in o.items() if k not in STRIP_KEYS}
    if isinstance(o, list):
        return [_strip(x) for x in o]
    return o


def _normalized_tree(root: Path) -> dict:
    """All JSON/JSONL artifacts under root, normalized for determinism diffs."""
    out: dict[str, Any] = {}
    for p in sorted(Path(root).rglob("*")):
        if not p.is_file() or p.suffix not in (".json", ".jsonl"):
            continue
        text = p.read_text(encoding="utf-8")
        if p.suffix == ".jsonl":
            content = [_strip(json.loads(line)) for line in text.splitlines() if line.strip()]
        else:
            content = _strip(json.loads(text))
        out[str(p.relative_to(root))] = content
    return out


def _load_claim(name: str) -> Claim:
    fx = json.loads((FIX / f"{name}.json").read_text(encoding="utf-8"))
    c = fx["claim"]
    return Claim(
        claim_id=f"claim-{name}",
        statement=c["statement"],
        domain=c.get("domain", "general"),
        data=c.get("data"),
        reference_truth=c.get("reference_truth"),
        seeded_fault=c.get("seeded_fault"),
    )


def _det_factory(cfg) -> DeterministicInvestigator:
    return DeterministicInvestigator(cfg)


# ---------------------------------------------------------------------------
# 1. All six primary arms route through the live path (A8 RC-1).
# ---------------------------------------------------------------------------
def test_a8_all_six_primary_arms_are_live() -> None:
    """LIVE_KEYS contains every primary arm key: S0/S3/S4/S5/A1/A3.

    Before A8 the three strategy arms (single_agent/adaptive_central/
    open_sharing_swarm) were OFFLINE (DeterministicInvestigator), making P1 a
    live-vs-deterministic comparison. A8 puts them on the live path.
    """
    live = set(runner.LIVE_KEYS)
    for cli, key in runner.ARM_ALIASES.items():
        if cli in SIX_ARMS:
            assert key in live, f"{cli} (key {key!r}) must be live after A8"
    # Explicit: the three newly-live strategy arms are present.
    assert set(LIVE_STRATEGY_KEYS) <= live
    # The six CLI labels all resolve to live keys.
    six_keys = {runner.ARM_ALIASES[c] for c in SIX_ARMS}
    assert six_keys <= live
    # The three newly-live arms are routed via the strategy path, not the
    # EESS-lifecycle registry.
    assert set(LIVE_STRATEGY_KEYS) <= set(runner._LIVE_STRATEGY_KEYS)


# ---------------------------------------------------------------------------
# 2. The P1 pair (S5 vs S4) records the SAME executor on the fake client.
# ---------------------------------------------------------------------------
def test_a8_p1_pair_same_executor_fake_clients(
    tmp_path: Path, monkeypatch
) -> None:
    """S5 and S4 (FakeLLMClient) on the same case/envelope are like-for-like.

    Both run_metadata.json must record offline_arm=false, the same model, the
    same harness_seed, and the same envelope_sha256 — the four fields that
    prove the P1 estimand is a like-for-like executor comparison.
    """
    out_s5 = tmp_path / "S5"
    out_s4 = tmp_path / "S4"
    assert _run_cli(
        "S5", "policy_rag", "--client-factory", "fake",
        monkeypatch=monkeypatch, out=out_s5,
    ) == 0
    assert _run_cli(
        "S4", "policy_rag", "--client-factory", "fake",
        monkeypatch=monkeypatch, out=out_s4,
    ) == 0

    m5 = json.loads((out_s5 / "run-01" / "run_metadata.json").read_text())
    m4 = json.loads((out_s4 / "run-01" / "run_metadata.json").read_text())

    # Both arms are LIVE (not deterministic).
    assert m5["offline_arm"] is False
    assert m4["offline_arm"] is False
    # Identical executor identity + harness seed + envelope.
    assert m5["model"] == m4["model"]
    assert m5["harness_seed"] == m4["harness_seed"] == 20261010
    assert m5["envelope_sha256"] == m4["envelope_sha256"]
    # The live model is the fake client's, never "deterministic".
    assert m5["model"] == "fake-v1"
    assert m4["model"] == "fake-v1"


# ---------------------------------------------------------------------------
# 3. The scorer refuses a mixed-executor P1 pair (A8.3.1 / RC-1 guard).
# ---------------------------------------------------------------------------
def _a8_run(
    root: Path,
    arm: str,
    run_id: str,
    *,
    model: str | None,
    offline_arm: bool | None,
    defect: str | None,
    target: str | None,
    tokens: int = 100,
    envelope: str = "e" * 64,
) -> None:
    """Write one schema-valid run dir with an A8 executor signature.

    Reuses the scorer's own contract schemas (final_verdict / budget_ledger /
    traces / run_metadata) so the completeness gate passes; ``model`` and
    ``offline_arm`` are the A8 executor-parity fields in run_metadata.
    """
    d = root / arm / run_id
    d.mkdir(parents=True, exist_ok=True)
    n = max(1, tokens // 50)
    calls = [
        {
            "seq": i + 1,
            "agent_id": "alpha",
            "prompt_tokens": tokens // 2,
            "completion_tokens": tokens - tokens // 2,
            "total_tokens": tokens // n,
            "wall_s": 0.1,
            "usage_present": True,
        }
        for i in range(n)
    ]
    fv = {
        "schema": "p08.final_verdict/1",
        "arm": arm,
        "case_id": "policy_rag_v1",
        "run_id": f"{arm}/{run_id}",
        "harness_seed": 20261010,
        "envelope_sha256": envelope,
        "n_agents": 3,
        "total_tokens": tokens,
        "wall_s": 0.0,
        "status": "completed",
        "verdict": "supported",
        "defect_class": defect,
        "target_artifact": target,
        "confidence": 0.5,
        "hypotheses": [],
        "counterfactual_slots_granted": 0,
        "counterfactual_slots_executed": 0,
        "integrity_rejections": 0,
        "agent_verdicts": [],
    }
    (d / "final_verdict.json").write_text(json.dumps(fv), encoding="utf-8")
    ledger = {
        "schema": "p08.budget_ledger/1",
        "envelope": {
            "max_tokens": 60000,
            "max_wall_s": 900.0,
            "max_agents": 3,
            "sha256": envelope,
        },
        "calls": calls,
        "totals": {
            "prompt_tokens": tokens // 2,
            "completion_tokens": tokens - tokens // 2,
            "total_tokens": tokens,
            "llm_calls": n,
            "wall_s": 0.1 * n,
        },
        "overflow_events": [],
    }
    (d / "budget_ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
    traces = [
        {"seq": 1, "ts": "2026-10-10T00:00:00Z", "agent_id": None,
         "type": "trace", "payload": {}},
        {"seq": 2, "ts": "2026-10-10T00:00:01Z", "agent_id": "alpha",
         "type": "verdict", "payload": {}},
    ]
    (d / "traces.jsonl").write_text(
        "\n".join(json.dumps(e) for e in traces) + "\n", encoding="utf-8"
    )
    meta = {
        "harness_seed": 20261010,
        "envelope_sha256": envelope,
        "tree_sha": "f" * 40,
    }
    if model is not None:
        meta["model"] = model
    if offline_arm is not None:
        meta["offline_arm"] = offline_arm
    (d / "run_metadata.json").write_text(json.dumps(meta), encoding="utf-8")


def test_a8_scorer_refuses_mixed_executor_p1(tmp_path: Path) -> None:
    """A mixed-executor P1 pair (S5 live vs S4 offline) yields a degraded
    ``executor_parity_violation`` with NO SUPPORTED/FALSIFIED/NOT_SUPPORTED
    decision (no ci95, no rule). A matched pair proceeds to the normal branch.
    """
    # --- mixed: S5 live-LLM, S4 offline/deterministic (A1.1's invalid P1) ---
    root = tmp_path / "mixed"
    for i in range(1, 4):
        # S5: correct diagnoses (M1 = 1.0), LIVE executor.
        _a8_run(root, "S5", f"run-{i:02d}", model="fake-v1", offline_arm=False,
                defect="retrieval_omission", target="returns-policy")
        # S4: offline/deterministic executor (M1 also 1.0 — irrelevant once the
        # guard fires, but otherwise-valid metrics).
        _a8_run(root, "S4", f"run-{i:02d}", model="deterministic", offline_arm=True,
                defect="retrieval_omission", target="returns-policy")
    res = sc.score_runs(root, "policy_rag_v1")
    p1 = res["p1_decision"]
    # Degraded shape, distinct reason.
    assert p1["decision"] == "executor_parity_violation"
    assert p1["decision"] not in (sc.P1_SUPPORTED, sc.P1_FALSIFIED, sc.P1_NOT_SUPPORTED)
    # The normal-branch outputs are ABSENT (follows the no_valid_runs pattern).
    assert "ci95" not in p1
    assert "rule" not in p1
    # The parity block surfaces the per-pair mismatch.
    assert res["parity"]["executor_parity"]["S5_S4"] is False
    assert res["parity"]["ok"] is False

    # --- control: the SAME arms but BOTH live (matched) -> proceeds to the
    # normal branch (guard is specific to a real executor mismatch). S5 all
    # correct (M1 1.0) vs S4 all wrong (M1 0.0) -> Δ = +1.0 -> SUPPORTED. ---
    root2 = tmp_path / "matched"
    for i in range(1, 4):
        _a8_run(root2, "S5", f"run-{i:02d}", model="fake-v1", offline_arm=False,
                defect="retrieval_omission", target="returns-policy")
        _a8_run(root2, "S4", f"run-{i:02d}", model="fake-v1", offline_arm=False,
                defect=None, target=None)
    res2 = sc.score_runs(root2, "policy_rag_v1")
    p1b = res2["p1_decision"]
    assert p1b["decision"] != "executor_parity_violation"
    assert p1b["decision"] == sc.decision_branch(tuple(p1b["ci95"]))
    assert res2["parity"]["executor_parity"]["S5_S4"] is True
    assert "rule" in p1b


# ---------------------------------------------------------------------------
# 4. Honest agent accounting (A8.3.4 / RC-3).
# ---------------------------------------------------------------------------
def test_a8_agent_accounting_honest(tmp_path: Path) -> None:
    """A 4-distinct-agent S3 run records 4 (not the declared 3), completes
    without a mid-run abort under the A7 4-agent envelope, and the parity
    report's declared-vs-observed classification flags an observed count that
    exceeds the cap.
    """
    # The A7 live envelope: 4 agents is the legal cap.
    env = BudgetEnvelope(max_tokens=60_000, max_wall_s=900.0, max_agents=4)
    claim = _load_claim("clean_refuted")  # disagreement -> S3 deploys a 4th agent
    ledger = BudgetLedger(env)
    spec = ArmSpec(arm_name="adaptive_central", claim_id=claim.claim_id, envelope=env)
    arm = AdaptiveCentralManager(_det_factory)

    # No mid-run abort: the run completes and the ledger records the TRUE
    # observed count (4), not a clamp to the declared self.n_agents (3).
    res = arm.run(claim, ledger, spec, tmp_path / "s3")
    assert res.verdict_label != "ABORTED"
    assert res.n_agents == 4  # observed distinct investigator count
    assert ledger.n_agents == 4
    rec = ledger.records()[0]
    assert rec.n_agents == 4, "BudgetRecord must record the true observed count"

    # Under the A7 4-agent envelope the 4th agent is LEGAL (not over budget):
    # the parity report faithfully reflects the honest count and stays valid.
    report = runner.assert_budget_parity([res], env)
    assert res.arm_name not in report["over_budget_arms"]
    assert report["parity"] is True
    assert report["n_arms"] == 1

    # Declared-vs-observed PARITY classification: an arm whose OBSERVED count
    # exceeds the envelope cap IS flagged (the rule res.n_agents > max_agents).
    over = runner.ArmResult(
        arm_name="synthetic_over",
        claim_id=claim.claim_id,
        verdict_label="INCONCLUSIVE",
        n_agents=5,  # observed 5 distinct agents > cap 4
        total_tokens=10,
        total_wall_s=0.1,
        envelope_sha256=env.sha256(),
        detail={},
    )
    report2 = runner.assert_budget_parity([over], env)
    assert "synthetic_over" in report2["over_budget_arms"]
    assert report2["parity"] is False


# ---------------------------------------------------------------------------
# 5. The §9 gate item: all six arms, fake client, byte-identical across runs.
# ---------------------------------------------------------------------------
def test_a8_fake_llmclient_parity_all_six_arms(tmp_path: Path, monkeypatch) -> None:
    """All six primary arms complete on the FakeLLMClient (same case/envelope/
    seed) and produce deterministic, identical run-01 payloads across two
    runs (volatile keys stripped). This is the §9 amendment gate item: it
    proves the P1 pair (and RQ2 comparators) are like-for-like and reproducible.
    """
    for i, arm in enumerate(SIX_ARMS):
        r1 = tmp_path / arm / "r1"
        r2 = tmp_path / arm / "r2"
        c1 = _run_cli(
            arm, "policy_rag", "--client-factory", "fake",
            monkeypatch=monkeypatch, out=r1,
        )
        c2 = _run_cli(
            arm, "policy_rag", "--client-factory", "fake",
            monkeypatch=monkeypatch, out=r2,
        )
        assert c1 == 0, f"{arm} run 1 must complete"
        assert c2 == 0, f"{arm} run 2 must complete"

        t1 = _normalized_tree(r1 / "run-01")
        t2 = _normalized_tree(r2 / "run-01")
        assert set(t1) == set(t2), f"{arm}: file set differs across runs"
        diffs = {k for k in t1 if t1[k] != t2[k]}
        assert not diffs, f"{arm}: non-deterministic artifacts: {sorted(diffs)}"

        # Every arm records the live (fake) executor, and the P1-relevant
        # identity fields are identical for the two members of each pair.
        meta1 = t1["run_metadata.json"]
        assert meta1["offline_arm"] is False
        assert meta1["model"] == "fake-v1"
        assert meta1["harness_seed"] == 20261010

    # Cross-arm: all six share ONE envelope sha256 (matched-budget precondition)
    # and the P1 pair members (S5, S4) + RQ2 comparators (S3, S0) all match.
    metas = {}
    for arm in SIX_ARMS:
        r1 = tmp_path / arm / "r1"
        metas[arm] = json.loads((r1 / "run-01" / "run_metadata.json").read_text())
    hashes = {m["envelope_sha256"] for m in metas.values()}
    assert len(hashes) == 1, f"arms did not share one envelope hash: {hashes}"
    for other in ("S3", "S0"):
        assert metas["S5"]["model"] == metas[other]["model"]
        assert metas["S5"]["offline_arm"] == metas[other]["offline_arm"] is False
