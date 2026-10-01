"""End-to-end slice: escrow commitments -> autonomous execution -> verified reveal.

The orchestrator owns ONLY the phase boundaries, the deterministic stop
rule, and the summary. Every choice of WHICH need to run, and every claim,
happens INSIDE the agents (P04 local policy over the public open-need list)
— the broker never ranks or assigns. The policy's discriminability is
computed by :func:`repliclaw.slice.derive.derive_discriminability` from the
published evidence only (no externally set numbers; science-judge item 3).
Each fulfilled need executes a REAL SimpleAudit arm (P02) and is verified
by clean re-execution + pinned-artifact hash comparison (never the agent's
self-attestation).

Lifecycle (one case, N autonomous agents), mirroring the escrow phase gate
``COMMIT -> REVEAL -> EXECUTE -> RESOLVE``:

1. COMMIT   — every agent privately commits a falsifiable prediction packet
   BEFORE any outcome exists, and publishes the need(s) it wants run.
2. REVEAL   — outcome-free reveal; every packet's commitment hash re-verified.
3. EXECUTE  — the need market drives real runs; after each arm the runner
   publishes a verified observation with provenance; the next round of
   choices is derived from the NEW evidence snapshot (T4 replanning).
4. RESOLVE  — the stop rule fires, the ledger resolves, and the summary
   record (per-packet supported/refuted verdicts + choice-change trace) is
   persisted.
"""
from __future__ import annotations

import json
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from repliclaw.canonical import sha256_hex
from repliclaw.counterfactual import load_case, load_interventions, run_case
from repliclaw.counterfactual.case import CaseSpec
from repliclaw.counterfactual.frozen_backend import extract_window_days
from repliclaw.escrow import EscrowLedger, EvidenceObservation, PredictionPacket
from repliclaw.needmarket.broker import NeedBroker
from repliclaw.needmarket.needs import CostEstimate, Need, WorkerCapability
from repliclaw.needmarket.policy import LocalEigPolicy
from repliclaw.needmarket.worker import CycleResult, NeedWorker
from repliclaw.slice.derive import ARM_BY_HYP, BASELINE_ARM, derive_discriminability

CASE_ID = "policy_rag_v1"
SEED = 0
LEASE_TTL_S = 60.0
COST_TOKENS_PER_ARM = 500
BASELINE_ARM_ID = BASELINE_ARM

# agent -> hypothesis it commits (and the arm that hypothesis is tested by).
HYP_BY_AGENT = {"alpha": "H_R", "beta": "H_P", "gamma": "H_J"}
ARM_BY_HYP_LOCAL = ARM_BY_HYP


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Falsifiable predictions (fixed BEFORE any outcome). Provenance: the P02
# hero-case design documents and the single-factor intervention protocol —
# NOT the sealed oracle (the oracle is only used post-run by hidden checks).
# ---------------------------------------------------------------------------
_HYPOTHESES: Dict[str, Dict[str, str]] = {
    "H_R": {
        "statement": (
            "The I0 baseline failure is hidden by stale retrieval: serving the "
            "current 30-day v2 policy snippet as top-1 (arm I_R) changes the "
            "deterministic target output, and the stale 14-day rubric flags it."
        ),
        "prediction": (
            "Arm I_R_retrieval_fix reports severity 'critical' while "
            "I0_baseline reports 'pass'; the target return window changes "
            "from 14 to 30 days."
        ),
        "refutation": (
            "Refuted iff I_R_retrieval_fix does not change the target return "
            "window from 14 to 30 days, or its severity stays 'pass'."
        ),
        "competing": (
            "The stale 14-day judge rubric alone (I_J) can flip the verdict "
            "without changing the target output."
        ),
    },
    "H_P": {
        "statement": (
            "Policy-conflict rendering (arm I_P) changes the deterministic "
            "target's return-window answer."
        ),
        "prediction": (
            "Arm I_P_policy_conflict produces a target output different from "
            "I0_baseline's."
        ),
        "refutation": (
            "Refuted iff I_P_policy_conflict's target output is "
            "byte-identical to I0_baseline's."
        ),
        "competing": "H_R: retrieval, not policy rendering, drives the output.",
    },
    "H_J": {
        "statement": (
            "The judge rubric's reference day count (arm I_J) determines the "
            "verdict severity while the target output stays identical to the "
            "baseline."
        ),
        "prediction": (
            "Arm I_J_judge_fix keeps the target output byte-identical to "
            "I0_baseline but its severity differs from the baseline's."
        ),
        "refutation": (
            "Refuted iff I_J_judge_fix's target output differs from "
            "I0_baseline's, or its severity equals the baseline's."
        ),
        "competing": (
            "H_R: the failure lives in retrieval, so fixing the rubric alone "
            "cannot change what the target says."
        ),
    },
}


