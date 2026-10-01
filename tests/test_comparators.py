"""P05 — matched-budget comparator baselines against the EESS swarm.

Red-first: these tests are written from the P05 acceptance criteria
(matched-budget parity + the three named arms) BEFORE the implementation in
``src/repliclaw/comparators/`` exists.

The comparison is only valid at MATCHED budgets: every arm must consume the
same declared token/time budget envelope. The tests below pin that property
and the behavior of each named comparator arm.

Arms (per IMPLEMENTATION_PLAN P05 "fair strong comparators"):
  * S0  single_agent         — one strong agent, no peers, no aggregation.
  * S3  adaptive_central     — a STRONG adaptive central manager that may
                               adapt its plan as evidence arrives (the
                               "strong equal-concurrency" comparator).
  * S4  open_sharing_swarm   — N agents sharing context, each seeing prior
                               agents' revealed conclusions (correlated by
                               construction).

All evidence is deterministic and offline (DeterministicInvestigator / a
deterministic stub). No live LLM, no network, no API keys.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from repliclaw.comparators import (
    AdaptiveCentralManager,
    ArmResult,
    ArmSpec,
    BudgetEnvelope,
    BudgetLedger,
    BudgetOverflow,
    ComparatorHarness,
    OpenSharingSwarm,
    SingleAgentBaseline,
    arm_registry,
    assert_budget_parity,
)
from repliclaw.comparators.budget import BudgetRecord
from repliclaw.investigators import DeterministicInvestigator
from repliclaw.models import Claim, InvestigatorConfig

FIX = Path(__file__).resolve().parent / "fixtures"


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------
def load_claim(name: str) -> tuple[Claim, str]:
    fx = json.loads((FIX / f"{name}.json").read_text())
    c = fx["claim"]
    claim = Claim(
        claim_id=f"claim-{name}",
        statement=c["statement"],
        domain=c.get("domain", "general"),
        data=c.get("data"),
        reference_truth=c.get("reference_truth"),
        seeded_fault=c.get("seeded_fault"),
    )
    return claim, fx["truth"]


def det_factory(cfg: InvestigatorConfig) -> DeterministicInvestigator:
    return DeterministicInvestigator(cfg)


def make_envelope(tokens: int = 10_000, wall_s: float = 30.0, agents: int = 3) -> BudgetEnvelope:
    return BudgetEnvelope(max_tokens=tokens, max_wall_s=wall_s, max_agents=agents)


# ---------------------------------------------------------------------------
# 1. Budget envelope + ledger (the parity mechanism)
# ---------------------------------------------------------------------------
def test_budget_envelope_is_frozen():
    """The declared envelope is an immutable contract: arms cannot mutate it."""
    env = make_envelope()
    with pytest.raises(Exception):
        env.max_tokens = 1  # type: ignore[misc]


def test_ledger_enforces_token_cap():
    env = make_envelope(tokens=100)
    ledger = BudgetLedger(env)
    ledger.record(BudgetRecord(agent_id="a", tokens=60, wall_s=1.0))
    # 60 + 50 = 110 > 100 -> overflow.
    with pytest.raises(BudgetOverflow):
        ledger.record(BudgetRecord(agent_id="b", tokens=50, wall_s=1.0))


def test_ledger_enforces_agent_cap():
    env = make_envelope(agents=2)
    ledger = BudgetLedger(env)
    # One arm deploying 2 agents fits; a second arm deploying 2 more would
    # push the total to 4 > 2.
    ledger.record(BudgetRecord(agent_id="a", tokens=1, wall_s=0.1, n_agents=2))
    with pytest.raises(BudgetOverflow):
        ledger.record(BudgetRecord(agent_id="b", tokens=1, wall_s=0.1, n_agents=2))


def test_ledger_enforces_wall_cap():
    env = make_envelope(wall_s=10.0)
    ledger = BudgetLedger(env)
    ledger.record(BudgetRecord(agent_id="a", tokens=1, wall_s=6.0))
    with pytest.raises(BudgetOverflow):
        ledger.record(BudgetRecord(agent_id="b", tokens=1, wall_s=6.0))


def test_ledger_within_budget_ok():
    env = make_envelope(tokens=100, wall_s=10.0, agents=3)
    ledger = BudgetLedger(env)
    ledger.record(BudgetRecord(agent_id="a", tokens=40, wall_s=2.0))
    ledger.record(BudgetRecord(agent_id="b", tokens=40, wall_s=2.0))
    assert ledger.total_tokens == 80
    assert ledger.total_wall_s == 4.0
    assert ledger.n_agents == 2
    assert not ledger.exhausted


# ---------------------------------------------------------------------------
# 2. The three named arms exist and are registered
# ---------------------------------------------------------------------------
def test_arm_registry_contains_the_three_named_arms():
    reg = arm_registry()
    assert {"single_agent", "adaptive_central", "open_sharing_swarm"} <= set(reg)


def test_arm_registry_builds_each_arm():
    reg = arm_registry()
    for name in ("single_agent", "adaptive_central", "open_sharing_swarm"):
        arm = reg[name](det_factory)
        assert arm.name() in reg


def test_single_agent_is_the_S0_baseline():
    arm = SingleAgentBaseline(det_factory)
    assert arm.name() == "single_agent"


def test_adaptive_central_is_the_S3_strong_manager():
    arm = AdaptiveCentralManager(det_factory)
    assert arm.name() == "adaptive_central"


def test_open_sharing_is_the_S4_swarm():
    arm = OpenSharingSwarm(det_factory, n_agents=3)
    assert arm.name() == "open_sharing_swarm"


# ---------------------------------------------------------------------------
# 3. Each arm runs under a shared envelope and reports a comparable ArmResult
# ---------------------------------------------------------------------------
def _run_arm(name: str, claim: Claim, tmp_path: Path) -> ArmResult:
    arm = arm_registry()[name](det_factory)
    env = make_envelope()
    ledger = BudgetLedger(env)
    spec = ArmSpec(arm_name=name, claim_id=claim.claim_id, envelope=env)
    res = arm.run(claim, ledger, spec, tmp_path / name)
    assert isinstance(res, ArmResult)
    return res


def test_each_arm_returns_common_schema(tmp_path):
    claim, _ = load_claim("clean_supported")
    for name in ("single_agent", "adaptive_central", "open_sharing_swarm"):
        res = _run_arm(name, claim, tmp_path)
        assert res.arm_name == name
        assert res.claim_id == claim.claim_id
        assert res.verdict_label in ("SUPPORTED", "REFUTED", "INCONCLUSIVE")
        assert res.n_agents >= 1
        assert res.total_tokens >= 0
        assert res.total_wall_s >= 0.0
        assert res.envelope_sha256  # non-empty content hash of the envelope


def test_arms_agree_on_clean_supported(tmp_path):
    """On the easy supported case every arm should call it SUPPORTED."""
    claim, _ = load_claim("clean_supported")
    for name in ("single_agent", "adaptive_central", "open_sharing_swarm"):
        res = _run_arm(name, claim, tmp_path)
        assert res.verdict_label == "SUPPORTED", name


# ---------------------------------------------------------------------------
# 4. MATCHED-BUDGET PARITY — the headline property
# ---------------------------------------------------------------------------
def test_all_arms_consume_the_same_envelope(tmp_path):
    """Every arm must be given the SAME declared envelope (identical content
    hash) — the comparison is only valid at matched budgets."""
    claim, _ = load_claim("clean_supported")
    env = make_envelope()
    hashes = set()
    for name in ("single_agent", "adaptive_central", "open_sharing_swarm"):
        arm = arm_registry()[name](det_factory)
        ledger = BudgetLedger(env)
        spec = ArmSpec(arm_name=name, claim_id=claim.claim_id, envelope=env)
        res = arm.run(claim, ledger, spec, tmp_path / name)
        hashes.add(res.envelope_sha256)
    assert len(hashes) == 1, f"arms consumed different envelopes: {hashes}"


def test_parity_report_is_true_for_matched_arms(tmp_path):
    """assert_budget_parity must PASS when all arms share one envelope and
    stay within it."""
    claim, _ = load_claim("clean_supported")
    env = make_envelope()
    results = []
    for name in ("single_agent", "adaptive_central", "open_sharing_swarm"):
        arm = arm_registry()[name](det_factory)
        ledger = BudgetLedger(env)
        spec = ArmSpec(arm_name=name, claim_id=claim.claim_id, envelope=env)
        results.append(arm.run(claim, ledger, spec, tmp_path / name))
    report = assert_budget_parity(results, env)
    assert report["parity"] is True
    assert report["n_arms"] == 3
    assert report["envelope_sha256"] == env.sha256()


def test_parity_fails_when_envelopes_differ():
    """If two arms were (incorrectly) given different envelopes, parity must
    be reported as FALSE (the comparison is invalid)."""
    env_a = make_envelope(tokens=1000)
    env_b = make_envelope(tokens=2000)
    ra = _mk_result("single_agent", env_a)
    rb = _mk_result("open_sharing_swarm", env_b)
    report = assert_budget_parity([ra, rb], env_a)
    assert report["parity"] is False
    assert report["envelope_sha256"] in (env_a.sha256(), env_b.sha256())


def test_parity_fails_when_an_arm_exceeds_budget(tmp_path):
    """An arm that overruns the shared envelope breaks parity even if the
    envelope hash matches (it consumed more than was declared)."""
    claim, _ = load_claim("clean_supported")
    env = make_envelope(tokens=1000)
    results = []
    for name in ("single_agent", "open_sharing_swarm"):
        arm = arm_registry()[name](det_factory)
        ledger = BudgetLedger(env)
        spec = ArmSpec(arm_name=name, claim_id=claim.claim_id, envelope=env)
        res = arm.run(claim, ledger, spec, tmp_path / name)
        # Force an overrun on the second arm's reported usage.
        if name == "open_sharing_swarm":
            res = ArmResult(
                arm_name=res.arm_name,
                claim_id=res.claim_id,
                verdict_label=res.verdict_label,
                n_agents=res.n_agents,
                total_tokens=env.max_tokens + 1,
                total_wall_s=res.total_wall_s,
                envelope_sha256=res.envelope_sha256,
                detail=res.detail,
            )
        results.append(res)
    report = assert_budget_parity(results, env)
    assert report["parity"] is False


def _mk_result(name: str, env: BudgetEnvelope) -> ArmResult:
    return ArmResult(
        arm_name=name,
        claim_id="claim-x",
        verdict_label="SUPPORTED",
        n_agents=1,
        total_tokens=10,
        total_wall_s=0.5,
        envelope_sha256=env.sha256(),
        detail={},
    )


# ---------------------------------------------------------------------------
# 5. The harness wires all arms under ONE envelope and emits a parity report
# ---------------------------------------------------------------------------
def test_harness_runs_all_arms_and_reports_parity(tmp_path):
    claim, _ = load_claim("clean_supported")
    harness = ComparatorHarness(det_factory)
    out = harness.run(claim, make_envelope(), tmp_path / "harness")
    assert set(out["arms"]) == {"single_agent", "adaptive_central", "open_sharing_swarm"}
    assert out["parity"]["parity"] is True
    assert out["parity"]["n_arms"] == 3
    # Each arm's result is present with a comparable schema.
    for name, res in out["arms"].items():
        assert res["arm_name"] == name
        assert res["verdict_label"] in ("SUPPORTED", "REFUTED", "INCONCLUSIVE")


def test_harness_rejects_oversized_envelope_for_swarm(tmp_path):
    """A swarm of 3 agents cannot fit in an envelope that allows only 1 agent:
    the harness must surface a BudgetOverflow (parity is not silently faked)."""
    claim, _ = load_claim("clean_supported")
    harness = ComparatorHarness(det_factory)
    tiny = BudgetEnvelope(max_tokens=10_000, max_wall_s=30.0, max_agents=1)
    with pytest.raises(BudgetOverflow):
        harness.run(claim, tiny, tmp_path / "harness")


# ---------------------------------------------------------------------------
# 6. ArmResult is frozen (comparable, tamper-evident record)
# ---------------------------------------------------------------------------
def test_arm_result_is_frozen():
    res = _mk_result("single_agent", make_envelope())
    with pytest.raises(Exception):
        res.total_tokens = 999  # type: ignore[misc]
