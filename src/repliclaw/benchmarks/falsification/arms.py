"""The four matched arms for the falsification comparison.

All arms are driven by REAL LLM calls (``LLMClient``) under the SAME matched
per-claim envelope (see :mod:`.config`) and over the SAME evidence union:

* ``escrowed_independent`` (treatment) — N=4 :class:`PartitionedInvestigator`s,
  one per source, each seeing ONLY its own partition, each sealing a per-claim
  verdict via escrow BEFORE any peer is seen, then reveal + majority aggregate.
* ``open_sharing`` — N=4 investigators that see ALL evidence, form an initial
  verdict, SHARE those verdicts, then finalize (the herding-risk arm).
* ``central_adaptive`` — ONE strong central manager that sees ALL evidence and
  adapts (multiple bounded tool calls / re-checks).
* ``single_investigator`` — ONE investigator that sees ALL evidence, single pass.

No arm receives secret extra evidence; the escrowed arm's partitions exactly
cover the union the pooled arms see. Every arm's LLM activity is captured in
auditable receipts.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from repliclaw.benchmarks.adversarial_audit import data as aa_data
from repliclaw.benchmarks.indepinfo import (
    InvestigatorConfig,
    InvestigatorRunError,
    PartitionedInvestigator,
    PartitionVault,
    run_case,
)
from repliclaw.escrow import EscrowLedger
from repliclaw.investigators import LLMClient

from .config import MatchedCaps
from .evidence import all_artifacts, build_evidence, pooled_evidence_block
from .pooled import PooledInvestigator, PooledRunError

ARM_NAMES = ("escrowed_independent", "open_sharing", "central_adaptive", "single_investigator")

ClientFactory = Callable[[str], LLMClient]

_VERDICT_RE = re.compile(r"VERDICT:\s*(TRUE|FALSE|ABSTAIN)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# result container
# ---------------------------------------------------------------------------
@dataclass
class ArmResult:
    """The outcome of one arm on one claim (auditable + scoreable)."""

    arm: str
    claim_id: str
    team_verdict: Optional[str]  # the arm's final conclusion (TRUE/FALSE/ABSTAIN)
    individual_verdicts: Dict[str, Optional[str]] = field(default_factory=dict)
    receipts: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    total_tokens: int = 0
    total_llm_calls: int = 0
    total_tool_calls: int = 0
    total_wall_s: float = 0.0
    model_reported: Optional[str] = None
    status: str = "completed"  # completed | failed
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "arm": self.arm,
            "claim_id": self.claim_id,
            "team_verdict": self.team_verdict,
            "individual_verdicts": self.individual_verdicts,
            "total_tokens": self.total_tokens,
            "total_llm_calls": self.total_llm_calls,
            "total_tool_calls": self.total_tool_calls,
            "total_wall_s": self.total_wall_s,
            "model_reported": self.model_reported,
            "status": self.status,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------
def parse_verdict_from_statement(text: Optional[str]) -> Optional[str]:
    """Extract a TRUE/FALSE/ABSTAIN verdict from an escrowed hypothesis_statement."""
    if not text:
        return None
    m = _VERDICT_RE.search(text)
    if m:
        return m.group(1).upper()
    up = text.upper()
    for v in ("ABSTAIN", "TRUE", "FALSE"):  # ABSTAIN first (contains no other)
        if v in up:
            return v
    return None


def majority(verdicts: Dict[str, Optional[str]]) -> Optional[str]:
    """Majority over the team's verdicts; a tie or no votes -> ABSTAIN."""
    votes = [v for v in verdicts.values() if v is not None]
    if not votes:
        return "ABSTAIN"
    top, n = Counter(votes).most_common(1)[0]
    return top if n > len(verdicts) / 2 else "ABSTAIN"


