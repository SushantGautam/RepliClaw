"""Five coordination baselines (M5 / AC09) over ONE shared task interface.

The scientific task (an investigator producing a finding from a sealed
context) and the evidence/verdict engine are IDENTICAL across all baselines
(DECISIONS.md: baselines differ only in coordination regime, not code). Each
baseline is a different COORDINATION POLICY:

1. `single_agent`   — one strong agent, no peers, no aggregation.
2. `fixed_dag`      — fixed central DAG: research → analysis → critic/judge,
                      each stage may read the previous stage's output.
3. `isolated_vote`  — N independent isolated agents + simple majority-vote
                      aggregation (no follow-up, no adjudication).
4. `open_debate`    — N agents sharing context, each seeing prior agents'
                      revealed conclusions (correlated by construction).
5. `repl_claw`      — blind commit/reveal + evidence-driven decentralized
                      follow-up (the full protocol; wraps RepliClawProtocol).

All return a `StrategyResult` with the same fields so the benchmark (M6) can
compare correctness, cost, latency, error-correlation, and recovery on equal
footing. `usage`/`wall_clock_s` are logged for every strategy (AC11).
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from . import scienceclaw_adapter as sc
from .evidence import detect_conflicts
from .isolation import ContextEnforcer, PhaseGate
from .models import (
    Claim,
    Commitment,
    Evidence,
    InvestigatorConfig,
    InvestigatorRole,
    ResourceUsage,
    Verdict,
)
from . import canonical
from .protocol import RepliClawProtocol
from .runstore import RunStore
from .verdict import compute_verdict


# ---------------------------------------------------------------------------
# Shared result schema (identical across all baselines)
# ---------------------------------------------------------------------------
@dataclass
class StrategyResult:
    strategy: str
    claim_id: str
    verdict: Verdict
    evidence: List[Evidence]
    commitments: List[Dict[str, Any]]
    needs: List[Dict[str, Any]]
    usage: ResourceUsage
    wall_clock_s: float
    agreement: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "claim_id": self.claim_id,
            "verdict": self.verdict.to_dict(),
            "n_evidence": len(self.evidence),
            "n_agents": len({e.agent_id for e in self.evidence}),
            "n_needs": len(self.needs),
            "agreement": self.agreement,
            "usage": self.usage.to_dict(),
            "wall_clock_s": round(self.wall_clock_s, 4),
            "errors": self.errors,
        }


def _new_enforcer(tmp: Path):
    store = RunStore(tmp)
    gate = PhaseGate()
    return store, gate, ContextEnforcer(store, gate)


def _ev(agent_id, finding, commitment_id, claim_id) -> Evidence:
    rel_map = {
        "supported": "supports",
        "refuted": "contradicts",
        "uncertain": "neutral",
    }
    conclusion = (finding.get("conclusion") or "").lower()
    rel = rel_map.get(conclusion, "neutral")
    from .models import EvidenceRelation

    return Evidence(
        evidence_id=f"ev-{agent_id}-{uuid.uuid4().hex[:8]}",
        claim_id=claim_id,
        agent_id=agent_id,
        relation=EvidenceRelation(rel),
        finding=finding,
        commitment_id=commitment_id,
        executable=bool(finding.get("executable", False)),
        confidence=float(finding.get("confidence", 0.5) or 0.5),
    )


def _commit(store, agent_id, role, finding, claim_id) -> Commitment:
    payload = {"conclusion": finding.get("conclusion"), "statement": finding.get("statement", ""),
               "plan": finding.get("plan", ""), "evidence": finding.get("evidence", {}),
               "confidence": float(finding.get("confidence", 0.5) or 0.5),
               "executable": bool(finding.get("executable", False))}
    c = Commitment(
        commitment_id=f"cmt-{agent_id}-{uuid.uuid4().hex[:6]}",
        claim_id=claim_id, agent_id=agent_id, role=role,
        content=payload, content_hash=canonical.commit_hash(payload),
    )
    store.commit(c)
    return c


def _finalize(strategy, claim, store, evidence, needs, usage, t0, errors, agreement):
    conflicts = detect_conflicts(evidence)
    verdict = compute_verdict(
        claim, evidence, conflicts=conflicts,
        independent_count=len({e.agent_id for e in evidence}) or 1,
    )
    store.save_verdict(verdict)
    for e in evidence:
        store.append_evidence(e)
    for n in needs:
        store.append_need(n)
    return StrategyResult(
        strategy=strategy, claim_id=claim.claim_id, verdict=verdict,
        evidence=evidence, commitments=store.list_commitments(), needs=needs,
        usage=usage, wall_clock_s=time.time() - t0, agreement=agreement, errors=errors,
    )


# ---------------------------------------------------------------------------
# Baseline 1: single strong agent
# ---------------------------------------------------------------------------
def run_single_agent(claim, factory, tmp: Path) -> StrategyResult:
    t0 = time.time()
    tmp = Path(tmp)
    store, gate, enf = _new_enforcer(tmp / "run")
    usage = ResourceUsage()
    errors: List[str] = []
    cfg = InvestigatorConfig(agent_id="single-agent", role=InvestigatorRole.ANALYST,
                             allowed_sources=["bundled_data"], seed_note="single strong agent")
    ctx = enf.build_context(claim, cfg, task_instructions="Assess the claim independently.")
    inv = factory(cfg)
    finding = inv.run(ctx)
    c = _commit(store, cfg.agent_id, cfg.role.value, finding, claim.claim_id)
    evidence = [_ev(cfg.agent_id, finding, c.commitment_id, claim.claim_id)]
    usage = _usage(inv)
    return _finalize("single_agent", claim, store, evidence, [], usage, t0, errors,
                     {"label": "single", "majority": 1.0, "unresolved": False})


# ---------------------------------------------------------------------------
# Baseline 2: fixed central DAG (research -> analysis -> critic/judge)
# ---------------------------------------------------------------------------
DAG_ROLES = [
    ("dag-research", InvestigatorRole.ANALYST, "research stage: frame the analysis"),
    ("dag-analysis", InvestigatorRole.STATISTICIAN, "analysis stage: run the primary test"),
    ("dag-critic", InvestigatorRole.CRITIC, "critic/judge stage: adjudicate the result"),
]


def run_fixed_dag(claim, factory, tmp: Path) -> StrategyResult:
    t0 = time.time()
    tmp = Path(tmp)
    store, gate, enf = _new_enforcer(tmp / "run")
    usage = ResourceUsage()
    errors: List[str] = []
    evidence: List[Evidence] = []
    prior: List[Dict[str, Any]] = []
    # Fixed DAG: each stage sees the previous stage's output (correlated chain).
    for i, (agent_id, role, note) in enumerate(DAG_ROLES):
        cfg = InvestigatorConfig(agent_id=agent_id, role=role,
                                 allowed_sources=["bundled_data"], seed_note=note)
        ctx = enf.build_context(claim, cfg, task_instructions=f"{note} "
                              "You are stage " + str(i + 1) + " of a fixed pipeline.")
        # Fixed DAG shares prior stage outputs with the next stage.
        if prior:
            ctx.revealed_materials = {p["agent_id"]: p["finding"] for p in prior}
        inv = factory(cfg)
        finding = inv.run(ctx)
        c = _commit(store, agent_id, role.value, finding, claim.claim_id)
        # Only the FINAL stage (critic/judge) is the DAG's verdict evidence;
        # earlier stages are supporting context (neutral lineage).
        is_final = i == len(DAG_ROLES) - 1
        ev = _ev(agent_id, finding, c.commitment_id, claim.claim_id)
        if not is_final:
            from .models import EvidenceRelation
            ev.relation = EvidenceRelation.NEUTRAL
            ev.notes = "fixed-dag intermediate stage (context only)"
        evidence.append(ev)
        prior.append({"agent_id": agent_id, "finding": finding})
        usage = _combine(usage, _usage(inv))
    return _finalize("fixed_dag", claim, store, evidence, [], usage, t0, errors,
                     {"label": "fixed_dag", "majority": 1.0, "unresolved": False})


# ---------------------------------------------------------------------------
# Baseline 3: isolated independent agents + simple vote aggregation
# ---------------------------------------------------------------------------
def _three(claim_id):
    from .protocol import default_investigators
    return default_investigators(claim_id)


def run_isolated_vote(claim, factory, tmp: Path) -> StrategyResult:
    t0 = time.time()
    tmp = Path(tmp)
    store, gate, enf = _new_enforcer(tmp / "run")
    usage = ResourceUsage()
    errors: List[str] = []
    evidence: List[Evidence] = []
    configs = _three(claim.claim_id)
    for cfg in configs:  # fully isolated: each sees ONLY the claim
        ctx = enf.build_context(claim, cfg, task_instructions="Assess the claim independently.")
        inv = factory(cfg)
        finding = inv.run(ctx)
        c = _commit(store, cfg.agent_id, cfg.role.value, finding, claim.claim_id)
        evidence.append(_ev(cfg.agent_id, finding, c.commitment_id, claim.claim_id))
        usage = _combine(usage, _usage(inv))
    # Simple vote aggregation (surfaced, NOT the verdict rule).
    from .protocol import RepliClawProtocol
    conclusions = {a: (v.get("conclusion") or "").lower() for a, v in
                   ((e.agent_id, e.finding) for e in evidence)}
    agreement = RepliClawProtocol._agreement(conclusions)
    store.event("vote_aggregated", agreement=agreement)
    # isolated_vote has NO follow-up/adjudication: a real conflict stays
    # INCONCLUSIVE (this is the point of the comparison).
    return _finalize("isolated_vote", claim, store, evidence, [], usage, t0, errors, agreement)


# ---------------------------------------------------------------------------
# Baseline 4: open shared-context multi-agent debate
# ---------------------------------------------------------------------------
def run_open_debate(claim, factory, tmp: Path) -> StrategyResult:
    t0 = time.time()
    tmp = Path(tmp)
    store, gate, enf = _new_enforcer(tmp / "run")
    usage = ResourceUsage()
    errors: List[str] = []
    evidence: List[Evidence] = []
    revealed: Dict[str, Dict[str, Any]] = {}
    configs = _three(claim.claim_id)
    for cfg in configs:  # each sees ALL prior agents' conclusions (shared)
        ctx = enf.build_context(claim, cfg, task_instructions="Assess the claim.")
        if revealed:
            ctx.revealed_materials = dict(revealed)
        inv = factory(cfg)
        finding = inv.run(ctx)
        c = _commit(store, cfg.agent_id, cfg.role.value, finding, claim.claim_id)
        revealed[cfg.agent_id] = finding
        evidence.append(_ev(cfg.agent_id, finding, c.commitment_id, claim.claim_id))
        usage = _combine(usage, _usage(inv))
    from .protocol import RepliClawProtocol
    conclusions = {e.agent_id: (e.finding.get("conclusion") or "").lower() for e in evidence}
    agreement = RepliClawProtocol._agreement(conclusions)
    return _finalize("open_debate", claim, store, evidence, [], usage, t0, errors, agreement)


# ---------------------------------------------------------------------------
# Baseline 5: RepliClaw (full protocol)
# ---------------------------------------------------------------------------
def run_repl_claw(claim, factory, tmp: Path) -> StrategyResult:
    t0 = time.time()
    tmp = Path(tmp)
    proto = RepliClawProtocol(run_root=tmp / "run", investigator_factory=factory,
                              min_independent=3)
    res = proto.run(claim)
    from .protocol import RepliClawProtocol as _P
    agreement = {}
    return StrategyResult(
        strategy="repl_claw", claim_id=claim.claim_id, verdict=res.verdict,
        evidence=res.evidence, commitments=res.commitments, needs=res.needs,
        usage=res.usage, wall_clock_s=res.usage.wall_clock_s or (time.time() - t0),
        agreement=agreement, errors=res.errors,
    )


def _usage(inv) -> ResourceUsage:
    client = getattr(inv, "client", None)
    u = ResourceUsage()
    if client is not None and hasattr(client, "usage"):
        u.prompt_tokens += client.usage.prompt_tokens
        u.completion_tokens += client.usage.completion_tokens
        u.total_tokens += client.usage.total_tokens
        u.llm_calls += client.usage.llm_calls
    return u


def _combine(a: ResourceUsage, b: ResourceUsage) -> ResourceUsage:
    a.prompt_tokens += b.prompt_tokens
    a.completion_tokens += b.completion_tokens
    a.total_tokens += b.total_tokens
    a.llm_calls += b.llm_calls
    a.tool_calls += b.tool_calls
    return a


# ---------------------------------------------------------------------------
# Runner registry
# ---------------------------------------------------------------------------
STRATEGY_RUNNERS = {
    "single_agent": run_single_agent,
    "fixed_dag": run_fixed_dag,
    "isolated_vote": run_isolated_vote,
    "open_debate": run_open_debate,
    "repl_claw": run_repl_claw,
}


def run_strategy(
    strategy: str,
    claim: Claim,
    investigator_factory: Callable[[InvestigatorConfig], Any],
    run_dir: str | Path,
) -> StrategyResult:
    if strategy not in STRATEGY_RUNNERS:
        raise ValueError(f"unknown strategy {strategy!r}; choices={list(STRATEGY_RUNNERS)}")
    return STRATEGY_RUNNERS[strategy](claim, investigator_factory, Path(run_dir))
