"""Cross-team verification surface (AC02 / AC13 / AC16).

Minimal, reusable interface for another ScienceClaw team:

    from repliclaw import verify
    report = verify("Treatment triples the event rate (RR=3.0) vs control",
                    data={...}, artifacts=[...], config={"backend": "deterministic"})
    print(report.verdict.label, report.report_path)

Or from the command line:

    repliclaw verify --claim "..." --data '{"n":400,...}' [--backend llm]

Backends:
- `deterministic` (default, hermetic, no network) — the offline statistical
  lenses. Works out-of-the-box so the interface is always testable.
- `llm` — real generated outputs from the OpenAI-compatible endpoint
  (AC18 demo path); requires an API key.

The interface is deliberately small: submit a claim (+ optional bundled data /
artifact references), get back a provenance-linked verification report without
adopting the whole codebase.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .investigators import LLMConfig
from .models import Claim, InvestigatorConfig
from .protocol import RepliClawProtocol

DEFAULT_OUT = Path("artifacts") / "verify"


# ---------------------------------------------------------------------------
# Backend factories
# ---------------------------------------------------------------------------
def _deterministic_factory(cfg: InvestigatorConfig):
    from .investigators import DeterministicInvestigator
    return DeterministicInvestigator(cfg)


def _llm_factory(client_cfg: "LLMConfig"):
    from .investigators import LLMClient, LLMInvestigator

    def factory(cfg: InvestigatorConfig):
        # Fresh client per investigator so per-agent usage accounting is exact
        # (the protocol adds each investigator's client.usage once).
        return LLMInvestigator(cfg, LLMClient(client_cfg))
    return factory


def make_investigator_factory(backend: str = "deterministic", **client_kwargs):
    backend = (backend or "deterministic").lower()
    if backend in ("llm", "live", "openai"):
        from .investigators import LLMClient, LLMConfig
        cfg = LLMConfig()
        if client_kwargs:
            cfg.__dict__.update({k: v for k, v in client_kwargs.items() if v is not None})
        client = LLMClient(cfg)
        if not client.cfg.available:
            raise RuntimeError(
                "backend='llm' needs an API key: set REPLICLAW_LLM_API_KEY "
                "(or CUSTOM_SIMULACHAT_KEY), or use backend='deterministic'."
            )
        return _llm_factory(cfg)
    return _deterministic_factory


# ---------------------------------------------------------------------------
# Verification report
# ---------------------------------------------------------------------------
@dataclass
class VerificationReport:
    run_id: str
    claim_id: str
    verdict_label: str
    verdict_confidence: float
    reasoning: str
    run_dir: str
    report_path: str
    n_evidence: int
    n_independent: int
    n_needs: int
    usage: Dict[str, Any] = field(default_factory=dict)
    verdict: Any = None
    evidence: List[Any] = field(default_factory=list)
    commitments: List[Dict[str, Any]] = field(default_factory=list)
    needs: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "claim_id": self.claim_id,
            "verdict": self.verdict_label,
            "confidence": self.verdict_confidence,
            "reasoning": self.reasoning,
            "run_dir": self.run_dir,
            "report_path": self.report_path,
            "n_evidence": self.n_evidence,
            "n_independent": self.n_independent,
            "n_needs": self.n_needs,
            "usage": self.usage,
            "needs": self.needs,
        }


def _render_markdown(claim, proto_result, backend: str) -> str:
    v = proto_result.verdict
    lines = [
        "# RepliClaw Verification Report",
        "",
        f"**Claim:** {claim.statement}",
        f"**Backend:** {backend}",
        f"**Run:** `{proto_result.run_id}`",
        "",
        "## Verdict",
        "",
        f"### `{v.label.value}`  (confidence {v.confidence:.3f})",
        "",
        v.reasoning,
        "",
        f"- Independent evidence: **{v.independent_evidence_count}** agents",
        f"- Support / contradict / replicate / fail-replicate: "
        f"{v.n_support} / {v.n_contradict} / {v.n_replicate} / {v.n_fail_replicate}",
    ]
    if v.unresolved_conflicts:
        lines += ["", "## Surfaced disagreements", ""]
        for c in v.unresolved_conflicts:
            lines.append(f"- agents: {c.get('agents')}")
    if proto_result.needs:
        lines += ["", "## Follow-up needs (plannerless)", ""]
        for n in proto_result.needs:
            lines.append(f"- **{n.get('kind')}** (priority {n.get('priority', 0):.2f}): {n.get('query')}")
    lines += ["", "## Evidence (provenance-linked)", ""]
    lines += ["| agent | relation | executable | confidence | commitment |"]
    lines += ["|---|---|---|---|---|"]
    for e in proto_result.evidence:
        lines.append(
            f"| {e.agent_id} | {e.relation.value} | {e.executable} | "
            f"{e.confidence:.2f} | `{e.commitment_id}` |"
        )
    lines += [
        "",
        "## Usage",
        "",
        f"- LLM calls: {proto_result.usage.llm_calls}",
        f"- Total tokens: {proto_result.usage.total_tokens}",
        f"- Wall clock: {proto_result.usage.wall_clock_s:.3f}s",
        "",
        f"Run directory: `{proto_result.run_dir}`",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# The verify() entry point
# ---------------------------------------------------------------------------
def verify(
    claim: "Claim | str | Dict[str, Any]",
    artifacts: Optional[List[Any]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> VerificationReport:
    """Verify a scientific claim with the RepliClaw protocol.

    Args:
      claim: a Claim, a plain statement string, or a dict with keys
             {statement, domain, data, reference_truth, seeded_fault, claim_id}.
      artifacts: optional list of artifact refs / dicts bundled with the claim.
      config: optional dict — keys:
               backend (deterministic|llm), run_root, max_followup_rounds,
               task_instructions, <any LLMClient kwargs e.g. model>.
    Returns:
      VerificationReport (provenance-linked; see .run_dir and .report_path).
    """
    config = config or {}
    backend = config.get("backend", "deterministic")
    run_root = Path(config.get("run_root", DEFAULT_OUT))
    # Each verify() call gets its own sub-run directory so runs are hermetic
    # and independent (no cross-run commitment/event leakage).
    import time as _time
    import uuid as _uuid
    run_root = run_root / f"{_time.strftime('%Y%m%d-%H%M%S')}-{_uuid.uuid4().hex[:6]}"

    # Normalize claim.
    if isinstance(claim, str):
        claim = Claim(statement=claim)
    elif isinstance(claim, dict):
        kw = {
            "statement": claim["statement"],
            "domain": claim.get("domain", "general"),
            "data": claim.get("data"),
            "reference_truth": claim.get("reference_truth"),
            "seeded_fault": claim.get("seeded_fault"),
        }
        if claim.get("claim_id"):
            kw["claim_id"] = claim["claim_id"]
        claim = Claim(**kw)
    if artifacts:
        # Bundle artifact references into the claim's data for investigators.
        claim.data = dict(claim.data or {})
        claim.data.setdefault("bundled_artifacts", artifacts)
        # Artifacts that carry a raw `data` block (e.g. raw event counts) are
        # merged into the claim's data so the analytical lenses can compute on
        # them — this is how cross teams submit data via `--artifact file.json`.
        for a in artifacts:
            if isinstance(a, dict) and isinstance(a.get("data"), dict):
                for k, v in a["data"].items():
                    claim.data.setdefault(k, v)

    run_root.mkdir(parents=True, exist_ok=True)
    # Only LLMClient-relevant knobs are forwarded to the backend; the rest of
    # the config (run_root, min_independent, ...) is protocol-level.
    _LLM_KWARGS = {
        "base_url", "api_key", "model", "max_calls", "max_tokens",
        "temperature", "timeout",
    }
    client_kwargs = {k: v for k, v in config.items() if k in _LLM_KWARGS}
    factory = make_investigator_factory(backend, **client_kwargs)
    proto = RepliClawProtocol(
        run_root=run_root,
        investigator_factory=factory,
        min_independent=config.get("min_independent", 3),
        max_followup_rounds=config.get("max_followup_rounds", 1),
    )
    result = proto.run(claim, task_instructions=config.get("task_instructions", ""))

    report_md = _render_markdown(claim, result, backend)
    report_path = run_root / "verify_report.md"
    report_path.write_text(report_md, encoding="utf-8")
    (run_root / "verify_report.json").write_text(
        json.dumps(result.verdict.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return VerificationReport(
        run_id=result.run_id,
        claim_id=claim.claim_id,
        verdict_label=result.verdict.label.value,
        verdict_confidence=result.verdict.confidence,
        reasoning=result.verdict.reasoning,
        run_dir=str(run_root),
        report_path=str(report_path),
        n_evidence=len(result.evidence),
        n_independent=result.verdict.independent_evidence_count,
        n_needs=len(result.needs),
        usage=result.usage.to_dict(),
        verdict=result.verdict,
        evidence=result.evidence,
        commitments=result.commitments,
        needs=result.needs,
    )
