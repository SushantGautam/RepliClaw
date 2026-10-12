"""Orchestrator for the 4-arm matched falsification comparison.

Runs the selected arms on the selected claims under the matched per-claim
envelope, scores them (evaluator-only), and persists ``results.json`` +
per-arm receipts + a short markdown summary.

Live vs dry-run:
  * ``dry_run=True`` uses the deterministic :class:`MockLLMClient` (NO network)
    and is clearly labeled a HARNESS CHECK, not a scientific result.
  * ``dry_run=False`` uses a real :class:`LLMClient` and REFUSES to run if no
    API key is configured (clear message). Live results are never fabricated.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from repliclaw.investigators import LLMClient, LLMConfig

from .arms import ARM_RUNNERS, ArmResult
from .config import DEFAULT_CAPS, MatchedCaps
from .evidence import dataset_sha256
from .mock import MockLLMClient
from .scoring import score_all

RESULTS_SCHEMA = "repliclaw.falsification.results/v1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_client_factory(dry_run: bool, llm_config: Optional[LLMConfig] = None):
    """Return ``(client_factory, model, temperature)`` for the selected mode.

    The factory yields a fresh client per agent/phase. ``model`` and
    ``temperature`` are the values that will actually be used (the env/default
    for live runs, the mock id for dry-runs) so the results record the true
    sampling settings, not placeholders. Every arm shares the same config, so
    model + temperature are matched across arms by construction.
    """
    if dry_run:
        return (lambda agent_id: MockLLMClient(agent_seed=agent_id)), "mock-dryrun", None
    cfg = llm_config or LLMConfig()
    if not cfg.available:
        raise RuntimeError(
            "No LLM API key configured for a LIVE run. Set REPLICLAW_LLM_API_KEY "
            "(or CUSTOM_SIMULACHAT_KEY) and re-run, or use --dry-run for an "
            "offline harness check (which is NOT a scientific result)."
        )
    return (lambda agent_id: LLMClient(cfg)), cfg.model, cfg.temperature


def run_comparison(
    claims: Sequence[str],
    arms: Sequence[str],
    out_dir: Path,
    dry_run: bool = False,
    caps: Optional[MatchedCaps] = None,
    llm_config: Optional[LLMConfig] = None,
) -> Dict[str, Any]:
    """Run the selected arms on the selected claims; persist + return results."""
    caps = caps or DEFAULT_CAPS
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    client_factory, model_used, temperature_used = make_client_factory(dry_run, llm_config)

    arm_results: Dict[str, List[ArmResult]] = {arm: [] for arm in arms}
    for claim_id in claims:
        for arm in arms:
            result = ARM_RUNNERS[arm](claim_id, client_factory, caps, out_dir)
            arm_results[arm].append(result)

    scores = score_all(arm_results)

    results: Dict[str, Any] = {
        "schema": RESULTS_SCHEMA,
        "generated_at": _now_iso(),
        "dry_run": dry_run,
        "harness_check_only": dry_run,
        "dataset": "adversarial_audit_rx441/v1",
        "dataset_sha256": dataset_sha256(),
        "caps": caps.as_dict(),
        "claims": list(claims),
        "arms": list(arms),
        "model_requested": model_used,
        "temperature": temperature_used,
        "scores": scores,
        "per_arm_per_claim": {
            arm: [r.to_dict() for r in arm_results[arm]] for arm in arms
        },
    }
    (out_dir / "results.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _write_summary(out_dir, results)
    return results


# ---------------------------------------------------------------------------
# markdown summary
# ---------------------------------------------------------------------------
def _fmt(x: Optional[float], pct: bool = False) -> str:
    if x is None:
        return "—"
    return f"{x * 100:.1f}%" if pct else f"{x:.4f}"


def _write_summary(out_dir: Path, results: Dict[str, Any]) -> None:
    scores = results["scores"]
    caps = results["caps"]
    mode = (
        "DRY-RUN — HARNESS CHECK ONLY (mock LLM, NOT a scientific result)"
        if results["dry_run"]
        else "LIVE (real LLM calls)"
    )
    lines = [
        "# Falsification Comparison — Results",
        "",
        f"**Mode:** {mode}",
        f"**Dataset:** {results['dataset']} (sha256 `{results['dataset_sha256'][:16]}…`)",
        f"**Claims:** {', '.join(results['claims'])}",
        f"**Arms:** {', '.join(results['arms'])}",
        f"**Matched per-claim caps:** total_tokens={caps['total_tokens']}, "
        f"total_calls={caps['total_calls']} (bounds tool calls), n_team={caps['n_team']}, "
        f"model={results['model_requested']}, temperature={results['temperature']}",
        "",
        "## Results table (arms × metrics)",
        "",
        "| Arm | Acc | Trap acc | Abstain | Tokens | Tool calls | LLM calls | Wall (s) | Ind acc | False-consensus |",
        "|-----|-----|----------|---------|--------|------------|-----------|----------|---------|-----------------|",
    ]
    for arm in results["arms"]:
        s = scores[arm]
        lines.append(
            f"| {arm} | {_fmt(s['accuracy'], True)} | {_fmt(s['robustness_trap_accuracy'], True)} "
            f"| {_fmt(s['abstention_rate'], True)} | {s['total_tokens']} | {s['total_tool_calls']} "
            f"| {s['total_llm_calls']} | {s['total_wall_s']} | {_fmt(s['individual_accuracy'], True)} "
            f"| {_fmt(s['false_consensus_rate'], True)} |"
        )
    lines += ["", "## Per-arm per-claim verdicts", ""]
    for arm in results["arms"]:
        s = scores[arm]
        lines.append(f"### {arm}")
        lines.append("")
        lines.append("| Claim | Expected | Predicted | Correct | Trap |")
        lines.append("|-------|----------|-----------|---------|------|")
        for claim_id in results["claims"]:
            pc = s["per_claim"].get(claim_id, {})
            lines.append(
                f"| {claim_id} | {pc.get('expected')} | {pc.get('predicted')} "
                f"| {'✓' if pc.get('correct') else '✗'} | {'yes' if pc.get('is_trap') else 'no'} |"
            )
        lines.append("")
    if results["dry_run"]:
        lines += [
            "> **NOTE:** This is a `--dry-run` harness check using a deterministic mock LLM. "
            "The verdicts and metrics above validate the plumbing only and are **not** a "
            "scientific result. Run without `--dry-run` (with an API key) for a live comparison.",
            "",
        ]
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


__all__ = ["RESULTS_SCHEMA", "make_client_factory", "run_comparison"]
