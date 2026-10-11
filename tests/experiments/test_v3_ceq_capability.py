"""V3 capability-matrix + cripple canaries R1/R3/R7 (+ F4 channel) —
design ceq_arm_design.md §4, §6 tests 3-4, 8, 10; §7 risks R1, R3, R7.

Offline only: FakeLLMClient + frozen case data + tmp_path artifacts.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from repliclaw.comparators.arms import ArmSpec
from repliclaw.comparators.budget import BudgetEnvelope, BudgetLedger
from repliclaw.comparators.runner import redact_claim_for_arms
from repliclaw.eess_live import fake
from repliclaw.eess_live.orchestrator import EVIDENCE_FORBIDDEN_SUBSTRINGS
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


class ScriptedClient(fake.FakeLLMClient):
    """Same test fake as the parity file: ``actions`` scripts the C-EQ
    planner per round; ``log`` records every (agent_id, prompt)."""

    actions: List[Dict[str, Any]] = []
    log: List[Tuple[str, str]] = []
    _state: Dict[str, int] = {"round": 0}

    @classmethod
    def reset(cls, actions: List[Dict[str, Any]] | None = None) -> None:
        cls.actions = list(actions or [])
        cls.log = []
        cls._state = {"round": 0}

    def chat(self, prompt: str, system: str = "", max_tokens: Any = None) -> str:
        # Base first: advances the fake usage exactly like the real client.
        reply = super().chat(prompt, system=system, max_tokens=max_tokens)
        agent = "unknown"
        for line in prompt.splitlines():
            if line.strip().startswith("AGENT_ID:"):
                agent = line.split(":", 1)[1].strip()
        type(self).log.append((agent, prompt))
        if "CEQ_PLANNER_DECISION (round" in prompt:
            st = type(self)._state
            st["round"] += 1
            acts = type(self).actions
            act = acts[st["round"] - 1] if st["round"] <= len(acts) else {}
            return json.dumps(act)
        return reply


def _scripted_factory(actions: List[Dict[str, Any]] | None = None) -> Any:
    ScriptedClient.reset(actions)
    return lambda _agent_id: ScriptedClient()


# ---------------------------------------------------------------------------
# Test 3 — unregistered intervention is rejected, never executed (R1-adjacent)
# ---------------------------------------------------------------------------

def test_ceq_rejects_unregistered_intervention(tmp_path: Path):
    env = _env()
    # A literal intervention id is fine in TESTS (the static no-fixed-script
    # test only constrains the ceq.py source).
    actions = [
        {"action": "intervene", "intervention_id": "I_X_bogus", "rationale": "off-menu"},
        {"action": "abstain", "rationale": "ok"},
    ]
    arm = ceq.CEQArm(_scripted_factory(actions), harness_seed=SEED)
    res = arm.run(_claim(), BudgetLedger(env), _spec("C-EQ", env), tmp_path / "C-EQ")
    assert res.detail["status"] == "completed"
    assert res.detail["slots_executed"] == 0
    mgr = arm._manager
    rejected = [t for t in mgr.traces if t["type"] == "rejected_intervention"]
    assert rejected, "no rejected_intervention trace"
    assert rejected[0]["payload"]["intervention_id"] == "I_X_bogus"
    # The executor was never called: no run cache, no counterfactual artifacts.
    assert mgr.run_cache == {}
    cf = tmp_path / "C-EQ" / "run-01" / "counterfactuals"
    assert not cf.exists() or not list(cf.glob("*.json"))


# ---------------------------------------------------------------------------
# Test 4 — forbidden-substring guard: corrupted evidence fails loud (R3)
# ---------------------------------------------------------------------------

def test_ceq_forbidden_substring_guard(tmp_path: Path, monkeypatch: Any):
    """Design test 4: an evidence record containing a forbidden oracle
    substring makes the arm fail loud (RuntimeError) instead of leaking
    sealed content into the planner prompt."""
    mgr = ceq.CEQManager(
        claim=_claim(),
        out_root=tmp_path / "out",
        escrow=ceq.PassThroughEscrow(),
        client_factory=lambda _a: ScriptedClient(),
        envelope=_env(),
        harness_seed=SEED,
    )
    bad_record = {
        "observation_id": "obs_corrupt0000000001",
        "case_id": "policy_rag_v1",
        "producer_id": "manager",
        "run_id": "policy_rag_v1::I0_baseline::seed0",
        "kind": "verified_run",
        "summary": "corrupted outcome label",
        # The block renders outcome from data.severity, so the leak must be
        # there to be caught (rendered fields only are guarded).
        "data": {
            "intervention_id": "I0_baseline",
            "severity": EVIDENCE_FORBIDDEN_SUBSTRINGS[0] + "_leak",
        },
        "provenance": {"config_sha256": "0" * 64},
        "published_at": "2026-10-09T00:00:00Z",
        "status": "public",
    }
    monkeypatch.setattr(
        type(mgr.escrow), "evidence", lambda self: [bad_record]
    )
    try:
        mgr._planner_prompt(1, None)
    except RuntimeError as exc:
        assert EVIDENCE_FORBIDDEN_SUBSTRINGS[0] in str(exc)
        return
    raise AssertionError("planner prompt built despite corrupted evidence")


def test_forbidden_substring_guard_unit():
    """Direct unit of the union builder's guard (ceq.py:298, substring list
    from orchestrator.py:59)."""
    records = [
        {
            "observation_id": "obs_corrupt0000000001",
            "case_id": "policy_rag_v1",
            "run_id": "policy_rag_v1::I0_baseline::seed0",
            "kind": "verified_run",
            "summary": "corrupted outcome label",
            "data": {
                "intervention_id": "I0_baseline",
                "severity": EVIDENCE_FORBIDDEN_SUBSTRINGS[0] + "_leak",
            },
            "provenance": {"config_sha256": "0" * 64},
        }
    ]
    try:
        ceq._evidence_block_union(records)
    except RuntimeError as exc:
        assert EVIDENCE_FORBIDDEN_SUBSTRINGS[0] in str(exc)
        return
    raise AssertionError("no RuntimeError raised on corrupted evidence")


# ---------------------------------------------------------------------------
# Test 8 — offline adaptivity: the plan changes because of evidence (R1)
# ---------------------------------------------------------------------------

def test_ceq_adaptivity_offline(tmp_path: Path):
    env = _env()
    r_arm = ceq.ARM_BY_HYP["H_R"]
    # Planner schedule: round 1 -> intervene <H_R arm>; rounds 2-4 abstain.
    # The canary is not "which arm was picked" (a fixed script could pick
    # the same one) — it is that the LATER decision prompt is conditioned on
    # the observation the run produced: round 2's prompt carries round 1's
    # obs id, so the choice at round 2 is provably evidence-driven.
    actions = [
        {"action": "intervene", "intervention_id": r_arm, "rationale": "probe"},
    ]
    arm = ceq.CEQArm(_scripted_factory(actions), harness_seed=SEED)
    res = arm.run(_claim(), BudgetLedger(env), _spec("C-EQ", env), tmp_path / "C-EQ")
    assert res.detail["status"] == "completed"
    assert res.detail["slots_executed"] == 1

    mgr = arm._manager
    # Exactly one executor run for one hypothesis arm.
    assert set(mgr.run_cache) == {r_arm}

    planner = [p for _, p in ScriptedClient.log if "CEQ_PLANNER_DECISION (round" in p]
    assert len(planner) == ceq.MAX_PLANNER_ROUNDS
    # Round 1 had nothing to condition on.
    assert "evidence_id=" not in planner[0]
    # Round 2's decision was made AFTER the observation existed and its
    # prompt contains that exact observation id -> the choice changed
    # because of evidence.
    run = mgr.run_cache[r_arm]
    obs_id = _obs_id(run)
    assert f"evidence_id={obs_id}" in planner[1]

    # Choice trace: abstain rounds come after the evidence-conditioned round.
    trace = mgr.choice_trace
    assert trace[0]["action"] == "intervene"
    assert trace[0]["intervention_id"] == r_arm
    assert [t["action"] for t in trace[1:]] == ["abstain"] * (ceq.MAX_PLANNER_ROUNDS - 1)


def _obs_id(run: Any) -> str:
    from repliclaw.canonical import sha256_hex

    return "obs_" + sha256_hex(
        json.dumps(
            {"run_id": run.run_id, "arm": run.intervention_id, "severity": run.severity},
            sort_keys=True,
        )
    )[:16]


# ---------------------------------------------------------------------------
# Test 10 — capability matrix pinned at class level + runtime commit counts
# ---------------------------------------------------------------------------

def test_capability_matrix():
    """Class level: every row equals design section 4's table exactly."""
    m = ceq.capability_matrix()
    assert set(m) == {"D-E", "C-EQ", "D-N", "D-R", "C-NE", "S-I"}

    rows = {
        # arm: (executor, menu, sealed, view, decentralized, n_inv, adaptive, fixed)
        "D-E": ("Y", "Y", "Y per-agent", "Y", "Y (EIG)", 3, "Y", "FORBIDDEN"),
        "C-EQ": ("Y", "Y", "Y (manager, 1)", "Y", "N", 4, "Y", "FORBIDDEN"),
        "D-N": ("Y", "Y", "N", "N (raw)", "Y (EIG)", 3, "Y", "n/a (seeded, not script)"),
        "D-R": ("Y", "Y", "Y per-agent", "Y", "Y (seeded rand)", 3, "Y (seeded)", "n/a (seeded, not script)"),
        "C-NE": ("Y", "Y", "N", "N (raw)", "N", 4, "Y", "FORBIDDEN"),
        "S-I": ("Y", "Y", "N", "N (own obs)", "N", 1, "Y (single)", "FORBIDDEN"),
    }
    for arm, (ex, menu, sealed, view, deconf, n_inv, adaptive, fixed) in rows.items():
        p = m[arm]
        assert p.counterfactual_executor == ex, arm
        assert p.full_menu == menu, arm
        assert p.sealed_forecast == sealed, arm
        assert p.verified_evidence_view == view, arm
        assert p.decentralized_selection == deconf, arm
        assert p.n_investigators == n_inv, arm
        assert p.adaptive_replanning == adaptive, arm
        assert p.sealed_truth_read == "FORBIDDEN", arm
        assert p.fixed_script == fixed, arm

    # F6: decision budgets are explicit in the registry, and C-EQ's cap is a
    # MATCHED cap, not an implicit one.
    assert m["D-E"].decision_budget == ceq.DE_DECISION_BUDGET == 9
    assert m["D-E"].max_decision_rounds == ceq.DE_MAX_CYCLES == 2
    for arm in ("C-EQ", "C-NE", "S-I"):
        assert m[arm].decision_budget == ceq.MAX_PLANNER_ROUNDS == 4
        assert m[arm].max_decision_rounds == ceq.MAX_PLANNER_ROUNDS == 4


