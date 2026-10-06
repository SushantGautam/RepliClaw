"""V3 budget canaries — design ceq_arm_design.md §6 tests 11-12 + the
``accounted_call`` ≡ ``LiveEESSOrchestrator._llm_call`` equivalence pin
(design §5: the only reimplementation, pinned to equivalence by a test).

Offline only: FakeLLMClient + frozen case data + tmp_path artifacts.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from repliclaw.comparators.arms import ArmSpec
from repliclaw.comparators.budget import BudgetEnvelope, BudgetLedger
from repliclaw.comparators.runner import redact_claim_for_arms
from repliclaw.eess_live import fake
from repliclaw.eess_live.accounting import LiveBudgetLedger
from repliclaw.eess_live.escrow import PassThroughEscrow
from repliclaw.eess_live.orchestrator import LiveEESSOrchestrator
from repliclaw.experiments.v3 import ceq
from repliclaw.models import Claim

SEED = 20261010
MANAGER = "manager"


def _env(**kw: Any) -> BudgetEnvelope:
    base = dict(max_tokens=60_000, max_wall_s=900.0, max_agents=4)
    base.update(kw)
    return BudgetEnvelope(**base)


def _claim() -> Claim:
    return redact_claim_for_arms(
        Claim(
            claim_id="claim_live_test",
            statement="The baseline policy-RAG system fails to cite the controlling provision.",
            domain="policy_rag",
        )
    )


def _spec(arm: str, env: BudgetEnvelope) -> ArmSpec:
    return ArmSpec(arm_name=arm, claim_id="claim_live_test", envelope=env)


def _run_arm(arm_cls: Any, env: BudgetEnvelope, tmp_path: Path, label: str) -> Any:
    arm = arm_cls(lambda _a: fake.FakeLLMClient(), harness_seed=SEED)
    return arm.run(_claim(), BudgetLedger(env), _spec(arm_cls.arm_label, env), tmp_path / label)


# ---------------------------------------------------------------------------
# Test 11 — C-EQ aborts on a hard token-cap breach, the tripping call is
# recorded with REAL usage (never zero-filled), and the run is void
# (status=aborted_budget, verdict=None).
# ---------------------------------------------------------------------------

def test_ceq_budget_enforcement(tmp_path: Path):
    env = _env()
    mgr = ceq.CEQManager(
        claim=_claim(),
        out_root=tmp_path / "out",
        escrow=ceq.PassThroughEscrow(),
        # 50k tokens per call: the 2nd call would push the run past the
        # 60k envelope -> must abort fail-loud on call 2.
        client_factory=lambda _a: fake.FakeLLMClient(per_call=(50_000, 0)),
        envelope=env,
        harness_seed=SEED,
    )
    res = mgr.run()

    # Void run, not a faked completion.
    assert res.status == "aborted_budget"
    assert res.verdict is None

    ledger = mgr.ledger
    # The run aborted on the 2nd LLM call (forecast ok, planner round 1 trips).
    assert len(ledger.calls) == 2, [c.to_dict() for c in ledger.calls]
    # Tripping call carries its REAL usage — never zero-filled.
    tripping = ledger.calls[-1]
    assert tripping.prompt_tokens == 50_000
    assert tripping.completion_tokens == 0
    assert tripping.usage_present is True
    # Overflow event recorded, and the contract totals are consistent
    # (derived from the calls, including the tripping one).
    assert len(ledger.overflow_events) == 1
    assert ledger.overflow_events[0]["kind"] == "budget_exhausted"
    assert ledger.overflow_events[0]["tokens_at_event"] == 50_000
    contract = ledger.to_contract_dict()
    assert contract["totals"]["total_tokens"] == 100_000
    assert contract["totals"]["llm_calls"] == 2
    assert contract["envelope"]["sha256"] == env.sha256()
    # Result carries the same contract (run_metadata / budget_ledger.json).
    assert res.budget_ledger["totals"] == contract["totals"]


# ---------------------------------------------------------------------------
# Equivalence pin — accounted_call ≡ LiveEESSOrchestrator._llm_call.
# Two fresh ledgers, two identical fake clients, one call each through each
# path: the resulting ledger state must be identical (wall-clock excluded).
# Run per envelope-breach state too: both must record the tripping call with
# real usage and append one overflow event.
# ---------------------------------------------------------------------------

def _state(ledger: LiveBudgetLedger) -> Dict[str, Any]:
    calls = []
    for c in ledger.calls:
        d = c.to_dict()
        d.pop("wall_s")  # wall-clock is not comparable
        calls.append(d)
    return {
        "calls": calls,
        "overflow_events": [
            {k: v for k, v in e.items() if k != "message"} | {"msg_has_budget": "budget" in e["message"].lower()}
            for e in ledger.overflow_events
        ],
        "distinct_agents": ledger.distinct_agents,
    }


def _orch_for_call(
    tmp_path: Path, label: str, per_call: tuple, env: BudgetEnvelope
) -> LiveEESSOrchestrator:
    return LiveEESSOrchestrator(
        claim=_claim(),
        out_root=tmp_path / label,
        escrow=PassThroughEscrow(),
        policy_factory=lambda _a: None,
        client_factory=lambda _a: fake.FakeLLMClient(per_call=per_call),
        envelope=env,
        harness_seed=SEED,
    )


def test_accounted_call_matches_llm_call_identical_state(tmp_path: Path):
    env = _env()
    orch = _orch_for_call(tmp_path, "orch-ok", (40, 12), env)
    ledger = LiveBudgetLedger(env)
    client = fake.FakeLLMClient(per_call=(40, 12))

    p1 = orch._llm_call("alpha", orch.client_factory("alpha"), "p1", purpose="finding")
    p2 = ceq.accounted_call(
        ledger, client, "p1", purpose="finding", agent_id="alpha"
    )
    assert p1 == p2  # same payload semantics for the same fake response
    assert _state(orch.ledger) == _state(ledger)


def test_accounted_call_matches_llm_call_breach_state(tmp_path: Path):
    # Per-call 50k against a 60k envelope: the FIRST call already fits
    # (50k <= 60k) so we call twice — the 2nd must abort identically.
    env = _env()
    orch = _orch_for_call(tmp_path, "orch-breach", (50_000, 0), env)
    orch._llm_call("alpha", orch.client_factory("alpha"), "p1", purpose="finding")
    try:
        orch._llm_call("alpha", orch.client_factory("alpha"), "p2", purpose="finding")
    except Exception as exc:  # BudgetOverflow
        assert "budget" in str(exc).lower() or "tokens" in str(exc).lower()

    ledger = LiveBudgetLedger(env)
    client = fake.FakeLLMClient(per_call=(50_000, 0))
    ceq.accounted_call(ledger, client, "p1", purpose="finding", agent_id="alpha")
    raised = False
    try:
        ceq.accounted_call(ledger, client, "p2", purpose="finding", agent_id="alpha")
    except Exception as exc:
        raised = True
        assert "budget" in str(exc).lower() or "tokens" in str(exc).lower()
    assert raised
    assert _state(orch.ledger) == _state(ledger)
    # And both recorded the tripping call with real usage.
    assert ledger.calls[-1].prompt_tokens == 50_000
    assert ledger.calls[-1].usage_present is True


# ---------------------------------------------------------------------------
# Test 12 — agent-cap canary (R8): the SAME envelope admits C-EQ at
# max_agents=4 (manager + 3 investigators) but aborts the 4th distinct agent
# at max_agents=3; S-I completes under max_agents=1.
# ---------------------------------------------------------------------------

def test_ceq_agent_cap(tmp_path: Path):
    # (a) max_agents=4: C-EQ = manager + 3 investigators -> completes.
    res4 = _run_arm(ceq.CEQArm, _env(max_agents=4), tmp_path, "ceq-4")
    assert res4.detail["status"] == "completed"
    assert res4.n_agents == 4

    # (b) max_agents=3: the first investigator consult introduces a 4th
    # distinct agent -> aborts fail-loud.
    res3 = _run_arm(ceq.CEQArm, _env(max_agents=3), tmp_path, "ceq-3")
    assert res3.detail["status"] == "aborted_budget"
    assert res3.n_agents == 4  # the 4th agent is in the ledger
    # S-I (manager only) fits in max_agents=1.
    res_si = _run_arm(ceq.SIArm, _env(max_agents=1), tmp_path, "si-1")
    assert res_si.detail["status"] == "completed"
    assert res_si.n_agents == 1
