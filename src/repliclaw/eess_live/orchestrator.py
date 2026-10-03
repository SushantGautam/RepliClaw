"""Live-LLM EESS orchestrator: the S5 canonical loop, shared by S5/A1/A3.

PREREG-2026-10 §5: the ablations (A1, A3) are "implemented as an option, not
a copy" — this orchestrator is written ONCE against two seams:

* the *escrow* seam (:class:`EscrowedEscrow` for S5/A3, :class:`PassThroughEscrow`
  for A1) — the single-factor "no escrow" change;
* the *policy* seam (``LocalEigPolicy`` for S5/A1, ``RandomPolicy`` for A3) —
  the single-factor "random selection" change.

Every model-reasoning step — the pre-outcome COMMIT and the post-evidence
VERDICT — goes through an LLM client interface (``FakeLLMClient`` offline, a
real ``LLMClient`` in P08b) and is accounted PER CALL against the matched
``BudgetEnvelope``.

Usage-invalidation (judge item 7 / Q13): a call whose reported usage is
absent is NEVER zero-filled. The arm turns a ``usage_present=False`` call
into a run with ``status="invalid_usage"`` (void, excluded from M1).
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..canonical import sha256_hex
from ..comparators.budget import BudgetEnvelope, BudgetOverflow
from ..counterfactual.executor import load_case, load_interventions, run_case
from ..counterfactual.frozen_backend import extract_window_days
from ..escrow import EvidenceObservation, PredictionPacket
from ..models import Claim
from ..needmarket import CostEstimate, Need, NeedBroker, NeedWorker, WorkerCapability
from ..needmarket.policy import ActionPolicy, LocalEigPolicy
from ..slice.derive import ARM_BY_HYP, BASELINE_ARM, derive_discriminability
from ..slice.orchestrate import HYP_BY_AGENT, _now_iso, evidence_view, verify_run
from .accounting import LiveBudgetLedger
from .budget_calls import InvalidUsageError, UsageSnapshot, usage_delta, usage_present, usage_snapshot
from .escrow import LiveEscrow
from .fake import COMMIT_MARKER, VERDICT_MARKER

CASE_ID = "policy_rag_v1"
AGENT_IDS = ("alpha", "beta", "gamma")
LEASE_TTL_S = 60.0
COST_TOKENS_PER_ARM = 500
CAP_BUDGET_TOKENS = 10_000


@dataclass
class LiveRunResult:
    """Outcome of one live-arm run.

    The arm maps this onto the P08 ``final_verdict.json`` (contract §2) and
    the per-call ledger (contract §3). ``choice_trace`` is the arm's local
    need-choice record (the A3 deterministic seed is asserted on it).
    """

    status: str  # completed | aborted_budget | invalid_usage
    verdict: Optional[str]  # supported | refuted | uncertain | None
    defect_class: Optional[str] = None
    target_artifact: Optional[str] = None
    confidence: Optional[float] = None
    hypotheses: List[Dict[str, Any]] = field(default_factory=list)
    agent_verdicts: List[Dict[str, Any]] = field(default_factory=list)
    total_tokens: int = 0
    wall_s: float = 0.0
    n_agents: int = 0
    integrity_rejections: int = 0
    counterfactual_slots_granted: int = 0
    counterfactual_slots_executed: int = 0
    traces: List[Dict[str, Any]] = field(default_factory=list)
    budget_ledger: Dict[str, Any] = field(default_factory=dict)
    choice_trace: List[Dict[str, Any]] = field(default_factory=list)
    usage: Dict[str, Any] = field(default_factory=dict)


def _arm_of_need(need: Need) -> Optional[str]:
    """``need_<arm>_<proposer>`` -> ``<arm>`` (arm ids carry no ``_``)."""
    rest = need.need_id[len("need_") :]
    arm = rest.rsplit("_", 1)[0]
    return arm if arm in ARM_BY_HYP.values() or arm == BASELINE_ARM else None


def _deterministic_obs_id(run: Any) -> str:
    """Observation id derived from content, not uuid4 — identical across
    same-seed reruns (required for A3's seeded random policy)."""
    body = {
        "run_id": run.run_id,
        "arm": run.intervention_id,
        "severity": run.severity,
    }
    return "obs_" + sha256_hex(json.dumps(body, sort_keys=True))[:16]


def _deterministic_packet_id(
    agent_id: str, payload: Dict[str, Any], prior_snapshot: str
) -> str:
    """32-hex uuid4-shaped, content-derived packet id (stable across
    same-seed reruns; the validator requires exactly 32 lowercase hex)."""
    body = {"phase": "COMMIT", "agent_id": agent_id, "payload": payload, "snapshot": prior_snapshot}
    digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).digest()
    b = bytearray(digest[:16])
    b[6] = (b[6] & 0x0F) | 0x40  # version 4
    b[8] = (b[8] & 0x3F) | 0x80  # RFC 4122 variant
    return bytes(b).hex()