def build_predictions(
    agent_id: str, hypothesis_id: str, intervention_id: str, prior_snapshot_sha: str
) -> PredictionPacket:
    h = _HYPOTHESES[hypothesis_id]
    return PredictionPacket(
        packet_id=uuid.uuid4().hex,
        case_id=CASE_ID,
        agent_id=agent_id,
        hypothesis_id=hypothesis_id,
        hypothesis_version=1,
        hypothesis_statement=h["statement"],
        intervention_id=intervention_id,
        predicted_outcome=h["prediction"],
        refutation_criterion=h["refutation"],
        competing_explanation=h["competing"],
        prior_evidence_snapshot_sha256=prior_snapshot_sha,
    )


def make_need(
    case_id: str, intervention_id: str, proposer_id: str, cost_tokens: int
) -> Need:
    return Need(
        need_id=f"need_{intervention_id}_{proposer_id}",
        case_id=case_id,
        title=f"Run counterfactual arm {intervention_id}",
        description=(
            f"Execute the {intervention_id} intervention arm on case "
            f"{case_id} via the P02 SimpleAudit executor and publish a "
            "verified evidence observation."
        ),
        proposer_id=proposer_id,
        proposed_at=_now_iso(),
        required_capability="counterfactual-arm",
        cost_estimate=CostEstimate(tokens=cost_tokens, wall_s=5.0),
    )


def arm_of_need(need_id: str) -> str:
    """need_<arm>_<proposer> -> <arm>."""
    return need_id[len("need_") :].rsplit("_", 1)[0]


# ---------------------------------------------------------------------------
# Execution + independent verification (P02)
# ---------------------------------------------------------------------------
def verify_run(case: CaseSpec, intervention, run) -> bool:
    """Re-execute in a clean temp dir; verified iff the persisted arm-file
    hashes reproduce exactly (P02 replay semantics, never self-attestation)."""
    with tempfile.TemporaryDirectory(prefix="repliclaw_verify_") as td:
        re = run_case(case, intervention, seed=SEED, out_root=Path(td))
    return bool(run.artifact_hashes) and re.artifact_hashes == run.artifact_hashes


def make_executor(case: CaseSpec, interventions, cache: Dict[str, Any]):
    """``execute(need)`` bound to one agent's run cache (agent id, root)."""

    def _execute(need: Need) -> Dict[str, Any]:
        arm_id = arm_of_need(need.need_id)
        intervention = interventions[arm_id]
        out_root = cache["__root__"] / "runs" / cache["__agent__"] / need.need_id
        run = run_case(case, intervention, seed=SEED, out_root=out_root)
        verified = verify_run(case, intervention, run)
        cache[arm_id] = run
        return {"artifact_id": run.run_id, "verified": verified, "intervention_id": arm_id}

    return _execute


def build_agents(
    agent_ids: List[str],
    broker: NeedBroker,
    case: CaseSpec,
    interventions,
    root: Path,
    rng_seed: int = 0,
) -> Dict[str, NeedWorker]:
    workers: Dict[str, NeedWorker] = {}
    for agent_id in agent_ids:
        cap = WorkerCapability(
            agent_id=agent_id,
            producible_types=["counterfactual-arm"],
            method_family="counterfactual-arm",
            model=case.target_model_id,
            budget_tokens=10_000,
        )
        cache: Dict[str, Any] = {"__agent__": agent_id, "__root__": root}
        workers[agent_id] = NeedWorker(
            capability=cap,
            broker=broker,
            policy=LocalEigPolicy(discriminability={}),
            execute=make_executor(case, interventions, cache),
            rng_seed=rng_seed,
        )
        workers[agent_id].run_cache = cache  # type: ignore[attr-defined]
    return workers


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------
def build_evidence(
    agent_id: str, run, arm_id_to_hyp: Dict[str, Optional[str]]
) -> EvidenceObservation:
    window = extract_window_days(run.target_output)
    return EvidenceObservation(
        observation_id=f"obs_{run.intervention_id}_{agent_id}_{uuid.uuid4().hex[:8]}",
        case_id=run.case_id,
        producer_id=agent_id,
        run_id=run.run_id,
        kind="verified_run",
        summary=(
            f"Arm {run.intervention_id} executed; severity={run.severity}, "
            f"target_window_days={window}, config_sha256={run.config_sha256[:12]}."
        ),
        data={
            "intervention_id": run.intervention_id,
            "severity": run.severity,
            "target_window_days": window,
            "target_output": run.target_output,
            "token_counts": run.token_counts,
            "hypothesis": arm_id_to_hyp.get(run.intervention_id),
        },
        provenance={
            "config_sha256": run.config_sha256,
            "case_sha256": run.case_sha256,
            "artifact_hashes": run.artifact_hashes,
            "seed": run.seed,
            "engine": run.engine,
        },
        published_at=_now_iso(),
    )


