"""RepliClaw protocol: claim → blind → commit → reveal → evidence →
follow-up → verdict.

This is the decentralized blind replication/falsification loop. The five
coordination baselines (M5) share the same task plumbing and differ only in
the `Strategy` policy — see strategies.py.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from . import canonical
from . import observability as obs
from . import scienceclaw_adapter as sc
from .evidence import detect_conflicts
from .isolation import ContextEnforcer, PhaseGate
from .models import (
    Claim,
    Commitment,
    Evidence,
    EvidenceRelation,
    FollowUpNeed,
    InvestigatorConfig,
    InvestigatorRole,
    NeedKind,
    ResourceUsage,
    RunMetadata,
    Verdict,
    commit_payload,
)
from .runstore import RevealMismatchError, RunStore
from .verdict import compute_verdict

STRATEGY_REPLICLAW = "repl_claw_blind_commit_reveal"
STRATEGIES = (
    STRATEGY_REPLICLAW,
    "single_agent",
    "fixed_dag",
    "isolated_vote",
    "open_debate",
)


def default_investigators(claim_id: str) -> List[InvestigatorConfig]:
    """Three methodologically distinct, mutually independent investigators."""
    return [
        InvestigatorConfig(
            agent_id="inv-analyst-1",
            role=InvestigatorRole.ANALYST,
            allowed_sources=["bundled_data"],
            seed_note="primary-effect analyst: effect size + significance",
        ),
        InvestigatorConfig(
            agent_id="inv-statistician-1",
            role=InvestigatorRole.STATISTICIAN,
            allowed_sources=["bundled_data"],
            seed_note="statistical auditor: independent re-derivation of tests",
        ),
        InvestigatorConfig(
            agent_id="inv-falsifier-1",
            role=InvestigatorRole.FALSIFIER,
            allowed_sources=["bundled_data", "published_figures"],
            seed_note="falsifier: attacks the claim against raw event data",
        ),
    ]


@dataclass
class ProtocolResult:
    run_id: str
    claim_id: str
    strategy: str
    verdict: Verdict
    evidence: List[Evidence]
    commitments: List[Dict[str, Any]]
    needs: List[Dict[str, Any]]
    run_dir: str
    usage: ResourceUsage
    errors: List[str] = field(default_factory=list)
    # A9.2.2 (C8): the protocol's FULL committed finding dicts, keyed by
    # agent_id. These carry the arm-neutral defect fields that the REVEALED
    # commitment payload (evidence.finding) does not, so the strategy layer can
    # aggregate the repl_claw arm's own diagnosis. Additive/optional: existing
    # consumers that construct ProtocolResult without it are unaffected.
    findings: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def report_dir(self) -> Path:
        return Path(self.run_dir)


class RepliClawProtocol:
    """Runs the blind commit/reveal protocol for one claim.

    investigator_factory: (InvestigatorConfig) -> Investigator
    """

    def __init__(
        self,
        run_root: str | Path,
        investigator_factory: Callable[[InvestigatorConfig], Any],
        strategy: str = STRATEGY_REPLICLAW,
        shared_public_materials: Optional[Dict[str, Any]] = None,
        followup_factory: Optional[Callable[[InvestigatorConfig], Any]] = None,
        max_followup_rounds: int = 1,
        min_independent: int = 3,
    ):
        self.run_root = Path(run_root)
        self.run_root.mkdir(parents=True, exist_ok=True)
        self.store = RunStore(self.run_root)
        self.gate = PhaseGate()
        self.enforcer = ContextEnforcer(self.store, self.gate)
        self.investigator_factory = investigator_factory
        self.followup_factory = followup_factory or investigator_factory
        self.strategy = strategy
        self.shared_public_materials = shared_public_materials or {}
        self.max_followup_rounds = max_followup_rounds
        self.min_independent = min_independent
        self._usage = ResourceUsage()

    # ------------------------------------------------------------------
    def run(
        self,
        claim: Claim,
        task_instructions: str = "",
        investigators: Optional[List[InvestigatorConfig]] = None,
    ) -> ProtocolResult:
        t0 = time.time()
        investigators = investigators or default_investigators(claim.claim_id)
        self._usage = ResourceUsage()
        errors: List[str] = []

        self.store.save_claim(claim)
        run_meta = RunMetadata(
            claim_id=claim.claim_id,
            strategy=self.strategy,
            n_investigators=len(investigators),
            config={
                "min_independent": self.min_independent,
                "shared_public_materials": sorted(self.shared_public_materials.keys()),
                "investigators": [i.agent_id for i in investigators],
            },
        )
        self.store.save_run(run_meta.to_dict())

        # Root OTel span for this run (no-op when no TracerProvider is set).
        # Child investigator spans (started in _run_phases) nest under it so an
        # OTLP consumer (e.g. SimpleAuditStudio) can see the full isolated run.
        with obs.run_span(
            run_id=run_meta.run_id,
            strategy=self.strategy,
            claim_id=claim.claim_id,
            n_investigators=len(investigators),
            task_instructions=task_instructions,
        ) as run_span_obj:
            result = self._run_phases(claim, investigators, run_meta, t0, errors, task_instructions)
            obs.finish_run_span(
                run_span_obj,
                label=result.verdict.label.value,
                confidence=result.verdict.confidence,
                usage=result.usage,
                errors=result.errors,
            )
        return result

    def _run_phases(
        self,
        claim: Claim,
        investigators: List[InvestigatorConfig],
        run_meta: RunMetadata,
        t0: float,
        errors: List[str],
        task_instructions: str = "",
    ) -> ProtocolResult:
        # ---------------- Phase 1: BLIND ----------------
        blind_span = obs.start_span("repliclaw.phase.blind", {obs.PHASE_ATTR: "blind"})
        self.gate.advance("blind")
        self.store.event("phase", phase="blind", n_investigators=len(investigators))
        findings: Dict[str, Dict[str, Any]] = {}
        contexts: Dict[str, Any] = {}
        for cfg in investigators:
            ctx = self.enforcer.build_context(
                claim=claim,
                investigator=cfg,
                task_instructions=task_instructions
                or f"Independently assess whether the claim is supported: {claim.statement}",
                shared_public_materials=self.shared_public_materials,
            )
            contexts[cfg.agent_id] = ctx
            with obs.investigator_span(cfg.agent_id, cfg.role.value) as inv_span:
                try:
                    inv = self.investigator_factory(cfg)
                    finding = inv.run(ctx)
                except Exception as exc:  # noqa: BLE001 - record, don't crash the run
                    errors.append(f"{cfg.agent_id}: {type(exc).__name__}: {exc}")
                    self.store.event("investigator_error", agent_id=cfg.agent_id, error=str(exc))
                    if inv_span is not None:
                        inv_span.set_attribute("error", str(exc))
                    continue
            findings[cfg.agent_id] = finding
            self._account_usage(inv)
        obs.end_span(blind_span)

        if not findings:
            # Total investigator failure (e.g. bad backend wiring) is a hard
            # error: a verdict over zero evidence would silently "succeed".
            self.store.event("phase", phase="aborted", reason="no_investigator_findings")
            raise RuntimeError(
                "all investigators failed: " + " | ".join(errors[:5])
            )
        if len(findings) < self.min_independent:
            errors.append(
                f"only {len(findings)}/{self.min_independent} investigators produced findings"
            )

        # ---------------- Phase 2: COMMIT ----------------
        with obs.phase_span("committed"):
            self.gate.advance("committed")
            self.store.event("phase", phase="committed")
            commitments: Dict[str, Commitment] = {}
            for agent_id, finding in findings.items():
                payload = commit_payload(finding)
                c = Commitment(
                    commitment_id=f"cmt-{agent_id}-{uuid.uuid4().hex[:8]}",
                    claim_id=claim.claim_id,
                    agent_id=agent_id,
                    role=finding.get("role", ""),
                    content=payload,
                    content_hash=canonical.commit_hash(payload),
                )
                self.store.commit(c)
                commitments[agent_id] = c

        # ---------------- Phase 3: REVEAL ----------------
        with obs.phase_span("revealing"):
            self.gate.advance("revealing")
            self.store.event("phase", phase="revealing")
            revealed: Dict[str, Dict[str, Any]] = {}
            for agent_id, c in commitments.items():
                try:
                    res = self.store.verify_reveal(c.commitment_id, c.content)
                    if not res.get("verified"):
                        errors.append(f"{agent_id}: reveal not verified")
                    revealed[agent_id] = c.content
                    self.store.event("reveal_ok", agent_id=agent_id, commitment_id=c.commitment_id)
                except RevealMismatchError as exc:
                    errors.append(f"{agent_id}: reveal mismatch — {exc}")
                    self.store.event("reveal_mismatch", agent_id=agent_id, commitment_id=c.commitment_id)
            self.gate.advance("revealed")

        # ---------------- Phase 4: EVIDENCE GRAPH ----------------
        with obs.phase_span("evidence"):
            evidence: List[Evidence] = []
            conclusions = {a: (v.get("conclusion") or "").lower() for a, v in revealed.items()}
            for agent_id, v in revealed.items():
                rel = self._relation_from_conclusion(conclusions[agent_id])
                ev = Evidence(
                    evidence_id=f"ev-{agent_id}-{uuid.uuid4().hex[:8]}",
                    claim_id=claim.claim_id,
                    agent_id=agent_id,
                    relation=rel,
                    finding=v,
                    commitment_id=commitments[agent_id].commitment_id,
                    executable=bool(v.get("executable", False)),
                    confidence=float(v.get("confidence", 0.5) or 0.5),
                )
                self.store.append_evidence(ev)
                evidence.append(ev)

            conflicts = detect_conflicts(evidence)
            agreement = self._agreement(conclusions)
            self.store.event(
                "agreement_computed",
                agreement=agreement,
                n_conflicts=len(conflicts),
                label=self._agreement_label(agreement),
            )

        # ---------------- Phase 5: EMERGENT FOLLOW-UP ----------------
        with obs.phase_span("followup"):
            self.gate.advance("followup")
            self.store.event("phase", phase="followup")
            needs: List[FollowUpNeed] = []
            if conflicts or agreement["unresolved"] or agreement["label"] == "conflict":
                need = FollowUpNeed(
                    need_id=f"need-{uuid.uuid4().hex[:10]}",
                    claim_id=claim.claim_id,
                    kind=NeedKind.FALSIFICATION if agreement["label"] == "conflict" else NeedKind.REPLICATION,
                    query=self._need_query(claim, conflicts),
                    rationale=(
                        "Investigators disagree / evidence insufficient: an independent "
                        "follow-up analysis is required before a verdict can be trusted."
                    ),
                    triggered_by=[e.evidence_id for e in evidence if e.relation in (
                        EvidenceRelation.SUPPORTS, EvidenceRelation.CONTRADICTS)],
                )
                need.priority = sc.pressure_score(
                    {"artifact_type": need.artifact_type, "query": need.query,
                     "rationale": need.rationale, "created_at": need.created_at},
                    parent_artifact_id="", producer_agent="orchestrator",
                    investigation_id=claim.claim_id,
                )
                self.store.append_need(need)
                needs.append(need)
                followup_ev = self._fulfill_need(claim, need, evidence, revealed, errors)
                if followup_ev is not None:
                    evidence.append(followup_ev)
                    self.store.event("need_fulfilled", need_id=need.need_id,
                                     evidence_id=followup_ev.evidence_id)
                    # Re-score conflicts after follow-up.
                    conflicts = detect_conflicts(evidence)
                else:
                    self.store.event("need_unfulfilled", need_id=need.need_id)
            else:
                self.store.event("no_followup_needed", agreement=agreement)

        # ---------------- Phase 6: VERDICT ----------------
        with obs.phase_span("verdict"):
            self.gate.advance("verdict")
            self.store.event("phase", phase="verdict")
            verdict = compute_verdict(
                claim, evidence,
                conflicts=conflicts,
                independent_count=self._independent_count(evidence),
                followup_evidence=[e for e in evidence if "fulfills need" in (e.notes or "")],
            )
            self.store.save_verdict(verdict)

            run_meta.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            run_meta.usage = self._usage
            self.store.save_run(run_meta.to_dict())
            self._usage.wall_clock_s = time.time() - t0

            # Save artifacts + report + metrics.
            self._save_artifacts(claim, evidence, commitments)
        return ProtocolResult(
            run_id=run_meta.run_id,
            claim_id=claim.claim_id,
            strategy=self.strategy,
            verdict=verdict,
            evidence=evidence,
            commitments=self.store.list_commitments(),
            needs=self.store.needs(),
            run_dir=str(self.run_root),
            usage=self._usage,
            errors=errors,
            findings=dict(findings),  # A9.2.2/C8: full finding dicts (defect fields)
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _relation_from_conclusion(conclusion: str) -> EvidenceRelation:
        c = (conclusion or "").lower()
        if c.startswith("refut") or c.startswith("false"):
            return EvidenceRelation.CONTRADICTS
        if c.startswith("support") or c.startswith("true"):
            return EvidenceRelation.SUPPORTS
        return EvidenceRelation.NEUTRAL

    @staticmethod
    def _agreement(conclusions: Dict[str, str]) -> Dict[str, Any]:
        vals = [v for v in conclusions.values() if v]
        supported = [v for v in vals if v.startswith("support")]
        refuted = [v for v in vals if v.startswith("refut")]
        n = len(vals)
        if not n:
            return {"label": "no_data", "majority": 0.0, "unresolved": True}
        if supported and refuted:
            return {"label": "conflict", "majority": max(len(supported), len(refuted)) / n, "unresolved": True}
        if n and (len(supported) == n or len(refuted) == n):
            return {"label": "agreement", "majority": 1.0, "unresolved": False}
        return {"label": "mixed", "majority": max(len(supported), len(refuted)) / n, "unresolved": True}

    @staticmethod
    def _agreement_label(a: Dict[str, Any]) -> str:
        return a["label"]

    @staticmethod
    def _need_query(claim: Claim, conflicts: List[Dict[str, Any]]) -> str:
        who = ", ".join(sorted({a for c in conflicts for a in c.get("agents", [])}))
        return (
            f"independent re-analysis of claim "
            f"'{claim.statement[:120]}' — investigators [{who}] disagree; "
            "recompute the primary test from raw data with a different method"
        )

    def _fulfill_need(
        self,
        claim: Claim,
        need: FollowUpNeed,
        evidence: List[Evidence],
        revealed: Dict[str, Dict[str, Any]],
        errors: List[str],
    ) -> Optional[Evidence]:
        """An available independent investigator autonomously picks up the need.

        The follow-up investigator sees the CLAIM and the revealed (already
        committed) evidence — but produces a fresh commitment of its own,
        preserving the one-shot commit/reveal guarantee.
        """
        # The follow-up uses a lens matching the need kind so it can actually
        # break the disagreement: a falsification need is attacked with the
        # falsifier lens (recompute from raw data), a replication need is
        # re-derived with the statistician lens.
        followup_role = (
            InvestigatorRole.FALSIFIER if need.kind == NeedKind.FALSIFICATION
            else InvestigatorRole.STATISTICIAN
        )
        cfg = InvestigatorConfig(
            agent_id=f"inv-followup-{need.need_id[-6:]}",
            role=followup_role,
            allowed_sources=(["bundled_data"] if claim.data is not None else []),
            seed_note=f"follow-up: independent re-analysis triggered by {need.kind.value}",
        )
        ctx = self.enforcer.build_context(
            claim=claim,
            investigator=cfg,
            task_instructions=(
                "A follow-up analysis was requested because independent "
                "investigators disagreed. " + need.query
            ),
            shared_public_materials=self.shared_public_materials,
        )
        try:
            with obs.investigator_span(cfg.agent_id, cfg.role.value):
                inv = self.followup_factory(cfg)
                finding = inv.run(ctx)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"followup {cfg.agent_id}: {type(exc).__name__}: {exc}")
            self.store.event("followup_error", agent_id=cfg.agent_id, error=str(exc))
            return None
        self._account_usage(inv)

        payload = commit_payload(finding)
        c = Commitment(
            commitment_id=f"cmt-{cfg.agent_id}-{uuid.uuid4().hex[:8]}",
            claim_id=claim.claim_id,
            agent_id=cfg.agent_id,
            role=finding.get("role", "critic"),
            content=payload,
            content_hash=canonical.commit_hash(payload),
        )
        self.store.commit(c)
        try:
            self.store.verify_reveal(c.commitment_id, c.content)
        except RevealMismatchError as exc:
            errors.append(f"followup reveal mismatch: {exc}")
            return None
        rel = self._relation_from_conclusion((finding.get("conclusion") or "").lower())
        ev = Evidence(
            evidence_id=f"ev-{cfg.agent_id}-{uuid.uuid4().hex[:8]}",
            claim_id=claim.claim_id,
            agent_id=cfg.agent_id,
            relation=rel,
            finding=finding,
            commitment_id=c.commitment_id,
            executable=bool(finding.get("executable", False)),
            confidence=float(finding.get("confidence", 0.5) or 0.5),
            notes=f"fulfills need {need.need_id} ({need.kind.value})",
        )
        self.store.append_evidence(ev)
        return ev

    @staticmethod
    def _independent_count(evidence: List[Evidence]) -> int:
        return len({e.agent_id for e in evidence})

    def _account_usage(self, inv: Any) -> None:
        client = getattr(inv, "client", None)
        if client is not None and hasattr(client, "usage"):
            self._usage.prompt_tokens += client.usage.prompt_tokens
            self._usage.completion_tokens += client.usage.completion_tokens
            self._usage.total_tokens += client.usage.total_tokens
            self._usage.llm_calls += client.usage.llm_calls

    def _save_artifacts(
        self, claim: Claim, evidence: List[Evidence], commitments: Dict[str, Commitment]
    ) -> None:
        """Materialize revealed findings as ScienceClaw artifacts (run-local)."""
        try:
            for ev in evidence:
                store = sc.RunLocalArtifactStore(ev.agent_id, self.run_root)
                parent_ids = []
                # lineage: link follow-ups to the evidence that triggered them
                if "fulfills need" in (ev.notes or ""):
                    parent_ids = [e.evidence_id for e in evidence if e.agent_id != ev.agent_id][:3]
                art = sc.artifact_from_finding(
                    agent_id=ev.agent_id,
                    investigation_id=claim.claim_id,
                    finding=ev.finding,
                    artifact_type="analysis_result",
                    parent_artifact_ids=parent_ids,
                    result_quality="ok" if ev.quality == "ok" else ev.quality,
                )
                store.save(art)
                ev.artifact_ids.append(art.artifact_id)
            self.store.event("artifacts_saved", count=len(evidence),
                             base=str(self.run_root / "artifacts"))
        except Exception as exc:  # noqa: BLE001
            self.store.event("artifact_save_error", error=str(exc))