def _persist_receipts(artifacts_dir: Path, arm: str, claim_id: str, receipts: Dict[str, Dict[str, Any]]) -> None:
    d = Path(artifacts_dir) / claim_id / arm
    d.mkdir(parents=True, exist_ok=True)
    with (d / "receipts.jsonl").open("w", encoding="utf-8") as f:
        for agent_id in sorted(receipts):
            f.write(json.dumps(receipts[agent_id], sort_keys=True) + "\n")


def _load_persisted_receipts(artifacts_dir: Path, claim_id: str, arm: str) -> Dict[str, Dict[str, Any]]:
    path = Path(artifacts_dir) / claim_id / arm / "receipts.jsonl"
    if not path.exists():
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            obj = json.loads(ln)
            out[obj["agent_id"]] = obj
    return out


def _tally(receipts: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "total_tokens": sum(int(r.get("total_tokens", 0)) for r in receipts.values()),
        "total_llm_calls": sum(int(r.get("num_llm_calls", 0)) for r in receipts.values()),
        "total_tool_calls": sum(int(r.get("num_tool_calls", 0)) for r in receipts.values()),
        "total_wall_s": round(sum(float(r.get("wall_s", 0.0)) for r in receipts.values()), 4),
        "model_reported": next((r.get("model_reported") for r in receipts.values() if r.get("model_reported")), None),
    }


# ---------------------------------------------------------------------------
# arm 1: escrowed_independent (treatment)
# ---------------------------------------------------------------------------
def run_escrowed(
    claim_id: str, client_factory: ClientFactory, caps: MatchedCaps, artifacts_dir: Path
) -> ArmResult:
    evidence = build_evidence(claim_id)
    ledger_root = Path(artifacts_dir) / claim_id / "escrowed_independent" / "ledger"
    ledger = EscrowLedger(ledger_root, worker_id="falsification")
    vault = PartitionVault(evidence, ledger, claim_id)

    investigators: List[PartitionedInvestigator] = []
    for source_id in aa_data.source_ids():
        agent_id = f"escrowed-{source_id}"
        view = vault.view_for(agent_id, source_id)
        client = client_factory(agent_id)
        inv = PartitionedInvestigator(view, client, InvestigatorConfig(**caps.team_investigator_caps()))
        investigators.append(inv)

    arm_dir = Path(artifacts_dir) / claim_id / "escrowed_independent"
    status = "completed"
    error: Optional[str] = None
    try:
        run_case(investigators, ledger, claim_id, arm_dir)
    except InvestigatorRunError as e:
        status = "failed"
        error = str(e)

    # Uniformly read the persisted receipts (run_case persists even on failure).
    receipts = _load_persisted_receipts(artifacts_dir, claim_id, "escrowed_independent")
    individual = {
        agent_id: parse_verdict_from_statement((r.get("packet") or {}).get("hypothesis_statement"))
        for agent_id, r in receipts.items()
    }
    tally = _tally(receipts)
    return ArmResult(
        arm="escrowed_independent",
        claim_id=claim_id,
        team_verdict=majority(individual),
        individual_verdicts=individual,
        receipts=receipts,
        status=status,
        error=error,
        **tally,
    )


# ---------------------------------------------------------------------------
# pooled-arm system prompts
# ---------------------------------------------------------------------------
_TOOL_MENU = (
    'To call a tool: {"action": "tool_call", "tool": "<name>", "args": {...}}\n'
    "Available tools (they operate on the full evidence union):\n"
    '  - "list_artifacts": args {} — list all artifacts (index, id, source, title)\n'
    '  - "get_artifact": {"index": <int>} — fetch one full artifact by index\n'
    '  - "search_artifacts": {"query": "<substring>"} — case-insensitive search\n'
    '  - "source_info": {} — list the evidence sources\n'
)
_TRUTH_RULE = (
    "A claim is TRUE only if the evidence supports it exactly as worded; a "
    "materially different magnitude, or a confounded association presented as "
    "causal, makes it FALSE."
)
_COMMIT = (
    'Commit: {"action": "commit", "verdict": "TRUE|FALSE|ABSTAIN", '
    '"reasoning": "<concise, evidence-grounded justification>"}'
)