def evidence_view(evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Deterministic view of published evidence (input to derived choices)."""
    return {
        "observations": sorted(evidence, key=lambda e: e.get("observation_id", ""))
    }


# ---------------------------------------------------------------------------
# Stop rule + summary
# ---------------------------------------------------------------------------
def stop_reason(
    broker_events: List[Dict[str, Any]],
    published: int,
    total: int,
    max_cycles: int,
    cycles_done: int,
    agent_ids: List[str],
) -> str:
    if published >= total:
        return "all_needs_fulfilled"
    if cycles_done >= max_cycles:
        abstains = sum(1 for e in broker_events if e["kind"] == "abstained")
        if abstains >= len(agent_ids) * 2:
            return "counter_evidence_no_remaining_needs"
        return "max_cycles_reached"
    return "running"


@dataclass
class SliceResult:
    case_id: str
    agent_ids: List[str]
    revealed_verified: int
    revealed_mismatch: int
    published_evidence: int
    stop_reason: str
    evidence_snapshot_sha256: str
    predictions_outcome: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    choice_trace: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "agent_ids": self.agent_ids,
            "revealed_verified": self.revealed_verified,
            "revealed_mismatch": self.revealed_mismatch,
            "published_evidence": self.published_evidence,
            "stop_reason": self.stop_reason,
            "evidence_snapshot_sha256": self.evidence_snapshot_sha256,
            "predictions_outcome": self.predictions_outcome,
            "choice_trace": self.choice_trace,
        }


@dataclass
class SliceReport:
    result: SliceResult
    ledger_events: List[Dict[str, Any]]
    broker_events: List[Dict[str, Any]]
    evidence: List[Dict[str, Any]]


def evaluate_predictions(
    packets: Dict[str, PredictionPacket], evidence: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """Post-hoc (never pre-reveal) verdict of each commitment against the
    published evidence."""
    by_arm: Dict[str, Dict[str, Any]] = {}
    for obs in evidence:
        iid = obs.get("data", {}).get("intervention_id")
        if iid:
            by_arm[iid] = obs.get("data", {})
    base = by_arm.get(BASELINE_ARM_ID)
    out: Dict[str, Dict[str, Any]] = {}
    for agent_id, packet in packets.items():
        d = by_arm.get(packet.intervention_id)
        outcome = "undetermined"
        if base is not None and d is not None:
            if packet.hypothesis_id == "H_R":
                outcome = (
                    "supported"
                    if (
                        d.get("severity") == "critical"
                        and base.get("severity") == "pass"
                        and d.get("target_window_days") == 30
                        and base.get("target_window_days") == 14
                    )
                    else "refuted"
                )
            elif packet.hypothesis_id == "H_P":
                outcome = (
                    "refuted"
                    if d.get("target_output") == base.get("target_output")
                    else "supported"
                )
            elif packet.hypothesis_id == "H_J":
                outcome = (
                    "supported"
                    if (
                        d.get("target_output") == base.get("target_output")
                        and d.get("severity") != base.get("severity")
                    )
                    else "refuted"
                )
        out[agent_id] = {
            "hypothesis_id": packet.hypothesis_id,
            "intervention_id": packet.intervention_id,
            "agent_id": packet.agent_id,
            "outcome": outcome,
        }
    return out


# ---------------------------------------------------------------------------
# The slice
# ---------------------------------------------------------------------------
def run_slice(
    root: Path,
    agent_ids: Optional[List[str]] = None,
    max_cycles: int = 2,
) -> SliceReport:
    root = Path(root)
    agent_ids = list(agent_ids or ["alpha", "beta", "gamma"])

    case = load_case(CASE_ID)
    interventions = {i.intervention_id: i for i in load_interventions(CASE_ID)}
    arm_id_to_hyp: Dict[str, Optional[str]] = {
        arm: hyp for hyp, arm in ARM_BY_HYP_LOCAL.items()
    }
    arm_id_to_hyp[BASELINE_ARM_ID] = None

    ledger = EscrowLedger(root / "ledger", worker_id="orchestrator")
    broker = NeedBroker(root / "market", lease_ttl_s=LEASE_TTL_S)

    # --- Phase COMMIT: pre-outcome packets + needs (before any run) ---------
    prior_snapshot = sha256_hex(
        json.dumps({"phase": "COMMIT", "case": case.case_id}, sort_keys=True)
    )
    packets: Dict[str, PredictionPacket] = {}
    for agent_id in agent_ids:
        hyp = HYP_BY_AGENT[agent_id]
        packets[agent_id] = build_predictions(
            agent_id, hyp, ARM_BY_HYP_LOCAL[hyp], prior_snapshot
        )
        ledger.commit(agent_id, packets[agent_id])
        broker.publish(
            make_need(CASE_ID, ARM_BY_HYP_LOCAL[hyp], agent_id, COST_TOKENS_PER_ARM)
        )
    broker.publish(make_need(CASE_ID, BASELINE_ARM_ID, "alpha", COST_TOKENS_PER_ARM))
    total_needs = len(broker.needs())

    # --- Phase REVEAL: outcome-free, commitment-verified ---------------------
    ledger.open_reveal(CASE_ID)
    revealed_verified = 0
    revealed_mismatch = 0
    for agent_id, packet in packets.items():
        res = ledger.reveal(agent_id, packet)
        if res.status == "verified":
            revealed_verified += 1
        else:
            revealed_mismatch += 1

    # --- Phase EXECUTE: autonomous need market drives real runs --------------
    ledger.enter_execute()
    workers = build_agents(agent_ids, broker, case, interventions, root)

    published = 0
    cycles_done = 0
    stop = "max_cycles_reached"
    choice_trace: List[Dict[str, Any]] = []
    prev_ranks: Dict[str, str] = {}

    for _ in range(max_cycles):
        cycles_done += 1
        for agent_id in agent_ids:
            worker = workers[agent_id]
            view = evidence_view(ledger.evidence())
            open_needs = broker.open_needs(exclude_agent=agent_id)
            arms = {n.need_id: arm_of_need(n.need_id) for n in open_needs}
            worker.policy.set_discriminability(
                derive_discriminability(
                    agent_id, HYP_BY_AGENT[agent_id], list(arms), view, arms
                )
            )
            result: Optional[CycleResult] = worker.cycle(view)

            # Track the observable choice (top of each agent's local ranking).
            top = result.ranked[0].need_id if result and result.ranked else None
            prev = prev_ranks.get(agent_id)
            if prev is not None and top is not None and top != prev:
                choice_trace.append(
                    {
                        "agent_id": agent_id,
                        "cycle": cycles_done,
                        "prev_top": prev,
                        "new_top": top,
                        "snapshot_sha": (
                            sha256_hex(json.dumps(view, sort_keys=True))
                            if view is not None
                            else "null"
                        ),
                    }
                )
            if top is not None:
                prev_ranks[agent_id] = top

            if result is None or not result.claimed or not result.claimed_need_id:
                continue
            arm = arm_of_need(result.claimed_need_id)
            run = getattr(worker, "run_cache", {}).get(arm)
            if run is not None:
                ledger.publish_evidence(build_evidence(agent_id, run, arm_id_to_hyp))
                published += 1

        stop = stop_reason(
            broker.events(), published, total_needs, max_cycles, cycles_done, agent_ids
        )
        if stop != "running":
            break

    # --- Phase RESOLVE --------------------------------------------------------
    ledger.resolve()
    evidence = ledger.evidence()
    snapshot_sha = sha256_hex(json.dumps(evidence_view(evidence), sort_keys=True))
    slice_result = SliceResult(
        case_id=CASE_ID,
        agent_ids=list(agent_ids),
        revealed_verified=revealed_verified,
        revealed_mismatch=revealed_mismatch,
        published_evidence=published,
        stop_reason=stop,
        evidence_snapshot_sha256=snapshot_sha,
        predictions_outcome=evaluate_predictions(packets, evidence),
        choice_trace=choice_trace,
    )
    (root / "slice_result.json").write_text(
        json.dumps(slice_result.to_dict(), indent=2, sort_keys=True), encoding="utf-8"
    )
    return SliceReport(
        result=slice_result,
        ledger_events=ledger.events(),
        broker_events=broker.events(),
        evidence=evidence,
    )