def _commit_events(escrow: Any) -> List[Dict[str, Any]]:
    ev = getattr(escrow, "events", None)
    events = ev() if callable(ev) else (ev or [])
    return [e for e in events if e.get("kind") == "commitment"]


def test_capability_commit_counts_runtime(tmp_path: Path):
    """Runtime: instrumented escrow commit calls — escrowed arms >=1,
    pass-through arms ==0 (R7: no escrow confound re-introduction)."""
    env = _env()
    reg = ceq.v3_arm_registry()

    def run_arm(arm_key: str) -> Any:
        arm_cls = reg[arm_key]
        arm = arm_cls(lambda _a: fake.FakeLLMClient(), harness_seed=SEED)
        arm.run(_claim(), BudgetLedger(env), _spec(arm_key, env), tmp_path / arm_key)
        return arm

    # D-* arms expose the orchestrator's escrow on the adapter; C-*/S-*
    # expose the manager's escrow.
    def escrow_of(arm: Any) -> Any:
        mgr = getattr(arm, "_manager", None)
        if mgr is not None:
            return mgr.escrow
        return getattr(arm, "_orch", None).escrow if getattr(arm, "_orch", None) else None

    for arm_key in ("D-E", "C-EQ", "D-R"):
        arm = run_arm(arm_key)
        esc = escrow_of(arm)
        assert esc is not None and esc.mode == "escrow", f"{arm_key} not escrowed"
        n = len(_commit_events(esc))
        assert n >= 1, f"{arm_key} sealed no forecast (expected >=1 commits)"

    for arm_key in ("D-N", "C-NE", "S-I"):
        arm = run_arm(arm_key)
        esc = escrow_of(arm)
        assert esc is not None, f"{arm_key} escrow not exposed"
        assert esc.mode == "pass_through", f"{arm_key} is escrowed (R7)"
        n = len(_commit_events(esc))
        assert n == 0, f"{arm_key} sealed {n} forecasts (expected 0)"


