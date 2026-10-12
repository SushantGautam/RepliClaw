#!/usr/bin/env python
"""Mechanism smoke runner — mechanism v2 arms on the V3 telemetry sandbox.

WHAT THIS IS (read first):

* A SMALL MECHANISM SMOKE of the changed mechanism (mechanism v2,
  lane-mechanism): independent D-E investigators with bounded tool/query
  turns + pre-outcome escrow + best-evidence commit, against the unchanged
  strongest C-EQ (kept strong: identical tool set, identical per-run token
  envelope, plus equivalent parallelism via per-turn tool-call batches).
* ACCESS-MATCHED OBSERVATIONAL diagnosis ONLY: the RCAEval telemetry sandbox
  exposes observational queries (system_context, top_anomalies,
  service_metrics, service_logs, service_traces) — it has NO executable
  interventions. Nothing in this output supports a causal-intervention claim.
* EVOLVING INSTRUMENT, non-comparable to prior ledgers (R1-R3 / Oct-12
  fast-finish campaign): the D-E mechanism and the caps CHANGED. The case is
  one of the 10 frozen pilot cases (already exposed to earlier experiment
  tuning) — this is an exploratory smoke, not a confirmatory heldout result.
  No p-values, no success-rate claims from a single case.

WHAT IT DOES:

* Runs BOTH arms on ONE existing RCAEval pilot case (opaque id) with LOW,
  IDENTICAL per-run caps (token envelope + wall cap, per-investigator tool
  cap) using the SimulaChat "default" model (Qwen3.8-27B, MODEL-SUBSTITUTION
  label) via env-only configuration (no credentials in code):
    SIMULACHAT_BASE_URL  (default: https://simulachat.sushant.pp.ua/api/v1)
    SIMULACHAT_API_KEY   (falls back to REPLICLAW_LLM_API_KEY)
    SIMULACHAT_MODEL     (default: "default")
* Scores scorer-side (official service-level accuracy@5 + top-1) exactly like
  ``pilot_run.py``: ground truth is resolved ONLY here, through the
  sanctioned scorer path; the arms never see it.
* Logs everything: git SHA, requested/echoed model ids, case id + case sha,
  caps, per-arm status/tokens/wall/LLM calls/tool calls, escrow commitments,
  failures (non-completions are failures — never excluded), and the label.

Usage (from the repo root):

    REPLICLAW_LLM_API_KEY="$(cat ~/.config/simulachat.key)" \
      uv run python scripts/mechanism_smoke.py \
        --case RCA-P-05 --tokens-per-run 30000 --de-tool-cap 6
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from pilot_run import (  # noqa: E402 — shared run plumbing (same driver)
    DEFAULT_CASES_INDEX,
    _case_sha256,
    _utc_now_iso,
    _write_json,
    build_simula_client,
    load_cases_index,
    persist_audit,
    preflight,
    resolve_truth,
    score_run,
    verify_cases_index,
)
from repliclaw.experiments.v3.telemetry import PilotCaseRegistry  # noqa: E402
from repliclaw.experiments.v3.telemetry_arms import (  # noqa: E402
    MECHANISM_LABEL,
    MODEL_SUBSTITUTION_LABEL,
    _Envelope,
    CEQTelemArm,
    DetelemArm,
)

DEFAULT_BASE_URL = "https://simulachat.sushant.pp.ua/api/v1"
LABEL = (
    f"MECHANISM SMOKE (v2, lane-mechanism) — {MECHANISM_LABEL}; "
    f"{MODEL_SUBSTITUTION_LABEL}; EVOLVING INSTRUMENT: non-comparable to "
    "prior ledgers; exploratory, single reused pilot case; no confirmatory "
    "or causal-intervention claims."
)


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _run_arm(
    *,
    arm: str,
    client: Any,
    registry: PilotCaseRegistry,
    case: str,
    seed: int,
    out_dir: Path,
    tokens_per_run: int,
    wall_cap_s: float,
    de_tool_cap: int,
) -> dict[str, Any]:
    envelope = _Envelope(max_tokens_per_run=tokens_per_run, wall_cap_s=wall_cap_s)
    if arm == "D-E-TELEM":
        arm_obj = DetelemArm(
            client=client, registry=registry, opaque_id=case, out_dir=out_dir,
            seed=seed, model_label=LABEL, envelope=envelope,
            phase1_tool_cap=de_tool_cap,
        )
    else:
        arm_obj = CEQTelemArm(
            client=client, registry=registry, opaque_id=case, out_dir=out_dir,
            seed=seed, model_label=LABEL, envelope=envelope,
        )
    wall_start = time.monotonic()
    result = arm_obj.run()
    wall_s = round(time.monotonic() - wall_start, 3)
    persist_audit(arm_obj, out_dir)

    status_obj = {
        "label": LABEL,
        "status": result.status,
        "tokens": result.tokens_total,
        "wall_s": wall_s,
        "tool_calls": result.tool_calls,
        "llm_calls": result.llm_calls,
        "submitted_ranking": result.submitted_ranking,
        "model_label": LABEL,
        "arm": arm,
        "case_id": case,
        "seed": seed,
        "caps": {
            "max_tokens_per_run": tokens_per_run,
            "wall_cap_s": wall_cap_s,
            "de_phase1_tool_cap": de_tool_cap if arm == "D-E-TELEM" else None,
        },
        "envelope_source": "identical _Envelope for both arms (mechanism smoke)",
        "case_sha256": _case_sha256(registry, case),
        "protocol_errors": result.protocol_errors,
        "crash_error": result.crash_error,
        "abort_reason": result.abort_reason,
        "warnings": list(result.warnings),
        "prompt_volume_ratio": result.prompt_volume_ratio,
        "escrow_ledger_path": result.escrow_ledger_path,
        "backend_model": (list(result.backend_models)
                          if any(m is not None for m in result.backend_models) else None),
        "interface": (
            "mechanism v2: independent D-E (bounded tool turns, pre-outcome "
            "escrow, best-evidence commit) vs C-EQ (strong, batch parallelism); "
            "ACCESS-MATCHED OBSERVATIONAL (no executable interventions)"
        ),
    }
    _write_json(out_dir / "status.json", status_obj)

    # Escrow commitments (the pre-outcome packets that are the point of the smoke).
    escrow_summary: list[dict[str, Any]] = []
    if result.escrow_ledger_path and Path(result.escrow_ledger_path).is_file():
        ledger = json.loads(Path(result.escrow_ledger_path).read_text())
        escrow_summary = [
            {
                "agent_id": e["agent_id"], "phase": e["phase"],
                "commit_sha256": e["commit_sha256"], "revealed": e["revealed"],
                "ranking": e["ranking"], "confidence": e["confidence"],
            }
            for e in ledger["entries"]
        ]
        status_obj["escrow_commitments"] = escrow_summary
        _write_json(out_dir / "status.json", status_obj)

    return {
        "arm": arm,
        "status": result.status,
        "tokens_total": result.tokens_total,
        "wall_s": wall_s,
        "tool_calls": result.tool_calls,
        "llm_calls": result.llm_calls,
        "submitted_ranking": result.submitted_ranking,
        "abort_reason": result.abort_reason,
        "crash_error": result.crash_error,
        "protocol_errors": result.protocol_errors,
        "warnings": list(result.warnings),
        "prompt_volume_ratio": result.prompt_volume_ratio,
        "backend_models": [m for m in result.backend_models if m is not None],
        "escrow_commitments": escrow_summary,
        "run_dir": str(out_dir),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--case", default="RCA-P-05",
                        help="opaque pilot case id (default RCA-P-05 — a reused "
                             "frozen pilot case, NOT a fresh heldout)")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--tokens-per-run", type=int, default=30_000,
                        help="per-run token envelope, IDENTICAL for both arms "
                             "(default 30000; pair total 60000 <= 120K budget)")
    parser.add_argument("--pair-token-cap", type=int, default=120_000,
                        help="refuse to start if 2 x tokens-per-run exceeds this")
    parser.add_argument("--wall-cap-s", type=float, default=600.0)
    parser.add_argument("--de-tool-cap", type=int, default=6,
                        help="D-E per-investigator bounded tool/query turns "
                             "(default 6; keep small, 4-8)")
    parser.add_argument("--model", default=None,
                        help="SimulaChat model id (default: env SIMULACHAT_MODEL "
                             "or 'default')")
    parser.add_argument("--out", default=str(REPO_ROOT / "docs" / "next_stage" / "results" / "mechanism_smoke"),
                        help="artifact output dir")
    args = parser.parse_args(argv)

    if 2 * args.tokens_per_run > args.pair_token_cap:
        print("refusing: pair token spend would exceed the smoke budget "
              f"({2 * args.tokens_per_run} > {args.pair_token_cap})", file=sys.stderr)
        return 2

    # Env-only provider configuration (no credentials in code).
    os.environ.setdefault("SIMULACHAT_BASE_URL", DEFAULT_BASE_URL)
    if not os.environ.get("SIMULACHAT_API_KEY", "").strip() and \
            os.environ.get("REPLICLAW_LLM_API_KEY", "").strip():
        os.environ["SIMULACHAT_API_KEY"] = os.environ["REPLICLAW_LLM_API_KEY"].strip()
    model = args.model or os.environ.get("SIMULACHAT_MODEL", "").strip() or "default"
    os.environ["SIMULACHAT_MODEL"] = model  # build_simula_client is env-only

    registry = PilotCaseRegistry()
    missing = preflight(registry, [args.case])
    if missing:
        print(f"case data missing: {missing}", file=sys.stderr)
        return 3

    client = build_simula_client()

    out_root = Path(args.out)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_root = out_root / f"smoke_{args.case}_seed{args.seed}_{stamp}"
    (run_root / "common").mkdir(parents=True, exist_ok=True)

    index_path = DEFAULT_CASES_INDEX
    index_sha = verify_cases_index(index_path)
    index_df = load_cases_index(index_path)

    summary: dict[str, Any] = {"label": LABEL}
    pair_tokens = 0
    for arm in ("D-E-TELEM", "C-EQ-TELEM"):
        arm_dir = run_root / "arms" / arm
        arm_dir.mkdir(parents=True, exist_ok=True)
        print(f"[mechanism-smoke] running {arm} on {args.case} "
              f"(tokens/run={args.tokens_per_run}, de_tool_cap={args.de_tool_cap}, "
              f"wall={args.wall_cap_s}s, model={model})", flush=True)
        arm_summary = _run_arm(
            arm=arm, client=client, registry=registry, case=args.case,
            seed=args.seed, out_dir=arm_dir, tokens_per_run=args.tokens_per_run,
            wall_cap_s=args.wall_cap_s, de_tool_cap=args.de_tool_cap,
        )
        pair_tokens += arm_summary["tokens_total"]

        # Scorer side (EVALUATOR-ONLY): ground truth resolved HERE and nowhere
        # in the arms (no oracle leakage).
        if (arm_summary["status"] == "completed" and arm_summary["submitted_ranking"]):
            true_service, idx_sha = resolve_truth(args.case, index_df, index_sha)
            score = score_run(arm_summary["submitted_ranking"], true_service, idx_sha)
            from repliclaw.experiments.v3.telemetry import normalize_service
            top1 = normalize_service(arm_summary["submitted_ranking"][0]) == \
                normalize_service(true_service)
            score = dict(score, top1_hit=bool(top1), true_service_norm=true_service)
            _write_json(arm_dir / "score.json", score)
            arm_summary["score"] = score
        else:
            arm_summary["score"] = None  # non-completion is a FAILURE, recorded as such
        summary[arm] = arm_summary
        s = arm_summary
        print(f"[mechanism-smoke] {arm}: status={s['status']} "
              f"tokens={s['tokens_total']} wall={s['wall_s']}s llm_calls={s['llm_calls']} "
              f"tool_calls={s['tool_calls']} commitments={len(s['escrow_commitments'])} "
              f"abort_reason={s['abort_reason']} score={s['score']}", flush=True)

    summary.update({
        "generated_at": _utc_now_iso(),
        "git_sha": _git_sha(),
        "branch": _git_branch(),
        "model_requested": model,
        "base_url_env": "SIMULACHAT_BASE_URL (operator env; default " + DEFAULT_BASE_URL + ")",
        "case_id": args.case,
        "case_sha256": _case_sha256(registry, args.case),
        "seed": args.seed,
        "index_sha": index_sha,
        "caps": {
            "tokens_per_run_each_arm": args.tokens_per_run,
            "pair_token_cap": args.pair_token_cap,
            "wall_cap_s_each_arm": args.wall_cap_s,
            "de_phase1_tool_cap": args.de_tool_cap,
        },
        "pair_tokens_total": pair_tokens,
        "failures": [
            {"arm": a, "status": summary[a]["status"],
             "abort_reason": summary[a]["abort_reason"],
             "crash_error": summary[a]["crash_error"]}
            for a in ("D-E-TELEM", "C-EQ-TELEM")
            if summary[a]["status"] != "completed"
        ],
        "interpretation": (
            "MECHANISM SMOKE ONLY. Access-matched observational diagnosis on a "
            "single reused pilot case with low caps; evolving instrument; NOT "
            "comparable to prior ledgers; no confirmatory, statistical, or "
            "causal-intervention claim is supported."
        ),
        "run_root": str(run_root),
    })
    _write_json(run_root / "smoke_report.json", summary)
    print(f"[mechanism-smoke] report: {run_root / 'smoke_report.json'}")
    print(json.dumps(summary, indent=2))
    return 0


def _git_branch() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO_ROOT,
            check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