def _open_sharing_system_prompt(claim_id: str, phase: str) -> str:
    block = pooled_evidence_block(claim_id)
    if phase == "initial":
        lead = (
            "You are one of four independent auditors reviewing a research claim. "
            "You have access to ALL evidence artifacts (all sources). Weigh each "
            "artifact's methodology (validation status, sample size, confidence "
            "intervals, confounders, allocation) before trusting its headline number. "
            "Form your INITIAL verdict now; you will later see the other auditors' "
            "initial verdicts and finalize."
        )
    else:
        lead = (
            "You are one of four independent auditors reviewing a research claim. "
            "You have access to ALL evidence artifacts (all sources) and you already "
            "formed an initial verdict. You are now shown the OTHER auditors' initial "
            "verdicts. Reconsider in light of the shared conclusions, but do NOT "
            "simply herd: if your evidence-based reasoning is sound, hold your verdict."
        )
    return (
        f"{lead}\n\n{block}\n\n"
        "Respond with EXACTLY ONE JSON object per turn — no prose outside the JSON.\n"
        f"{_TOOL_MENU}\n{_TRUTH_RULE}\n{_COMMIT}"
    )


def _central_system_prompt(claim_id: str) -> str:
    block = pooled_evidence_block(claim_id)
    return (
        "You are a strong central audit manager with access to ALL evidence "
        "artifacts (all sources). Reach the correct TRUE/FALSE conclusion by "
        "thorough, adaptive investigation: examine the relevant artifacts, "
        "cross-reference across sources, weigh methodology (validation status, "
        "sample size, confidence intervals, confounders, allocation factors), "
        "reconcile contradictions, and re-check your reasoning before committing.\n\n"
        f"{block}\n\n"
        "Respond with EXACTLY ONE JSON object per turn — no prose outside the JSON.\n"
        f"{_TOOL_MENU}\nYou may make multiple tool calls and re-check. When confident, "
        f"{_TRUTH_RULE}\n{_COMMIT}"
    )


def _single_system_prompt(claim_id: str) -> str:
    block = pooled_evidence_block(claim_id)
    return (
        "You are a single auditor with access to ALL evidence artifacts (all "
        "sources). Produce your TRUE/FALSE conclusion in a single pass: you may "
        "make a few tool calls to verify key artifacts, but aim to conclude "
        "directly from the evidence block.\n\n"
        f"{block}\n\n"
        "Respond with EXACTLY ONE JSON object per turn — no prose outside the JSON.\n"
        f"{_TOOL_MENU}\n{_TRUTH_RULE}\n{_COMMIT}"
    )


def _run_pooled_single(
    claim_id: str,
    arm: str,
    agent_id: str,
    system_prompt: str,
    client_factory: ClientFactory,
    caps: MatchedCaps,
    artifacts_dir: Path,
) -> ArmResult:
    client = client_factory(agent_id)
    inv = PooledInvestigator(
        client, agent_id, claim_id, arm, all_artifacts(), system_prompt, caps.single_agent_caps()
    )
    status = "completed"
    error: Optional[str] = None
    try:
        receipt = inv.run()
    except PooledRunError as e:
        status = "failed"
        error = str(e)
        receipt = e.receipt
    rdict = receipt.to_dict() if receipt is not None else {}
    receipts = {agent_id: rdict}
    _persist_receipts(artifacts_dir, arm, claim_id, receipts)
    tally = _tally(receipts)
    return ArmResult(
        arm=arm,
        claim_id=claim_id,
        team_verdict=receipt.verdict if receipt is not None else None,
        individual_verdicts={agent_id: (receipt.verdict if receipt is not None else None)},
        receipts=receipts,
        status=status,
        error=error,
        **tally,
    )


def run_central(claim_id: str, client_factory: ClientFactory, caps: MatchedCaps, artifacts_dir: Path) -> ArmResult:
    return _run_pooled_single(
        claim_id, "central_adaptive", "central", _central_system_prompt(claim_id), client_factory, caps, artifacts_dir
    )


