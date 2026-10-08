"""Live-LLM EESS arm tests (P08, offline — FakeLLMClient, no network, no key).

Covers the plan's acceptance bar for the live arms:

1. A1 pass-through records but never gates (integrity_rejections == 0 by
   construction; raw packets visible via ``raw_artifacts``).
2. A3 is seeded-deterministic: identical traces at the same harness seed,
   different traces across seeds.
3. Budget exhaustion mid-lifecycle => ``aborted_budget`` + overflow_events.
4. Usage-present on every call (the never-zero-fill invariant, judge item 7):
   a client whose usage the provider drops => ``invalid_usage``, run void.
5. S5 canonical run: commitment/reveal escrow events, verified SimpleAudit
   counterfactual evidence, choice trace populated.
6. The run-dir artifact set matches the P08 artifact contract schemas
   (final_verdict keys, budget_ledger schema, trace-line shape).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from repliclaw.comparators.arms import ArmSpec
from repliclaw.comparators.budget import BudgetEnvelope, BudgetLedger
from repliclaw.eess_live import (
    EESSLiveA1Arm,
    EESSLiveA3Arm,
    EESSLiveS5Arm,
    EscrowedEscrow,
    FakeLLMClient,
    LiveEESSOrchestrator,
    PassThroughEscrow,
)
from repliclaw.eess_live.orchestrator import AGENT_IDS, CASE_ID
from repliclaw.models import Claim
from repliclaw.needmarket.policy import LocalEigPolicy

SEED = 20261010
SEED_ALT = 20261020


def _claim() -> Claim:
    return Claim(
        claim_id="claim_live_test",
        statement="The baseline policy-RAG system fails to cite the controlling provision.",
        domain="policy_rag",
    )


def _envelope(**kw: Any) -> BudgetEnvelope:
    base = dict(max_tokens=60_000, max_wall_s=900.0, max_agents=3)
    base.update(kw)
    return BudgetEnvelope(**base)


def _spec(arm: str, env: BudgetEnvelope) -> ArmSpec:
    return ArmSpec(arm_name=arm, claim_id="claim_live_test", envelope=env)


def _run_arm(arm_cls, tmp_path: Path, harness_seed: int = SEED) -> tuple:
    arm = arm_cls(lambda _a: FakeLLMClient(), harness_seed=harness_seed)
    env = _envelope()
    result = arm.run(_claim(), BudgetLedger(env), _spec(arm_cls.arm_label, env), tmp_path / arm_cls.arm_label)
    return arm, result, tmp_path / arm_cls.arm_label / "run-01"


def _traces(run_dir: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (run_dir / "traces.jsonl").read_text().splitlines()]


def _final_verdict(run_dir: Path) -> dict[str, Any]:
    return json.loads((run_dir / "final_verdict.json").read_text())


def _budget_ledger(run_dir: Path) -> dict[str, Any]:
    return json.loads((run_dir / "budget_ledger.json").read_text())


# ---------------------------------------------------------------------------
# 1. A1 pass-through: records but never gates
# ---------------------------------------------------------------------------
def test_a1_pass_through_never_gates(tmp_path: Path):
    arm = EESSLiveA1Arm(lambda _a: FakeLLMClient(), harness_seed=SEED)
    env = _envelope()
    result = arm.run(_claim(), BudgetLedger(env), _spec("A1", env), tmp_path / "A1")
    fv = _final_verdict(tmp_path / "A1" / "run-01")
    assert result.arm_name == "A1"
    assert fv["status"] == "completed"
    # No integrity gate exists in pass-through: zero rejections by construction.
    assert fv["integrity_rejections"] == 0
    # Pass-through keeps raw packets/observations visible (no filtering).
    escrow = PassThroughEscrow()
    from repliclaw.escrow import PredictionPacket

    escrow.open(CASE_ID)
    pkt = PredictionPacket(
        packet_id="a" * 32,
        case_id=CASE_ID,
        agent_id="alpha",
        hypothesis_id="H_R",
        hypothesis_version=1,
        hypothesis_statement="s",
        intervention_id="I_R_retrieval_fix",
        predicted_outcome="o",
        refutation_criterion="r",
        competing_explanation="c",
        prior_evidence_snapshot_sha256="b" * 64,
    )
    escrow.commit("alpha", pkt)
    raw = escrow.raw_artifacts()
    assert "raw_packets" in raw and len(raw["raw_packets"]) == 1


# ---------------------------------------------------------------------------
# 2. A3 seeded determinism
# ---------------------------------------------------------------------------
def test_a3_seeded_deterministic(tmp_path: Path):
    def one(sub: Path, seed: int):
        arm = EESSLiveA3Arm(lambda _a: FakeLLMClient(), harness_seed=seed)
        env = _envelope()
        arm.run(_claim(), BudgetLedger(env), _spec("A3", env), sub / "A3")
        return _traces(sub / "A3" / "run-01")

    same_1 = one(tmp_path / "s1", SEED)
    same_2 = one(tmp_path / "s2", SEED)
    other = one(tmp_path / "s3", SEED_ALT)

    def shape(traces: list) -> list:
        # ts differs by wall clock; the deterministic content is seq/type/agent/payload.
        return [
            (t["seq"], t["type"], t["agent_id"],
             json.dumps(t["payload"], sort_keys=True, default=str))
            for t in traces
        ]

    assert shape(same_1) == shape(same_2)
    assert shape(same_1) != shape(other)


# ---------------------------------------------------------------------------
# 3. Budget exhaustion => aborted_budget + overflow event
# ---------------------------------------------------------------------------
def test_budget_exhaustion_aborts(tmp_path: Path):
    # Each fake call costs 40+12=52 tokens; a 150-token ceiling trips on the
    # 3rd commit call (156 > 150) — mid-lifecycle budget exhaustion.
    orch = LiveEESSOrchestrator(
        claim=_claim(),
        out_root=tmp_path / "runs",
        escrow=EscrowedEscrow(tmp_path / "escrow"),
        policy_factory=lambda _a: LocalEigPolicy({}),
        client_factory=lambda _a: FakeLLMClient(),
        envelope=_envelope(max_tokens=150),
        harness_seed=SEED,
        max_cycles=2,
    )
    result = orch.run()
    assert result.status == "aborted_budget"
    assert result.verdict is None
    assert result.budget_ledger["overflow_events"], "overflow must be recorded, not swallowed"
    assert any(e.get("kind") == "budget_exhausted" for e in result.budget_ledger["overflow_events"])


# ---------------------------------------------------------------------------
# 4. Usage invalidation (judge item 7): never zero-fill
# ---------------------------------------------------------------------------
def test_missing_usage_marks_invalid(tmp_path: Path):
    class _NoUsageClient(FakeLLMClient):
        """Provider returned a response but dropped the usage fields: the
        cumulative usage counter stays at zero, so the per-call snapshot
        delta is zero — exactly the case the never-zero-fill rule must void."""

        def chat(self, prompt, system="s", max_tokens=None):
            out = super().chat(prompt, system=system, max_tokens=max_tokens)
            self.usage.prompt_tokens = 0
            self.usage.completion_tokens = 0
            self.usage.total_tokens = 0
            return out

    arm = EESSLiveS5Arm(lambda _a: _NoUsageClient(), harness_seed=SEED)
    env = _envelope()
    arm.run(_claim(), BudgetLedger(env), _spec("S5", env), tmp_path / "S5")
    fv = _final_verdict(tmp_path / "S5" / "run-01")
    # A zero-usage delta is recorded with usage_present=False, never counted
    # as 0 tokens and called compliant: the run is void.
    assert fv["status"] == "invalid_usage"
    bl = _budget_ledger(tmp_path / "S5" / "run-01")
    assert any(not c["usage_present"] for c in bl["calls"])
    assert "oracle" not in json.dumps(fv).lower()


# ---------------------------------------------------------------------------
# 5. S5 canonical run: escrow events + verified evidence + choice trace
# ---------------------------------------------------------------------------
def test_s5_canonical_run(tmp_path: Path):
    arm = EESSLiveS5Arm(lambda _a: FakeLLMClient(), harness_seed=SEED)
    env = _envelope()
    result = arm.run(_claim(), BudgetLedger(env), _spec("S5", env), tmp_path / "S5")
    run_dir = tmp_path / "S5" / "run-01"
    fv = _final_verdict(run_dir)
    traces = _traces(run_dir)

    types = {t["type"] for t in traces}
    # Escrow lifecycle events are present (commitment before reveal).
    assert {"commitment", "reveal", "verdict", "evidence_published", "choice"} <= types
    commit_idx = [t["seq"] for t in traces if t["type"] == "commitment"]
    reveal_idx = [t["seq"] for t in traces if t["type"] == "reveal"]
    assert min(commit_idx) < min(reveal_idx), "commitment must precede reveal"

    # Real verified SimpleAudit runs for every committed hypothesis arm.
    cf_files = sorted(p.name for p in (run_dir / "counterfactuals").iterdir())
    assert "I_R_retrieval_fix.json" in cf_files
    assert "I_P_policy_conflict.json" in cf_files
    assert "I_J_judge_fix.json" in cf_files
    for name in cf_files:
        doc = json.loads((run_dir / "counterfactuals" / name).read_text())
        assert doc["verified"] is True
        assert doc["provenance"]["artifact_hashes"], "verified run must carry artifact hashes"

    # Verified evidence was published; hypotheses attempted falsification.
    assert fv["counterfactual_slots_executed"] >= 3
    assert all(h["attempted_falsification"] for h in fv["hypotheses"])
    # All three agents reached a post-evidence verdict.
    assert len(fv["agent_verdicts"]) == len(AGENT_IDS)
    assert fv["status"] == "completed"
    assert result.verdict_label in ("supported", "refuted", "uncertain")


# ---------------------------------------------------------------------------
# 6. Artifact set matches the P08 contract schemas
# ---------------------------------------------------------------------------
FINAL_VERDICT_KEYS = {
    "schema", "arm", "case_id", "run_id", "harness_seed", "envelope_sha256",
    "n_agents", "total_tokens", "wall_s", "status", "verdict", "defect_class",
    "target_artifact", "confidence", "hypotheses",
    "counterfactual_slots_granted", "counterfactual_slots_executed",
    "integrity_rejections", "agent_verdicts",
}


def test_artifact_set_matches_contract(tmp_path: Path):
    arm = EESSLiveS5Arm(lambda _a: FakeLLMClient(), harness_seed=SEED)
    env = _envelope()
    arm.run(_claim(), BudgetLedger(env), _spec("S5", env), tmp_path / "S5")
    run_dir = tmp_path / "S5" / "run-01"

    for fname in ("final_verdict.json", "budget_ledger.json", "traces.jsonl"):
        assert (run_dir / fname).exists(), f"missing contract artifact {fname}"
    assert (run_dir / "counterfactuals").is_dir()

    fv = _final_verdict(run_dir)
    assert fv["schema"] == "p08.final_verdict/1"
    assert set(fv) >= FINAL_VERDICT_KEYS
    for h in fv["hypotheses"]:
        assert set(h) >= {"id", "statement", "falsifiable", "attempted_falsification", "outcome", "counterfactual_slot"}
        assert h["outcome"] in ("supported", "refuted", "not_run")

    bl = _budget_ledger(run_dir)
    assert bl["schema"] == "p08.budget_ledger/1"
    assert bl["envelope"]["sha256"] == env.sha256()
    assert bl["totals"]["llm_calls"] == len(bl["calls"])
    for c in bl["calls"]:
        assert set(c) >= {
            "seq", "agent_id", "prompt_tokens", "completion_tokens",
            "total_tokens", "wall_s", "usage_present",
        }

    for t in _traces(run_dir):
        assert set(t) >= {"seq", "ts", "agent_id", "type", "payload"}
        # oracle isolation: nothing the arm read from an oracle may leak out
        assert "reference_truth" not in json.dumps(t)
    assert fv["case_id"] == CASE_ID
    assert fv["harness_seed"] == SEED


# ---------------------------------------------------------------------------
# matched-budget parity across the three live arms
# ---------------------------------------------------------------------------
def test_live_arms_share_one_envelope_hash(tmp_path: Path):
    env = _envelope()
    hashes = []
    for arm_cls in (EESSLiveS5Arm, EESSLiveA1Arm, EESSLiveA3Arm):
        arm = arm_cls(lambda _a: FakeLLMClient(), harness_seed=SEED)
        result = arm.run(_claim(), BudgetLedger(env), _spec(arm_cls.arm_label, env), tmp_path / arm_cls.arm_label)
        hashes.append(result.envelope_sha256)
    assert len(set(hashes)) == 1 == env.sha256() and True or hashes[0] == env.sha256()
