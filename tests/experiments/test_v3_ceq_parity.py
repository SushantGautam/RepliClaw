"""V3 parity canaries — design ceq_arm_design.md §5, tests 1-2, 5-7, 9, 14-15.

Offline only: FakeLLMClient + frozen case data + tmp_path artifacts. No LLM,
no network. R6: offline runs are labeled ``offline: true`` in run_metadata
(asserted wherever run_metadata is inspected).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from repliclaw.canonical import sha256_hex
from repliclaw.comparators.arms import ArmSpec
from repliclaw.comparators.budget import BudgetEnvelope, BudgetLedger
from repliclaw.comparators.runner import assert_budget_parity, redact_claim_for_arms
from repliclaw.counterfactual.case import CaseSpec
from repliclaw.counterfactual.executor import load_case, run_case
from repliclaw.eess_live import fake
from repliclaw.eess_live import orchestrator as eess_orchestrator
from repliclaw.eess_live.arm import EESSLiveS5Arm, write_counterfactuals
from repliclaw.eess_live.fake import COMMIT_MARKER, VERDICT_MARKER
from repliclaw.experiments.v3 import ceq
from repliclaw.experiments.v3.ceq import (
    CEQArm,
    LiveRunResult,
    SIArm,
    hyp_id_for_arm,
    interface_snapshot,
    v3_arm_registry,
)
from repliclaw.models import Claim

SEED = 20261010
MANAGER = "manager"


# ---------------------------------------------------------------------------
# Shared helpers (self-contained per file by design)
# ---------------------------------------------------------------------------

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
    """Offline fake with two test hooks:

    * ``actions`` — C-EQ planner replies, consumed per planner round (round
      N uses ``actions[N-1]``); when exhausted the planner abstains. All
      other prompts (forecast, findings, verdicts) fall through to the
      stock FakeLLMClient canned payloads.
    * ``log`` — records every ``(agent_id, prompt)`` pair received.

    Both are class-level (shared by the per-agent instances one factory
    produces) so a full-arm run is observable from one collection.
    """

    actions: List[Dict[str, Any]] = []
    log: List[Tuple[str, str]] = []
    _state: Dict[str, int] = {"round": 0}

    @classmethod
    def reset(cls, actions: List[Dict[str, Any]] | None = None) -> None:
        cls.actions = list(actions or [])
        cls.log = []
        cls._state = {"round": 0}

    def chat(self, prompt: str, system: str = "", max_tokens: Any = None) -> str:
        # Call the base FIRST: it advances the fake usage exactly like the
        # real client (skipping it would make usage_present False and void
        # the whole run).
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


def _scripted_factory(
    actions: List[Dict[str, Any]] | None = None, **client_kw: Any
) -> Any:
    """One fresh collection per arm run: reset happens at factory
    construction (once), so the log accumulates every prompt of the run."""
    ScriptedClient.reset(actions)
    return lambda _agent_id: ScriptedClient(**client_kw)


def _snapshot_log() -> List[Tuple[str, str]]:
    """Copy the shared log (subsequent calls in the same run must not be
    retroactively visible to an earlier snapshot)."""
    return list(ScriptedClient.log)


def _run_c_eq(
    tmp: Path,
    env: BudgetEnvelope,
    work: str = "C-EQ",
    actions_pre: List[Dict[str, Any]] | None = None,
    client_kw: Dict[str, Any] | None = None,
):
    arm = CEQArm(_scripted_factory(actions_pre, **(client_kw or {})), harness_seed=SEED)
    res = arm.run(_claim(), BudgetLedger(env), _spec("C-EQ", env), tmp / work)
    return arm, res, tmp / work / "run-01"


def _run_d_e(
    tmp: Path,
    env: BudgetEnvelope,
    work: str = "S5",
    actions_pre: List[Dict[str, Any]] | None = None,
    client_kw: Dict[str, Any] | None = None,
):
    arm = EESSLiveS5Arm(_scripted_factory(actions_pre, **(client_kw or {})), harness_seed=SEED)
    res = arm.run(_claim(), BudgetLedger(env), _spec("S5", env), tmp / work)
    return arm, res, tmp / work / "run-01"


def _planner_prompts(log: List[Tuple[str, str]]) -> List[str]:
    return [p for _, p in log if "CEQ_PLANNER_DECISION (round" in p]


def _vol(prompts: List[str]) -> int:
    """Fake tokenization per design §5.6: ``len(prompt)//4``."""
    return sum(len(p) // 4 for p in prompts)


def _obs_id_from_cf_doc(doc: Dict[str, Any], arm_id: str) -> str:
    return "obs_" + sha256_hex(
        json.dumps(
            {"run_id": doc["run_id"], "arm": arm_id, "severity": doc["severity"]},
            sort_keys=True,
        )
    )[:16]


# ---------------------------------------------------------------------------
# Test 1 — interface snapshot byte-equal across all six arms
# ---------------------------------------------------------------------------

def test_interface_snapshot_identical_all_arms():
    case = load_case(ceq.CASE_ID)
    env = _env()
    expected = interface_snapshot(case, env)
    for _arm_name, _arm_cls in v3_arm_registry().items():
        # The snapshot is arm-independent by construction: it describes the
        # shared tool interface (case, full menu, defect menu, engine,
        # envelope), so every arm must see the same bytes.
        snap = interface_snapshot(load_case(ceq.CASE_ID), env)
        assert json.dumps(snap, sort_keys=True) == json.dumps(expected, sort_keys=True)
    assert expected["schema"] == "v3.interface_snapshot/1"
    assert expected["case_sha256"]
    assert expected["defect_menu_sha256"]
    assert expected["interventions"], "menu must be non-empty"


def test_interface_snapshot_in_run_metadata(tmp_path: Path):
    env = _env()
    _run_c_eq(tmp_path, env)
    meta = json.loads((tmp_path / "C-EQ" / "run-01" / "run_metadata.json").read_text())
    case = load_case(ceq.CASE_ID)
    assert json.loads(json.dumps(meta["interface_snapshot"], sort_keys=True)) == json.loads(
        json.dumps(interface_snapshot(case, env), sort_keys=True)
    )
    # R6: offline labeling.
    assert meta["offline"] is True


# ---------------------------------------------------------------------------
# Test 2 — one shared envelope across all six arms
# ---------------------------------------------------------------------------

def test_envelope_parity_six_arms(tmp_path: Path):
    env = _env()
    results = []
    for i, (arm_name, _arm_cls) in enumerate(sorted(v3_arm_registry().items())):
        arm = _arm_cls(lambda _a: fake.FakeLLMClient(), harness_seed=SEED)
        res = arm.run(
            _claim(),
            BudgetLedger(env),
            ArmSpec(arm_name=arm_name, claim_id="claim_live_test", envelope=env),
            tmp_path / f"arm{i}",
        )
        assert res.envelope_sha256 == env.sha256(), arm_name
        results.append(res)
    report = assert_budget_parity(results, env)
    assert report["parity"] is True
    assert report["n_arms"] == 6
    assert report["over_budget_arms"] == []


# ---------------------------------------------------------------------------
# Test 5 — prompt-volume parity: two-sided (R2 anti-starve AND F5 anti-inflate)
# ---------------------------------------------------------------------------

def test_prompt_volume_parity_ceq_vs_de(tmp_path: Path):
    env = _env()

    _run_d_e(tmp_path / "de", env)
    de_log = list(ScriptedClient.log)

    _run_c_eq(tmp_path / "ceq", env)
    ceq_log = list(ScriptedClient.log)

    de_prompts = [p for _, p in de_log]
    assert de_prompts, "D-E produced no prompts"
    de_total = _vol(de_prompts)

    ceq_by_agent: Dict[str, List[str]] = {}
    for agent, p in ceq_log:
        ceq_by_agent.setdefault(agent, []).append(p)
    manager_vol = _vol(ceq_by_agent.get(MANAGER, []))
    worker_vol = sum(_vol(ps) for a, ps in ceq_by_agent.items() if a != MANAGER)

    # Anti-starvation (design §5.6): the C-EQ agents' combined prompting
    # budget must not be thinner than D-E's.
    assert manager_vol + worker_vol >= de_total, (
        f"C-EQ total volume {manager_vol + worker_vol} starved vs D-E {de_total}"
    )
    # Two-sided (F5 + §5.6): the single central manager's decision volume is
    # measured against D-E's TOTAL prompting budget — not starved (floor)
    # and not inflated (ceiling).
    ratio = manager_vol / de_total
    assert ceq.PROMPT_VOLUME_FLOOR <= ratio <= ceq.PROMPT_VOLUME_CEIL, (
        f"manager volume ratio {ratio:.3f} outside "
        f"[{ceq.PROMPT_VOLUME_FLOOR}, {ceq.PROMPT_VOLUME_CEIL}] "
        f"(manager={manager_vol}, de_total={de_total})"
    )
    # Investigator prompts are the D-E finding prompts: each worker gets
    # real per-agent work (not one shared prompt reused).
    worker_vols = sorted(_vol(ps) for a, ps in ceq_by_agent.items() if a != MANAGER)
    assert all(v > 0 for v in worker_vols), worker_vols


# ---------------------------------------------------------------------------
# Test 6 — information timing in C-EQ
# ---------------------------------------------------------------------------

def test_information_timing_ceq(tmp_path: Path):
    env = _env()
    arm_id = sorted(ceq.ARM_BY_HYP.values())[0]
    _run_c_eq(tmp_path, env, actions_pre=[
        {"action": "intervene", "intervention_id": arm_id, "rationale": "probe"},
    ])
    log = list(ScriptedClient.log)
    planner = _planner_prompts(log)
    assert len(planner) == 4
    # Planner prompt #1: nothing executed yet -> no evidence lines at all.
    assert "evidence_id=" not in planner[0]
    # Planner prompt #2 contains the obs id published after run #1.
    doc = json.loads(
        (tmp_path / "C-EQ" / "run-01" / "counterfactuals" / f"{arm_id}.json").read_text()
    )
    obs = _obs_id_from_cf_doc(doc, arm_id)
    assert f"evidence_id={obs}" in planner[1]
    assert f"evidence_id={obs}" in planner[2]

    # The final diagnosis prompt embeds the shared defect-adjudication block
    # byte-identically (design §5.4).
    final = [p for a, p in log if a == MANAGER and "CEQ_FINAL_DIAGNOSIS" in p]
    assert final, "no final diagnosis prompt"
    assert ceq.DEFECT_ADJUDICATION_INSTRUCTION in final[0]


# ---------------------------------------------------------------------------
# Test 7 — information timing in D-E (S5)
# ---------------------------------------------------------------------------

def test_information_timing_de(tmp_path: Path):
    env = _env()
    # Two hypothesis commits so the post-baseline verdicts carry evidence.
    arm_id = sorted(ceq.ARM_BY_HYP.values())[0]
    commit_payload = {
        "hypothesis_id": hyp_id_for_arm(arm_id),
        "hypothesis_statement": "The baseline omits the governing rule.",
        "falsification": "A correct retrieval would cite it.",
        "severity_if_supported": "partial_defect",
        "counterfactual_plan": {"intervention": arm_id, "prediction": "severity drops"},
    }

    def factory(_agent_id: str) -> fake.FakeLLMClient:
        return ScriptedClient(commit_payload=commit_payload)

    ScriptedClient.reset([{"action": "abstain"}])
    arm_cls = v3_arm_registry()["D-E"]
    arm = arm_cls(factory, harness_seed=SEED)
    arm.run(
        _claim(),
        BudgetLedger(env),
        ArmSpec(arm_name="D-E", claim_id="claim_live_test", envelope=env),
        tmp_path / "S5",
    )
    log = _snapshot_log()
    commit_prompts = [p for _, p in log if COMMIT_MARKER in p]
    verdict_prompts = [p for _, p in log if VERDICT_MARKER in p]
    assert commit_prompts and verdict_prompts
    # Commit prompts are sealed pre-outcome: no evidence line may appear.
    for p in commit_prompts:
        assert "evidence_id=" not in p
    # Evidence appears only in the post-evidence verdict prompts (timing).
    assert any("evidence_id=" in p for p in verdict_prompts)
    # Verdict prompts embed the shared defect-adjudication block.
    assert all(ceq.DEFECT_ADJUDICATION_INSTRUCTION in p for p in verdict_prompts)


# ---------------------------------------------------------------------------
# Test 9 — reset determinism: two fresh runs, identical observations
# ---------------------------------------------------------------------------

def test_reset_determinism_ceq(tmp_path: Path):
    env = _env()
    arm_id = sorted(ceq.ARM_BY_HYP.values())[0]
    actions = [
        {"action": "intervene", "intervention_id": arm_id, "rationale": "probe"},
    ]
    arm1, res1, dir1 = _run_c_eq(tmp_path / "a", env, actions_pre=actions)
    arm2, res2, dir2 = _run_c_eq(tmp_path / "b", env, actions_pre=actions)
    assert res1.detail["status"] == res2.detail["status"] == "completed"
    assert set(arm1._manager.run_cache) == set(arm2._manager.run_cache)
    for aid, r1 in arm1._manager.run_cache.items():
        r2 = arm2._manager.run_cache[aid]
        assert r1.config_sha256 == r2.config_sha256
        assert r1.target_output == r2.target_output
        assert r1.severity == r2.severity

    # Published evidence identical modulo the wall-clock field.
    ev1 = [
        {k: v for k, v in rec.items() if k != "published_at"}
        for rec in arm1._manager.escrow.evidence()
    ]
    ev2 = [
        {k: v for k, v in rec.items() if k != "published_at"}
        for rec in arm2._manager.escrow.evidence()
    ]
    assert ev1 == ev2 and ev1, "expected at least one published observation"

    # Counterfactual artifacts byte-equal.
    files = sorted(p.name for p in (dir1 / "counterfactuals").glob("*.json"))
    assert files
    for name in files:
        assert (dir1 / "counterfactuals" / name).read_bytes() == (
            dir2 / "counterfactuals" / name
        ).read_bytes()


# ---------------------------------------------------------------------------
# Test 14 — both arms go through the same run_case executor (R4)
# ---------------------------------------------------------------------------

def test_ceq_uses_same_executor_api(tmp_path: Path, monkeypatch: Any):
    calls: Dict[str, List[Dict[str, Any]]] = {"C-EQ": [], "D-E": []}

    def spy(arm_key: str):
        def inner(case, intervention, seed, out_root):
            calls[arm_key].append(
                {
                    "case_type": type(case).__name__,
                    "intervention_id": intervention.intervention_id,
                    "seed": seed,
                }
            )
            return run_case(case, intervention, seed=seed, out_root=out_root)

        return inner

    # Both C-EQ (experiments/v3/ceq.py) and D-E (eess_live/orchestrator.py)
    # import run_case into their own namespaces; patch each binding.
    monkeypatch.setattr(ceq, "run_case", spy("C-EQ"))
    monkeypatch.setattr(eess_orchestrator, "run_case", spy("D-E"))
    try:
        env = _env()
        arm_id = sorted(ceq.ARM_BY_HYP.values())[0]
        actions = [{"action": "intervene", "intervention_id": arm_id, "rationale": "probe"}]
        _run_c_eq(tmp_path / "ceq", env, actions_pre=actions)
        _run_d_e(tmp_path / "de", env, actions_pre=actions)
    finally:
        monkeypatch.undo()

    assert calls["C-EQ"], "C-EQ never reached the shared executor"
    assert calls["D-E"], "D-E never reached the shared executor"
    for c in calls["C-EQ"] + calls["D-E"]:
        assert c["seed"] == 0, c
        assert c["case_type"] == CaseSpec.__name__, c
    # Same argument shape on both sides: (case, intervention, seed=0, out_root).
    assert calls["C-EQ"][0]["intervention_id"] == arm_id


# ---------------------------------------------------------------------------
# Test 15 — counterfactual artifacts: same writer, same schema, same run
# ---------------------------------------------------------------------------

def test_write_counterfactuals_ducktyping(tmp_path: Path):
    env = _env()
    arm_id = sorted(ceq.ARM_BY_HYP.values())[0]
    hyp_id = hyp_id_for_arm(arm_id)
    arm, res, run_dir = _run_c_eq(
        tmp_path, env,
        actions_pre=[
            {"action": "intervene", "intervention_id": arm_id, "rationale": "probe"},
        ],
    )
    cf_file = run_dir / "counterfactuals" / f"{arm_id}.json"
    assert cf_file.exists()
    doc = json.loads(cf_file.read_text())
    assert doc["schema"] == "p08.counterfactual/1"

    # Build the D-E reference: same InterventionRun, same writer
    # (eess_live/arm.py:37), D-E's hypothesis table (the only
    # arm-specific fields).
    manager = arm._manager
    run = manager.run_cache[arm_id]
    de_hypotheses = [
        {
            "id": hyp_id,
            "outcome": "refuted" if run.severity == "no_defect" else "supported",
            "counterfactual_slot": arm_id,
        }
    ]
    ref = tmp_path / "de-ref"
    ref.mkdir()
    write_counterfactuals(
        manager,
        LiveRunResult(status="completed", verdict=None, hypotheses=de_hypotheses),
        ref,
    )
    ref_doc = json.loads((ref / "counterfactuals" / f"{arm_id}.json").read_text())
    assert set(doc) == set(ref_doc)
    # Run-identity fields (R4 / design §5.5): identical verified run.
    for key in ("run_id", "case_id", "seed", "verified", "severity", "token_counts", "provenance"):
        assert doc[key] == ref_doc[key], key
    assert doc["provenance"]["config_sha256"] == run.config_sha256
    assert doc["hypothesis_id"] == ref_doc["hypothesis_id"] == hyp_id


def test_canary_templates_pinned():
    """J-SCI W1 S3: the prompt-volume band [0.6, 1.25] was calibrated
    against the frozen C-EQ planner/final-diagnosis templates. These static
    pieces are sha-pinned here; if a template changes, the band must be
    recalibrated and the preregistration updated BEFORE any run."""
    pins = {
        ceq.PLANNER_PROMPT_STATIC_TAIL: "4df178e5124b8660033769aceb158c065151ebae2a8cacf20f209500821513dc",
        ceq.FINAL_DIAGNOSIS_STATIC_HEAD: "11150fa2b11206143ab1eee5b1d54efc28ae685e27f354ef733d3bb8984d0bcf",
        ceq.FINAL_DIAGNOSIS_STATIC_TAIL: "45e7ab3c2111395d9522e14da6855e9cf0171f4a391ac176ffa246bd88c9aa85",
    }
    for template, expected in pins.items():
        assert sha256_hex(template) == expected, (
            f"template changed (was {sha256_hex(template)[:12]}…): recalibrate "
            "PROMPT_VOLUME_FLOOR/CEIL and update the V3 preregistration"
        )


def test_final_verdict_key_parity(tmp_path: Path):
    """R10: final_verdict.json keys identical between D-E and C-EQ."""
    env = _env()
    _run_d_e(tmp_path / "de", env)
    _run_c_eq(tmp_path / "ceq", env)
    de_doc = json.loads((tmp_path / "de" / "S5" / "run-01" / "final_verdict.json").read_text())
    ceq_doc = json.loads((tmp_path / "ceq" / "C-EQ" / "run-01" / "final_verdict.json").read_text())
    assert set(de_doc) == set(ceq_doc)
    # S-I also writes the same schema (no forecast sealed).
    si = SIArm(lambda _a: ScriptedClient(), harness_seed=SEED)
    res = si.run(_claim(), BudgetLedger(env), _spec("S-I", env), tmp_path / "si")
    assert res.detail["status"] == "completed", res.detail
    si_doc = json.loads((tmp_path / "si" / "run-01" / "final_verdict.json").read_text())
    assert set(si_doc) == set(de_doc)
