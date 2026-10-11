"""Run the frozen four-arm protocol end to end (COMPOUND_CAUSAL_4ARM.md).

Usage:
    python -m repliclaw.benchmarks.compound_causal run \
        --root .artifacts/compound-causal-dev \
        --out  .artifacts/compound-causal-4arm

Pipeline (protocol sections 2, 4, 5, 8):
  1. Load dataset; write case_order.json in fixed stratum order (harness-only
     gold access, used ONLY for ordering — never exposed to strategies).
  2. For each arm x case: fresh BenchmarkSession -> run_arm -> validate ->
     append predictions/<arm>.jsonl -> save traces/<arm>/<case_id>.json.
  3. Freeze prediction files (read-only), record git SHA, then score via
     score_predictions() and write scores.json with metric tables.
Private oracles are read here ONLY for case ordering and scoring.
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

from .arms import ARMS, make_submission, run_arm, validate_submission
from .core import BenchmarkSession, load_dataset, score_predictions

TOKEN_COSTS = {"observe": 50, "commit": 80, "intervene": 120, "final_submission": 100}
STRATUM_ORDER = ("distributed/compound", "distributed/simple",
                 "shared/compound", "shared/simple")


def build_case_order(gold: dict[str, dict[str, Any]],
                     file_order: list[str]) -> list[str]:
    """Fixed stratum ordering; file order within each stratum."""
    by_stratum: dict[str, list[str]] = {s: [] for s in STRATUM_ORDER}
    for cid in file_order:
        by_stratum[gold[cid]["stratum"]].append(cid)
    return [cid for s in STRATUM_ORDER for cid in by_stratum[s]]


def _tokens_from_history(history: dict[str, Any], n_revealed_forecasts: int) -> int:
    """Deterministic proxy from call counts: observe + commit + intervene + final."""
    commits = len(history["revealed_forecasts"]) + len(history["still_sealed_commitments"])
    return (len(history["observations"]) * TOKEN_COSTS["observe"]
            + commits * TOKEN_COSTS["commit"]
            + len(history["interventions"]) * TOKEN_COSTS["intervene"]
            + TOKEN_COSTS["final_submission"])


def _git_sha() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                             text=True, check=True)
        return out.stdout.strip()
    except Exception:
        return "unknown"


def _freeze(path: Path) -> None:
    path.chmod(0o444)


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 6) if values else 0.0


def _brier_for(history: dict[str, Any]) -> tuple[float, bool, int]:
    """Mean Brier over revealed forecasts for this case; (value, had_forecast, committed)."""
    revealed = history["revealed_forecasts"]
    committed = len(revealed) + len(history["still_sealed_commitments"])
    if not revealed:
        return 0.0, False, committed
    return _mean([f["brier"] for f in revealed]), True, committed


def _duplication_rate(interventions: list[dict[str, Any]]) -> tuple[int, int]:
    seen: set[tuple[str, ...]] = set()
    total = dups = 0
    for iv in interventions:
        key = tuple(iv["repairs"])
        total += 1
        if key in seen:
            dups += 1
        seen.add(key)
    return dups, total


def compute_arm_metrics(submissions: list[dict[str, Any]],
                        traces: dict[str, dict[str, Any]],
                        gold: dict[str, dict[str, Any]],
                        scored: dict[str, Any]) -> dict[str, Any]:
    per_case_rows = {r["case_id"]: r for r in scored["per_case"]}
    briers: list[float] = []
    no_forecast_cases = 0
    forecasts_committed = 0
    exp_total = 0
    dup_total = dup_cases_sum = 0
    tokens_total = 0
    wall_total = 0
    completed = 0
    interaction_correct = interaction_total = 0
    abstention_correct = false_conclusion = wrong_nonclean = 0
    clean_total = 0
    cause_and_logic_by_stratum: dict[str, dict[str, int]] = {}

    for sub in submissions:
        cid = sub["case_id"]
        world = gold[cid]
        trace = traces[cid]
        history = trace["public_history"]
        row = per_case_rows.get(cid, {})
        completed += 1 if trace.get("completed") else 0
        brier_val, had_forecast, committed = _brier_for(history)
        forecasts_committed += committed
        if had_forecast:
            briers.append(brier_val)
        else:
            no_forecast_cases += 1
        dups, total_iv = _duplication_rate(history["interventions"])
        exp_total += total_iv
        dup_total += dups
        dup_cases_sum += total_iv
        tokens_total += trace["tokens_proxy"]
        wall_total += trace["wall_clock_ms"]
        logic = world["causal_logic"]
        pred_logic = sub["predicted_logic"]
        if logic in ("or", "and"):
            interaction_total += 1
            interaction_correct += pred_logic == logic
        if logic == "clean":
            clean_total += 1
            if pred_logic == "abstain":
                abstention_correct += 1
            else:
                false_conclusion += 1
        elif not row.get("cause_and_logic_exact"):
            wrong_nonclean += 1
        s = world["stratum"]
        bucket = cause_and_logic_by_stratum.setdefault(s, {"scored": 0, "exact": 0})
        bucket["scored"] += 1
        bucket["exact"] += 1 if row.get("cause_and_logic_exact") else 0

    return {
        "exact_cause_set": scored["exact_causes"],
        "cause_and_logic_exact": scored["exact_cause_and_logic"],
        "cause_and_logic_by_stratum": cause_and_logic_by_stratum,
        "interaction_correct": interaction_correct,
        "interaction_total": interaction_total,
        "abstention_correct": abstention_correct,
        "false_conclusion_clean": false_conclusion,
        "wrong_nonclean": wrong_nonclean,
        "clean_cases": clean_total,
        "forecast_brier_mean": _mean(briers),
        "no_forecast_cases": no_forecast_cases,
        "forecasts_committed": forecasts_committed,
        "experiment_count": exp_total,
        "duplication_rate": round(dup_total / dup_cases_sum, 6) if dup_cases_sum else 0.0,
        "tokens_proxy_total": tokens_total,
        "wall_clock_ms_total": wall_total,
        "completion_rate": round(completed / len(submissions), 6) if submissions else 0.0,
    }


def run_protocol(root: Path, out: Path) -> dict[str, Any]:
    root, out = Path(root), Path(out)
    cards, gold = load_dataset(root)
    file_order = [json.loads(line)["case_id"]
                  for line in (root / "public" / "cases.jsonl").read_text(encoding="utf-8").splitlines()
                  if line.strip()]
    case_order = build_case_order(gold, file_order)

    out.mkdir(parents=True, exist_ok=True)
    pred_dir = out / "predictions"
    trace_root = out / "traces"
    pred_dir.mkdir(exist_ok=True)
    trace_root.mkdir(exist_ok=True)
    (out / "case_order.json").write_text(json.dumps(case_order, indent=2) + "\n", encoding="utf-8")

    predictions: dict[str, list[dict[str, Any]]] = {a: [] for a in ARMS}
    traces: dict[str, dict[str, dict[str, Any]]] = {a: {} for a in ARMS}

    for arm in ARMS:
        arm_trace_dir = trace_root / arm
        arm_trace_dir.mkdir(exist_ok=True)
        pred_file = pred_dir / f"{arm}.jsonl"
        with pred_file.open("w", encoding="utf-8") as fh:
            for idx, cid in enumerate(case_order):
                session = BenchmarkSession(cards[cid], gold[cid])
                t0 = time.perf_counter()
                completed = False
                submission: dict[str, Any] | None = None
                try:
                    submission, _meter = run_arm(arm, session, index_in_case_order=idx)
                    validate_submission(submission)
                    completed = True
                except Exception:
                    # Protocol bug guard: best-effort valid submission so the
                    # case still gets a frozen row (completion_rate < 1 flags it).
                    submission = make_submission(cid, [], "abstain")
                    completed = False
                wall_ms = int(round((time.perf_counter() - t0) * 1000))
                history = session.public_history()
                trace = {
                    "case_id": cid,
                    "arm": arm,
                    "wall_clock_ms": wall_ms,
                    "tokens_proxy": _tokens_from_history(history, len(history["revealed_forecasts"])),
                    "completed": completed,
                    "public_history": history,
                }
                (arm_trace_dir / f"{cid}.json").write_text(
                    json.dumps(trace, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                fh.write(json.dumps(submission, sort_keys=True) + "\n")
                predictions[arm].append(submission)
                traces[arm][cid] = trace

    # Freeze predictions BEFORE scoring (protocol section 5).
    for arm in ARMS:
        _freeze(pred_dir / f"{arm}.jsonl")

    git_sha = _git_sha()
    scores: dict[str, Any] = {
        "schema": "compound_causal_4arm/v1",
        "git_sha": git_sha,
        "case_order_source": "stratum ordering from private gold (harness-only)",
        "arms": {},
    }
    for arm in ARMS:
        scored = score_predictions(gold, predictions[arm])
        metrics = compute_arm_metrics(predictions[arm], traces[arm], gold, scored)
        scores["arms"][arm] = {"score_predictions": scored, "metrics": metrics}

    (out / "scores.json").write_text(json.dumps(scores, indent=2, sort_keys=True) + "\n",
                                     encoding="utf-8")
    return scores


def main(argv: list[str] | None = None) -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Run the frozen four-arm protocol")
    parser.add_argument("--root", required=True, type=Path, help="benchmark dataset root")
    parser.add_argument("--out", required=True, type=Path, help="artifact output directory")
    args = parser.parse_args(argv)
    scores = run_protocol(args.root, args.out)
    summary = {
        arm: {k: v for k, v in data["metrics"].items()}
        for arm, data in scores["arms"].items()
    }
    print(json.dumps({"out": str(args.out), "git_sha": scores["git_sha"],
                      "headline": summary}, indent=2))