def _safe_usage_snapshot(client: Any) -> Any:
    """``usage_snapshot`` that tolerates a client whose ``.usage`` is absent
    (None / not set). An absent usage object must be *recorded and void the
    run* (``usage_present=False``), never zero-filled — so we return a zeroed
    snapshot and let ``usage_present`` classify it as missing."""
    u = getattr(client, "usage", None)
    if u is None:
        return UsageSnapshot()
    return usage_snapshot(client)


def _wall_free_evidence(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Strip wall-clock ``published_at`` so the evidence snapshot the workers
    hash is content-deterministic (mirrors the ledger's snapshot() which
    excludes wall-clock fields by design)."""
    return [{k: v for k, v in e.items() if k != "published_at"} for e in evidence]


def build_evidence(agent_id: str, run: Any) -> EvidenceObservation:
    """The SAME observation schema the offline slice publishes (contract §3)."""
    window = extract_window_days(run.target_output)
    arm_to_hyp = {v: k for k, v in ARM_BY_HYP.items()}
    return EvidenceObservation(
        observation_id=_deterministic_obs_id(run),
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
            "hypothesis": arm_to_hyp.get(run.intervention_id),
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


class LiveEESSOrchestrator:
    """One arm's live S5 lifecycle on a claim, with per-call budget accounting.

    ``escrow`` is the escrow seam; ``policy_factory(agent_id)`` builds each
    agent's ranking policy; ``client_factory(agent_id)`` builds one LLM client
    per agent (fresh, so per-agent usage is exact). ``harness_seed`` seeds the
    A3 :class:`RandomPolicy` and any deterministic tie-breaks (prereg §10.2);
    it is deliberately NOT passed to ``run_case`` (verify_run re-executes at
    seed 0, so the case engine stays pinned).
    """

    def __init__(
        self,
        *,
        claim: Claim,
        out_root: Path,
        escrow: LiveEscrow,
        policy_factory: Callable[[str], ActionPolicy],
        client_factory: Callable[[str], Any],
        envelope: BudgetEnvelope,
        harness_seed: int,
        max_cycles: int = 2,
        cost_tokens_per_arm: int = COST_TOKENS_PER_ARM,
        deadline_s: Optional[float] = None,
        on_event: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        lease_ttl_s: float = LEASE_TTL_S,
    ) -> None:
        self.claim = claim
        self.out_root = Path(out_root)
        self.escrow = escrow
        self.policy_factory = policy_factory
        self.client_factory = client_factory
        self.envelope = envelope
        self.harness_seed = int(harness_seed)
        self.max_cycles = int(max_cycles)
        self.cost_tokens_per_arm = int(cost_tokens_per_arm)
        self.lease_ttl_s = float(lease_ttl_s)
        self.case = load_case(CASE_ID)
        self.interventions = {i.intervention_id: i for i in load_interventions(CASE_ID)}
        self.ledger = LiveBudgetLedger(envelope)
        self.broker = NeedBroker(self.out_root / "needs", lease_ttl_s=self.lease_ttl_s)
        self.run_cache: Dict[str, Any] = {}
        self.choice_trace: List[Dict[str, Any]] = []
        self.traces: List[Dict[str, Any]] = []
        self.start = time.time()
        self.deadline_s = float(deadline_s) if deadline_s is not None else None
        self.on_event = on_event or (lambda _t, _p: None)
        self._seq = 0

    # -- event / accounting helpers ----------------------------------------
    def _emit(self, type_: str, payload: Dict[str, Any], agent_id: Optional[str] = None) -> None:
        self._seq += 1
        self.traces.append(
            {"seq": self._seq, "ts": _now_iso(), "agent_id": agent_id, "type": type_, "payload": payload}
        )
        self.on_event(type_, {"agent_id": agent_id, "type": type_, "payload": payload})

    def _deadline_exceeded(self) -> bool:
        return self.deadline_s is not None and (time.time() - self.start) > self.deadline_s

    def _llm_call(self, agent_id: str, client: Any, prompt: str, purpose: str) -> Dict[str, Any]:
        """One accounted model call (snapshot-delta over the whole
        ``chat_json`` — it may retry once). Raises ``BudgetOverflow`` on an
        envelope breach (after recording the tripping call, never zero-filled)
        or ``InvalidUsageError`` if the endpoint reported no usage (void, not
        zero-filled — judge item 7 / Q13)."""
        t0 = time.monotonic()
        before = _safe_usage_snapshot(client)
        payload = client.chat_json(prompt)
        after = _safe_usage_snapshot(client)
        wall = time.monotonic() - t0
        delta = usage_delta(before, after)
        present = usage_present(delta)

        def _record_tripping() -> None:
            self.ledger.record_overflow_call(
                agent_id,
                delta.prompt_tokens,
                delta.completion_tokens,
                wall,
                purpose=purpose,
                usage_present=present,
                message="envelope exceeded",
            )

        try:
            self.ledger.record_live_call(
                agent_id,
                prompt_tokens=delta.prompt_tokens,
                completion_tokens=delta.completion_tokens,
                wall_s=wall,
                purpose=purpose,
                usage_present=present,
            )
        except BudgetOverflow:
            _record_tripping()  # record the tripping call + overflow event
            raise
        if not present:
            # Judge item 7 / Q13: absent usage is never zero-filled — the call
            # was recorded (with usage_present=False) so the artifact shows
            # WHERE usage went missing, and the run is voided below.
            raise InvalidUsageError(
                f"LLM call by {agent_id} reported no usage fields — "
                "run invalidated (never zero-filled)"
            )
        return payload

    # -- lifecycle ---------------------------------------------------------
    def run(self) -> LiveRunResult:
        """Execute the full lifecycle; always returns a ``LiveRunResult``.

        Budget exhaustion is caught here and reported as ``aborted_budget``
        (the harness — not the model — aborts, prereg §5.2)."""
        status = "completed"
        verdict: Optional[str] = None
        defect_class: Optional[str] = None
        target_artifact: Optional[str] = None
        confidence: Optional[float] = None
        hypotheses: List[Dict[str, Any]] = []
        agent_verdicts: List[Dict[str, Any]] = []
        slots_executed = 0
        total_needs = 0
        packets: Dict[str, PredictionPacket] = {}

        try:
            # ---------------- COMMIT ----------------
            self._emit("phase", {"phase": "COMMIT"})
            self.escrow.open(CASE_ID)
            prior_snapshot = sha256_hex(
                json.dumps(
                    {"phase": "COMMIT", "case": CASE_ID, "claim": self.claim.claim_id},
                    sort_keys=True,
                )
            )
            for agent_id in AGENT_IDS:
                if self._deadline_exceeded():
                    raise BudgetOverflow("wall deadline exceeded during COMMIT")
                client = self.client_factory(agent_id)
                hyp = HYP_BY_AGENT[agent_id]
                prompt = (
                    f"{COMMIT_MARKER}\n"
                    f"AGENT_ID: {agent_id}\n"
                    f"Case: {CASE_ID} (claim {self.claim.claim_id}): "
                    f"{self.claim.statement[:200]}\n"
                    f"Before seeing ANY counterfactual evidence, commit your "
                    f"prediction for hypothesis {hyp}. Respond with JSON containing "
                    f"hypothesis_statement, predicted_outcome, refutation_criterion, "
                    f"competing_explanation, confidence."
                )
                payload = self._llm_call(agent_id, client, prompt, purpose="commit")
                packet = PredictionPacket(
                    packet_id=_deterministic_packet_id(agent_id, payload, prior_snapshot),
                    case_id=CASE_ID,
                    agent_id=agent_id,
                    hypothesis_id=hyp,
                    hypothesis_version=1,
                    hypothesis_statement=str(payload.get("hypothesis_statement") or hyp),
                    intervention_id=ARM_BY_HYP[hyp],
                    predicted_outcome=str(
                        payload.get("predicted_outcome") or "the arm changes the target output"
                    ),
                    refutation_criterion=str(
                        payload.get("refutation_criterion") or "the arm leaves the target unchanged"
                    ),
                    competing_explanation=str(
                        payload.get("competing_explanation") or "a residual confound flips the verdict"
                    ),
                    prior_evidence_snapshot_sha256=prior_snapshot,
                )
                packets[agent_id] = packet
                self.escrow.commit(agent_id, packet)
                self._emit(
                    "commitment",
                    {"agent_id": agent_id, "packet_id": packet.packet_id, "hypothesis": hyp},
                    agent_id=agent_id,
                )
                self._make_need(ARM_BY_HYP[hyp], agent_id)
            self._make_need(BASELINE_ARM, "alpha")
            total_needs = len(self.broker.needs())
            self._emit("needs_published", {"total_needs": total_needs})

            # ---------------- REVEAL ----------------
            self._emit("phase", {"phase": "REVEAL"})
            self.escrow.begin_reveal(CASE_ID)
            for agent_id in AGENT_IDS:
                outcome = self.escrow.reveal(agent_id, packets[agent_id])
                self._emit(
                    "reveal",
                    {
                        "agent_id": agent_id,
                        "packet_id": outcome.packet_id,
                        "status": outcome.status,
                        "integrity_rejected": outcome.integrity_rejected,
                    },
                    agent_id=agent_id,
                )
            if self.escrow.mode == "escrow":
                self.escrow.enter_execute()  # phase gate before publish_evidence

            # ---------------- EXECUTE ----------------
            self._emit("phase", {"phase": "EXECUTE", "max_cycles": self.max_cycles})
            prev_top: Dict[str, Optional[str]] = {}
            for cycle in range(1, self.max_cycles + 1):
                if self._deadline_exceeded():
                    raise BudgetOverflow("wall deadline exceeded during EXECUTE")
                # Stable, wall-clock-free view of everything currently published.
                view = evidence_view(_wall_free_evidence(self.escrow.evidence()))
                for agent_id in AGENT_IDS:
                    if self._deadline_exceeded():
                        raise BudgetOverflow("wall deadline exceeded during EXECUTE")
                    capability = WorkerCapability(
                        agent_id=agent_id,
                        producible_types=["counterfactual-arm"],
                        method_family="counterfactual-arm",
                        model=self.case.target_model_id,
                        budget_tokens=CAP_BUDGET_TOKENS,
                    )
                    policy = self.policy_factory(agent_id)
                    # LocalEigPolicy (S5/A1) is evidence-directed; A3's
                    # RandomPolicy has no discriminability (single factor).
                    if isinstance(policy, LocalEigPolicy):
                        arms = {n.need_id: a for n in self.broker.open_needs(exclude_agent=agent_id)
                                if (a := _arm_of_need(n)) is not None}
                        policy.set_discriminability(
                            derive_discriminability(
                                agent_id, HYP_BY_AGENT[agent_id], list(arms), view, arms
                            )
                        )
                    worker = NeedWorker(
                        capability,
                        self.broker,
                        policy,
                        execute=self._execute,
                        rng_seed=self.harness_seed,
                    )
                    result = worker.cycle(view)
                    if result is None:
                        continue
                    top = result.ranked[0].need_id if result.ranked else None
                    self.choice_trace.append(
                        {
                            "agent_id": agent_id,
                            "cycle": cycle,
                            "ranked": [r.need_id for r in result.ranked],
                            "top": top,
                            "claimed_need_id": result.claimed_need_id,
                            "claimed": result.claimed,
                            "fulfilled": result.fulfilled,
                            "abstained": result.abstained,
                            "abstain_reason": result.abstain_reason,
                        }
                    )
                    self._emit(
                        "choice",
                        {
                            "cycle": cycle,
                            "ranked": [r.need_id for r in result.ranked],
                            "claimed_need_id": result.claimed_need_id,
                            "claimed": result.claimed,
                            "abstained": result.abstained,
                        },
                        agent_id=agent_id,
                    )
                    if top is not None:
                        prev = prev_top.get(agent_id)
                        if prev is not None and top != prev:
                            self._emit(
                                "choice_changed",
                                {"agent_id": agent_id, "prev_top": prev, "new_top": top},
                                agent_id=agent_id,
                            )
                        prev_top[agent_id] = top
                    if result.claimed and result.claimed_need_id is not None:
                        slots_executed += 1

            # ---------------- RESOLVE ----------------
            self._emit("phase", {"phase": "RESOLVE"})
            if self.escrow.mode == "escrow":
                self.escrow.resolve()

            # ---------------- post-evidence verdicts (LLM) ----------------
            outcomes: Dict[str, str] = {}
            for agent_id in AGENT_IDS:
                client = self.client_factory(agent_id)
                packet = packets[agent_id]
                prompt = (
                    f"{VERDICT_MARKER}\n"
                    f"AGENT_ID: {agent_id}\n"
                    f"Evidence has been observed for hypothesis "
                    f"{packet.hypothesis_id}. Your pre-outcome commitment was: "
                    f"{packet.predicted_outcome!r}. Respond with JSON containing "
                    f"conclusion (supported|refuted|uncertain), confidence, "
                    f"defect_class, target_artifact, statement."
                )
                payload = self._llm_call(agent_id, client, prompt, purpose="verdict")
                conclusion = str(payload.get("conclusion", "uncertain"))
                if conclusion not in ("supported", "refuted", "uncertain"):
                    conclusion = "uncertain"
                outcomes[agent_id] = conclusion
                if not defect_class and payload.get("defect_class"):
                    defect_class = str(payload["defect_class"])
                if not target_artifact and payload.get("target_artifact"):
                    target_artifact = str(payload["target_artifact"])
                agent_verdicts.append(
                    {
                        "agent_id": agent_id,
                        "verdict": conclusion,
                        "confidence": float(payload.get("confidence", 0.0)),
                    }
                )
                self._emit(
                    "verdict",
                    {"agent_id": agent_id, "conclusion": conclusion},
                    agent_id=agent_id,
                )

            # Aggregate: plurality over agent verdicts (tie/none -> uncertain).
            tally: Dict[str, int] = {}
            for v in outcomes.values():
                tally[v] = tally.get(v, 0) + 1
            if tally:
                best = max(sorted(tally), key=lambda k: tally[k])
                verdict = best if tally[best] * 2 > len(outcomes) else "uncertain"
            else:
                verdict = "uncertain"
            confidence = (
                sum(a["confidence"] for a in agent_verdicts) / len(agent_verdicts)
                if agent_verdicts
                else None
            )

            # Hypotheses: one per committed agent, outcome driven by the
            # measured counterfactual effect (preregistered in derive.py).
            hypotheses = [
                {
                    "id": HYP_BY_AGENT[aid],
                    "statement": packets[aid].hypothesis_statement,
                    "falsifiable": bool(packets[aid].refutation_criterion),
                    "attempted_falsification": ARM_BY_HYP[HYP_BY_AGENT[aid]] in self.run_cache,
                    "outcome": "not_run",
                    "counterfactual_slot": ARM_BY_HYP[HYP_BY_AGENT[aid]],
                }
                for aid in AGENT_IDS
            ]
            arm_to_hyp = {v: k for k, v in ARM_BY_HYP.items()}
            for arm, run in self.run_cache.items():
                if arm == BASELINE_ARM:
                    continue
                hyp_id = arm_to_hyp.get(arm)
                for h in hypotheses:
                    if h["id"] == hyp_id:
                        h["outcome"] = "refuted" if run.severity == "no_defect" else "supported"
        except BudgetOverflow as exc:
            status = "aborted_budget"
            # The tripping call + one budget_exhausted event were already
            # recorded in _llm_call; only append a second event if the
            # abort came from a deadline/other path that bypassed a call.
            if not any(e.get("kind") == "budget_exhausted" for e in self.ledger.overflow_events):
                self.ledger.record_overflow(str(exc), kind="budget_exhausted")
            self._emit("budget_abort", {"message": str(exc), "kind": "budget_exhausted"})
        except InvalidUsageError as exc:
            # Judge item 7 / Q13: the offending call is already in the ledger
            # with usage_present=False; mark the run void (never zero-filled).
            status = "invalid_usage"
            self.ledger.record_overflow(str(exc), kind="invalid_usage")
            self._emit("usage_invalid", {"message": str(exc), "kind": "invalid_usage"})

        wall = time.time() - self.start
        completed = status == "completed"
        return LiveRunResult(
            status=status,
            verdict=verdict if completed else None,
            defect_class=defect_class if completed else None,
            target_artifact=target_artifact if completed else None,
            confidence=confidence if completed else None,
            hypotheses=hypotheses,
            agent_verdicts=agent_verdicts,
            total_tokens=self.ledger.total_tokens,
            wall_s=wall,
            n_agents=self.ledger.distinct_agents,
            integrity_rejections=self.escrow.integrity_rejections,
            counterfactual_slots_granted=total_needs,
            counterfactual_slots_executed=slots_executed,
            traces=self.traces,
            budget_ledger=self.ledger.to_contract_dict(),
            choice_trace=self.choice_trace,
            usage=self._usage_block(),
        )

    # -- internals ---------------------------------------------------------
    def _make_need(self, arm: str, agent_id: str) -> None:
        self.broker.publish(
            Need(
                need_id=f"need_{arm}_{agent_id}",
                case_id=CASE_ID,
                title=f"Run counterfactual arm {arm}",
                description=(
                    f"Execute the {arm} intervention arm on case {CASE_ID} via "
                    f"the P02 SimpleAudit executor and publish a verified "
                    f"evidence observation. (proposed by {agent_id})"
                ),
                proposer_id=agent_id,
                proposed_at=_now_iso(),
                required_capability="counterfactual-arm",
                cost_estimate=CostEstimate(tokens=self.cost_tokens_per_arm, wall_s=5.0),
            )
        )

    def _execute(self, need: Need) -> Dict[str, Any]:
        """Run + verify the counterfactual arm a need points at.

        Returns the worker contract ``{"artifact_id", "verified", ...}``; the
        broker marks a need done only when ``verified`` is True (P02 replay
        semantics — never self-attestation)."""
        arm = _arm_of_need(need)
        if arm is None:
            return {"artifact_id": "", "verified": False, "intervention_id": need.need_id}
        intervention = self.interventions.get(arm)
        if intervention is None:
            return {"artifact_id": "", "verified": False, "intervention_id": arm}
        cached = self.run_cache.get(arm)
        if cached is not None:
            return {
                "artifact_id": cached.run_id,
                "verified": True,
                "intervention_id": arm,
            }
        # verify_run re-executes at seed 0; keep the run's seed at 0 so the
        # persisted arm-file hashes reproduce exactly. The harness_seed is NOT
        # a case-engine seed (prereg §10.2: it seeds A3's ranking only).
        run = run_case(self.case, intervention, seed=0, out_root=self.out_root / "runs" / arm)
        verified = verify_run(self.case, intervention, run)
        if not verified:
            self._emit("verification_failed", {"arm": arm, "reason": "hash mismatch"})
            return {"artifact_id": "", "verified": False, "intervention_id": arm}
        self.run_cache[arm] = run
        obs = build_evidence(need.proposer_id, run)
        self.escrow.publish_evidence(obs)
        self._emit(
            "evidence_published",
            {"arm": arm, "run_id": run.run_id, "observation_id": obs.observation_id},
            agent_id=need.proposer_id,
        )
        return {"artifact_id": run.run_id, "verified": True, "intervention_id": arm}

    def _usage_block(self) -> Dict[str, Any]:
        """Per-call usage presence + totals (contract §3; missing => void)."""
        calls = [
            {
                "seq": c.seq,
                "agent_id": c.agent_id,
                "prompt_tokens": c.prompt_tokens,
                "completion_tokens": c.completion_tokens,
                "total_tokens": c.total_tokens,
                "wall_s": round(c.wall_s, 6),
                "usage_present": c.usage_present,
            }
            for c in self.ledger.calls
        ]
        return {
            "calls": calls,
            "totals": {
                "prompt_tokens": sum(c.prompt_tokens for c in self.ledger.calls),
                "completion_tokens": sum(c.completion_tokens for c in self.ledger.calls),
                "total_tokens": sum(c.total_tokens for c in self.ledger.calls),
                "llm_calls": len(self.ledger.calls),
            },
            "usage_present_all_calls": all(c.usage_present for c in self.ledger.calls)
            if self.ledger.calls
            else False,
        }


__all__ = [
    "CASE_ID",
    "AGENT_IDS",
    "LiveEESSOrchestrator",
    "LiveRunResult",
    "build_evidence",
]