def test_consultation_channel_bounded_and_logged(tmp_path: Path):
    """F4: every manager<->investigator message is counted, capped, and
    recorded in run metadata; the cap is enforced fail-loud."""
    env = _env()
    arm = ceq.CEQArm(_scripted_factory([]), harness_seed=SEED)
    arm.run(_claim(), BudgetLedger(env), _spec("C-EQ", env), tmp_path / "C-EQ")
    mgr = arm._manager

    meta = json.loads((tmp_path / "C-EQ" / "run-01" / "run_metadata.json").read_text())
    ch = meta["consultation_channel"]
    assert ch["cap_per_round"] == ceq.CONSULT_CAP_PER_ROUND == 1
    assert ch["cap_per_case"] == ceq.CONSULT_CAP_PER_CASE == 1
    messages = ch["messages"]
    assert messages, "consultation channel not logged"
    per_agent: Dict[str, int] = {}
    for m in messages:
        per_agent[m["agent_id"]] = per_agent.get(m["agent_id"], 0) + 1
    for agent, n in per_agent.items():
        assert n <= ceq.CONSULT_CAP_PER_CASE, (agent, n)
    assert ch["per_agent_prompt_counts"] == {
        a: len(ps) for a, ps in sorted(mgr.prompt_log.items())
    }
    # Exactly one consultation per investigator (3 investigators in C-EQ).
    assert per_agent == {a: 1 for a in ceq.AGENT_IDS[:3]}

    # Fail-loud: a 2nd consultation for the same agent in the same case is
    # a hard error.
    escrow = ceq.PassThroughEscrow()
    mgr2 = ceq.CEQManager(
        claim=_claim(),
        out_root=tmp_path / "out2",
        escrow=escrow,
        client_factory=lambda _a: ScriptedClient(),
        envelope=env,
        harness_seed=SEED,
    )
    victim = ceq.AGENT_IDS[0]
    # Two prior consults for the same agent in the same case: the next one
    # must be refused.
    mgr2.consultation_log.extend(
        {"agent_id": victim, "purpose": "consult", "prompt_chars": 1} for _ in range(2)
    )
    try:
        mgr2._enforce_consult_caps(victim, "consult")
    except RuntimeError as exc:
        assert "cap exceeded" in str(exc)
        return
    raise AssertionError("consult cap not enforced fail-loud")
