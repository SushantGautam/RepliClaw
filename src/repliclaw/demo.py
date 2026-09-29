"""Reproducible demo (AC16 / AC18) — real generated outputs, no fabrication.

`repliclaw demo --out artifacts/demo [--backend auto|llm|deterministic]`

Produces under the output dir:
- `demo_transcript.md` — the full protocol trace: visible commitments BEFORE
  reveal (hashes + phase), revealed evidence, disagreement, the autonomous
  follow-up need, and the final provenance-linked verdict.
- `demo_summary.md` — verdict for the supported claim + the comparison table
  against the coordination baselines on the misleading claim.
- per-run `verify_report.md` + full run dirs (events, commitments, artifacts).

Backends:
- `llm` — real generated outputs from the OpenAI-compatible endpoint (the
  AC18 demo path).
- `deterministic` — hermetic offline lenses (works with no network).
- `auto` (default) — llm if an API key is available, else deterministic.

The demo NEVER edits or injects results: everything shown is produced by the
run itself (AC18). If RepliClaw underperforms on a case, the transcript shows
it as-is.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .benchmark import FIXTURES_DIR
from .models import Claim
from .strategies import STRATEGY_RUNNERS, run_strategy
from .verify import make_investigator_factory, verify


def pick_backend(requested: str = "auto") -> str:
    if requested == "auto":
        from .investigators import LLMConfig
        return "llm" if LLMConfig().available else "deterministic"
    return requested


def _claim_from_fixture(name: str) -> Claim:
    fx = json.loads((FIXTURES_DIR / f"{name}.json").read_text())
    c = fx["claim"]
    return Claim(
        claim_id=f"demo-{fx['id']}",
        statement=c["statement"],
        domain=c.get("domain", "general"),
        data=c.get("data"),
        seeded_fault=c.get("seeded_fault"),
    )


def run_demo(out_dir: str | Path, backend: str = "auto") -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    backend = pick_backend(backend)
    factory = make_investigator_factory(backend)
    t0 = time.time()

    # ---- Case 1: genuine supported claim (the clean positive) -------------
    supported_claim = _claim_from_fixture("clean_supported")
    rep_supported = verify(
        {"statement": supported_claim.statement, "data": supported_claim.data,
         "claim_id": supported_claim.claim_id},
        config={"backend": backend, "run_root": str(out / "case_supported")},
    )

    # ---- Case 2: misleading artifact (disagreement + follow-up) -----------
    misleading_claim = _claim_from_fixture("misleading_wrong_test")
    rep_misleading = verify(
        {"statement": misleading_claim.statement, "data": misleading_claim.data,
         "claim_id": misleading_claim.claim_id,
         "seeded_fault": misleading_claim.seeded_fault},
        config={"backend": backend, "run_root": str(out / "case_misleading")},
    )

    # ---- Baseline comparison on the SAME misleading claim -----------------
    comparisons: List[Dict[str, Any]] = []
    for strat in ("single_agent", "fixed_dag", "isolated_vote", "open_debate", "repl_claw"):
        res = run_strategy(strat, _claim_from_fixture("misleading_wrong_test"),
                           factory, out / "baselines" / strat)
        comparisons.append({
            "strategy": strat,
            "label": res.verdict.label.value,
            "confidence": res.verdict.confidence,
            "n_agents": len({e.agent_id for e in res.evidence}),
            "n_needs": len(res.needs),
            "tokens": res.usage.total_tokens,
            "wall_clock_s": round(res.wall_clock_s, 3),
        })

    transcript = _render_transcript(backend, rep_supported, rep_misleading)
    summary = _render_summary(backend, rep_supported, rep_misleading, comparisons,
                              time.time() - t0)
    (out / "demo_transcript.md").write_text(transcript, encoding="utf-8")
    (out / "demo_summary.md").write_text(summary, encoding="utf-8")
    (out / "demo_summary.json").write_text(json.dumps({
        "backend": backend,
        "case_supported": rep_supported.to_dict(),
        "case_misleading": rep_misleading.to_dict(),
        "baseline_comparison_misleading_case": comparisons,
        "wall_clock_s": round(time.time() - t0, 2),
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
def _commitments_table(run_dir: str) -> str:
    """The VISIBLE commitments BEFORE reveal, reconstructed from the run's
    event log (`committed` events carry only the hash — never content, AC10).
    Shows exactly what the protocol observed at the blind/committed phase."""
    events_path = Path(run_dir) / "events.jsonl"
    lines = ["| agent | commitment_id | content_hash (sealed, no content visible) | committed_at |",
             "|---|---|---|---|"]
    seen = set()
    reveal_started = False
    if events_path.exists():
        for line in events_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            if e.get("kind") == "phase" and e.get("phase") == "revealing":
                reveal_started = True
                continue
            # Only the initial blind round: commitments made before the first
            # reveal (follow-up commitments happen later and are not part of
            # the pre-reveal view).
            if reveal_started:
                continue
            if e.get("kind") == "committed" and e.get("agent_id") not in seen:
                seen.add(e["agent_id"])
                cid = e.get("commitment_id", "")
                ch = str(e.get("content_hash", ""))
                lines.append(
                    f"| {e['agent_id']} | `{cid}` | `{ch[:16]}…` | {e.get('ts','')[:19]}Z |"
                )
    if not seen:
        lines.append("| (no commitments recorded) | | | |")
    lines.append("")
    lines.append("_Note: at this point the run store would return metadata only "
                 "(`read_sealed_commitment(revealed=False)`); reading content now raises "
                 "`IsolationViolation`. Reveal timestamps and `reveal_verified: true` are "
                 "recorded in `commitments/*.json` after the reveal phase._")
    return "\n".join(lines)


def _render_transcript(backend, rep_supported, rep_misleading) -> str:
    L: List[str] = [
        "# RepliClaw Demo Transcript",
        "",
        f"**Backend:** `{backend}` | **Generated:** {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        "",
        "Everything below is produced by the runs themselves (no injected values, AC18).",
        "",
        "## Case 1 — genuine supported claim",
        "",
        rep_supported.verdict.reasoning,
        "",
        f"**Verdict: `{rep_supported.verdict_label}`** (confidence {rep_supported.verdict_confidence:.3f})",
        "",
        f"Report: `{rep_supported.report_path}`",
        "",
        "---",
        "",
        "## Case 2 — misleading artifact"
        + (" (conflict → autonomous follow-up)" if rep_misleading.needs else " (no unresolved conflict this run)"),
        "",
        "**Phase 2 — visible commitments BEFORE reveal** (tamper-evident hashes; content sealed):",
        "",
        _commitments_table(rep_misleading.run_dir),
        "",
        "**Phase 3 — revealed evidence** (verified against the commitments):",
        "",
        "| agent | relation | conclusion | executable | confidence |",
        "|---|---|---|---|---|",
    ]
    for e in rep_misleading.evidence:
        L.append(f"| {e.agent_id} | {e.relation.value} | "
                 f"{e.finding.get('conclusion', '')} | {e.executable} | {e.confidence:.2f} |")
    L += ["", "**Phase 5 — autonomous follow-up need(s)** (plannerless):", ""]
    for n in rep_misleading.needs:
        L.append(f"- **{n.get('kind')}** (priority {n.get('priority', 0):.2f}): {n.get('query')}")
    if not rep_misleading.needs:
        L.append("- (no follow-up needed — investigators agreed)")
    L += [
        "",
        "**Phase 6 — final provenance-linked verdict:**",
        "",
        f"### `{rep_misleading.verdict_label}`  (confidence {rep_misleading.verdict_confidence:.3f})",
        "",
        rep_misleading.verdict.reasoning,
        "",
        f"Report: `{rep_misleading.report_path}`",
    ]
    return "\n".join(L)


def _render_summary(backend, rep_supported, rep_misleading, comparisons, elapsed) -> str:
    L = [
        "# RepliClaw Demo — Summary & Baseline Comparison",
        "",
        f"Backend: `{backend}` | Wall clock: {elapsed:.1f}s",
        "",
        "## Case results",
        "",
        "| case | truth | verdict | confidence |",
        "|---|---|---|---|",
        f"| genuine supported (RR=1.5, raw RR=1.5) | supported | "
        f"**{rep_supported.verdict_label}** | {rep_supported.verdict_confidence:.3f} |",
        f"| misleading (means look significant; raw RR=1.0) | refuted | "
        f"**{rep_misleading.verdict_label}** | {rep_misleading.verdict_confidence:.3f} |",
        "",
        "## Baseline comparison on the misleading case",
        "",
        "| strategy | verdict | confidence | agents | follow-up needs | tokens | latency (s) |",
        "|---|---|---|---|---|---|---|",
    ]
    for c in comparisons:
        L.append(
            f"| {c['strategy']} | {c['label']} | {c['confidence']:.3f} | "
            f"{c['n_agents']} | {c['n_needs']} | {c['tokens']} | {c['wall_clock_s']:.3f} |"
        )
    L += [
        "",
        "## Interpretation (derived from the numbers above, not asserted)",
        "",
    ]
    L += _interpret(comparisons, rep_supported, rep_misleading)
    return "\n".join(L)


def _interpret(comparisons, rep_supported, rep_misleading) -> List[str]:
    """Data-driven read of the tables — states what actually happened in THIS
    run (AC18: no manufactured narrative)."""
    by = {c["strategy"]: c for c in comparisons}
    rc = by.get("repl_claw", {})
    misled = [s for s in ("single_agent", "fixed_dag")
              if by.get(s, {}).get("label") == "SUPPORTED"]
    abstained = [s for s in ("isolated_vote", "open_debate")
                 if by.get(s, {}).get("label") == "INCONCLUSIVE"]
    lines: List[str] = []

    if rc.get("label") == "REFUTED":
        lines.append(
            f"- RepliClaw concluded **REFUTED** "
            f"(conf {rc.get('confidence', 0):.3f}, {rc.get('n_agents')} agents, "
            f"{rc.get('n_needs')} follow-up need(s)) — matching the ground truth "
            "that the published RR is not supported by the raw events."
        )
    elif rc.get("label") == "INCONCLUSIVE":
        lines.append(
            f"- RepliClaw abstained (**INCONCLUSIVE**, conf "
            f"{rc.get('confidence', 0):.3f}). The live model did not produce "
            "decisive executable directional evidence this run; the protocol "
            "correctly refused to over-claim. (See transcript for per-agent "
            "reasons.)"
        )
    else:
        lines.append(
            f"- RepliClaw concluded **{rc.get('label')}** "
            f"(conf {rc.get('confidence', 0):.3f}) on this run."
        )

    # Needs + fulfillment are reported from the Case-2 run itself
    # (`rep_misleading`), so the bullet is self-consistent. A need is only
    # called "fulfilled" when an actual follow-up piece of evidence exists
    # (notes = "fulfills need ..."); needs.jsonl is written at emission, so a
    # count alone could overstate fulfillment.
    case_needs = len(rep_misleading.needs or [])
    fulfilled_ev = [
        e for e in (rep_misleading.evidence or [])
        if "fulfills need" in (getattr(e, "notes", "") or "")
    ]
    if case_needs:
        if fulfilled_ev:
            lines.append(
                f"- {case_needs} follow-up need(s) was/were emitted AND fulfilled by "
                "independent follow-up investigator(s) (evidence-conditional, "
                "non-hard-coded path): "
                + ", ".join(f"`{e.agent_id}`" for e in fulfilled_ev) + "."
            )
        else:
            lines.append(
                f"- {case_needs} follow-up need(s) was/were emitted but NOT fulfilled "
                "in this run (the follow-up investigator errored or its reveal "
                "mismatched); the verdict reflects the base evidence only."
            )
    else:
        lines.append(
            "- No follow-up need was emitted this run: the revealed evidence "
            "did not contain an unresolved independent conflict (the follow-up "
            "branch is evidence-conditional, not fixed)."
        )

    if misled:
        lines.append(f"- Baselines that false-accepted the misleading artifact: **{', '.join(misled)}**.")
    else:
        lines.append("- On this run, no baseline false-accepted the misleading artifact "
                     "(with live models, raw-event reading is straightforward for all roles).")
    if abstained:
        lines.append(f"- Baselines that abstained instead of deciding: **{', '.join(abstained)}**.")

    if rep_supported.verdict_label == "SUPPORTED":
        lines.append(
            f"- Control case: the genuine supported claim was verified "
            f"**SUPPORTED** (conf {rep_supported.verdict_confidence:.3f}), so the "
            "refutation above is not a blanket abstention/refutation bias."
        )
    lines.append("")
    lines.append("_Deterministic-backend runs (offline) additionally demonstrate the full "
                 "conflict → follow-up adjudication recovery path; see "
                 "`artifacts/demo/` and `artifacts/benchmark/`._")
    return lines