def run_single(claim_id: str, client_factory: ClientFactory, caps: MatchedCaps, artifacts_dir: Path) -> ArmResult:
    return _run_pooled_single(
        claim_id, "single_investigator", "single", _single_system_prompt(claim_id), client_factory, caps, artifacts_dir
    )


# ---------------------------------------------------------------------------
# arm 2: open_sharing (two-phase share-then-finalize)
# ---------------------------------------------------------------------------
def _format_shared_conclusions(phase1: Dict[str, Dict[str, Any]]) -> str:
    lines = ["The other auditors' INITIAL verdicts (before finalizing):"]
    for agent_id in sorted(phase1):
        r = phase1[agent_id]
        v = r.get("verdict") or "ABSTAIN"
        reasoning = (r.get("reasoning") or "").strip()
        lines.append(f"- {agent_id}: {v}" + (f" — {reasoning}" if reasoning else ""))
    lines.append("Reconsider in light of the above and commit your FINAL verdict.")
    return "\n".join(lines)


def run_open_sharing(
    claim_id: str, client_factory: ClientFactory, caps: MatchedCaps, artifacts_dir: Path
) -> ArmResult:
    phase_caps = caps.open_sharing_phase_caps()
    agent_ids = [f"open-{i}" for i in range(caps.n_team)]

    # Phase 1: independent initial verdicts (all see the full union).
    phase1: Dict[str, Dict[str, Any]] = {}
    for agent_id in agent_ids:
        client = client_factory(f"{agent_id}-p1")
        inv = PooledInvestigator(
            client, agent_id, claim_id, "open_sharing", all_artifacts(),
            _open_sharing_system_prompt(claim_id, "initial"), phase_caps,
        )
        try:
            receipt = inv.run()
        except PooledRunError as e:
            receipt = e.receipt
        phase1[agent_id] = receipt.to_dict() if receipt is not None else {}

    shared = _format_shared_conclusions(phase1)

    # Phase 2: finalize after reading the shared initial verdicts.
    phase2: Dict[str, Dict[str, Any]] = {}
    for agent_id in agent_ids:
        client = client_factory(f"{agent_id}-p2")
        inv = PooledInvestigator(
            client, agent_id, claim_id, "open_sharing", all_artifacts(),
            _open_sharing_system_prompt(claim_id, "finalize"), phase_caps,
            shared_context=shared,
        )
        try:
            receipt = inv.run()
        except PooledRunError as e:
            receipt = e.receipt
        phase2[agent_id] = receipt.to_dict() if receipt is not None else {}

    # Persist BOTH phases (auditable); the final verdicts come from phase 2.
    combined = {f"{a}::initial": r for a, r in phase1.items()}
    combined.update({f"{a}::final": r for a, r in phase2.items()})
    _persist_receipts(artifacts_dir, "open_sharing", claim_id, combined)

    individual = {agent_id: (phase2[agent_id].get("verdict")) for agent_id in agent_ids}
    # Tally over BOTH phases (8 receipts) so the arm's total spend is not
    # undercounted; phase1 and phase2 share agent_id keys, so a naive merge
    # would drop phase1.
    tally = _tally(combined)
    failed = any(not r.get("verdict") for r in phase2.values())
    return ArmResult(
        arm="open_sharing",
        claim_id=claim_id,
        team_verdict=majority(individual),
        individual_verdicts=individual,
        receipts=combined,
        status="failed" if failed else "completed",
        error="one or more open_sharing investigators did not finalize a verdict" if failed else None,
        **tally,
    )


ARM_RUNNERS = {
    "escrowed_independent": run_escrowed,
    "open_sharing": run_open_sharing,
    "central_adaptive": run_central,
    "single_investigator": run_single,
}

__all__ = [
    "ARM_NAMES",
    "ARM_RUNNERS",
    "ArmResult",
    "parse_verdict_from_statement",
    "majority",
    "run_escrowed",
    "run_open_sharing",
    "run_central",
    "run_single",
]
