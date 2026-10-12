"""Runner/CLI for the three-arm HiddenBench measurement.

Small scored run:

    export REPLICLAW_LLM_API_KEY="$(cat ~/.config/simulachat.key)"
    uv run python -m repliclaw.benchmarks.hiddenbench.runner \
        --task-ids 1,2,3,4 --rounds 3 --seed 2026 \
        --max-calls 256 --max-tokens 200000 \
        --out docs/next_stage/results/hiddenbench

Offline smoke (no network, deterministic fake):

    uv run python -m repliclaw.benchmarks.hiddenbench.runner \
        --task-ids 1 --fake --out docs/next_stage/results/hiddenbench/smoke
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from ._vendor import ensure_path
from .arms import ARM_RUNNERS, load_prompts, run_arm_task, score_arm  # noqa: F401
from .client import CountingOpenAIClient, FakeClient

ensure_path()

from hiddenbench.benchmark import find_task, load_benchmark  # noqa: E402

DEFAULT_BENCHMARK = (
    Path(__file__).resolve().parents[4] / "third_party" / "hiddenbench" / "data" / "benchmark.json"
)

LABELS = ["OBSERVATIONAL", "ACCESS-MATCHED (not causal)", "MODEL-SUBSTITUTION"]


def _git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[4],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def run_arms(
    *,
    benchmark_path: Path = DEFAULT_BENCHMARK,
    task_ids: list[Any] | None = None,
    arms: list[str] = ("escrow", "open-share", "central"),
    rounds: int = 3,
    seed: int = 2026,
    max_calls: int = 256,
    max_tokens: int = 200_000,
    fake: bool = False,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    """Run the requested arms over the requested tasks; returns the summary."""
    tasks_all = load_benchmark(source="local", path=str(benchmark_path))
    tasks = [find_task(tasks_all, task_id=tid) for tid in (task_ids or [t.id for t in tasks_all])]
    prompts = load_prompts()

    summary: dict[str, Any] = {
        "benchmark": str(benchmark_path),
        "benchmark_file_sha256": _sha_file(benchmark_path),
        "task_ids": [t.id for t in tasks],
        "arms": list(arms),
        "rounds": rounds,
        "seed": seed,
        "caps": {"max_calls_per_arm": max_calls, "max_total_tokens_per_arm": max_tokens},
        "fake": fake,
        "labels": LABELS if not fake else ["OBSERVATIONAL", "ACCESS-MATCHED (not causal)", "FAKE-LLM SMOKE (no model)"],
        "git_sha": _git_sha(),
        "run_started_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "per_arm": {},
    }

    raw_dir = None
    if out_dir is not None:
        out_dir = Path(out_dir)
        raw_dir = out_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)

    for arm in arms:
        client = (
            FakeClient(max_calls=max_calls, max_total_tokens=max_tokens)
            if fake
            else CountingOpenAIClient(max_calls=max_calls, max_total_tokens=max_tokens)
        )
        summary["model"] = client.model
        summary["base_url"] = getattr(client, "base_url", None)
        arm_runs = []
        for task_index, task in enumerate(tasks):
            run = run_arm_task(arm, task, task_index, client, prompts, seed, rounds)
            arm_runs.append(run)
            status = "ok" if run["completed"] else f"FAILED ({run['failure']})"
            print(f"[{arm}] task {task.id} ({task.name}): {status}", flush=True)
        arm_summary = score_arm(arm_runs)
        arm_summary["usage"] = client.usage.to_dict()
        summary["per_arm"][arm] = arm_summary
        if raw_dir is not None:
            raw = {
                "arm": arm,
                "model": client.model,
                "seed": seed,
                "rounds": rounds,
                "runs": arm_runs,
            }
            (raw_dir / f"{arm}.json").write_text(
                json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8"
            )

    if out_dir is not None:
        (Path(out_dir) / "summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (Path(out_dir) / "REPORT.md").write_text(_render_report(summary), encoding="utf-8")
        print(f"Wrote results to {out_dir}", flush=True)
    return summary


def _sha_file(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# HiddenBench (ICML 2026) — RepliClaw three-arm measurement",
        "",
        f"- **Labels:** {', '.join(summary['labels'])}",
        "- **Claim scope:** observational, access-matched. Not a causal claim.",
        f"- Git SHA: `{summary['git_sha']}`",
        f"- Model: `{summary.get('model')}` @ `{summary.get('base_url')}`"
        + (" (FAKE — smoke only)" if summary.get("fake") else " (model substitution, not the released baseline)"),
        f"- Benchmark: `{summary['benchmark']}` (sha256 `{summary['benchmark_file_sha256'][:16]}…`)",
        f"- Tasks: {summary['task_ids']} | rounds: {summary['rounds']} | seed: {summary['seed']}",
        f"- Caps per arm: {summary['caps']}",
        f"- Started: {summary['run_started_at']}",
        "",
        "| arm | tasks | done | acc(done) | acc(all) | indiv-acc | calls | tokens | wall s |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for arm, s in summary["per_arm"].items():
        lines.append(
            f"| {arm} | {s['num_tasks']} | {s['completed']} | "
            f"{s['group_decision_accuracy_completed']:.3f} | "
            f"{s['group_decision_accuracy_all_tasks']:.3f} | "
            f"{s['mean_individual_final_vote_accuracy']:.3f} | "
            f"{s['total_llm_calls']} | {s['total_tokens']} | {s['total_wall_s']} |"
        )
    for arm, s in summary["per_arm"].items():
        if s["failure_reasons"]:
            lines.append(f"\n**Failures ({arm}):**")
            for f in s["failure_reasons"]:
                lines.append(f"- task {f['task_id']} ({f['scenario']}): {f['failure']}")
    lines += [
        "",
        "## Arm definitions",
        "- **escrow**: per-round evidence packets + a ranked-answer commitment held in escrow "
        "(content-free pre-reveal digests, `repliclaw.escrow.phase` gate, `repliclaw.canonical` "
        "commit hashes); revealed only before the final vote; group decision = majority of final votes.",
        "- **open-share**: official HiddenBench discussion protocol (agents see each other while "
        "reasoning); group decision = majority of final votes.",
        "- **central**: one controller receives the pooled information (shared + all hidden facts) "
        "directly and decides in a single vote (C-EQ-style control; pooled access differs by design).",
        "",
        "## Per-task detail",
        "",
    ]
    for arm, s in summary["per_arm"].items():
        lines.append(f"### {arm}")
        for t in s["by_task"]:
            mark = "correct" if t["correct"] else ("FAILURE" if not t["completed"] else "incorrect")
            lines.append(
                f"- task {t['task_id']} ({t['scenario']}): **{mark}** — "
                f"decision={t['group_decision']}, calls={t['llm_calls']}, tokens={t['tokens']}"
            )
    lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", default=str(DEFAULT_BENCHMARK))
    parser.add_argument("--task-ids", default="", help="Comma-separated task ids (default: all).")
    parser.add_argument("--arms", default="escrow,open-share,central")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--max-calls", type=int, default=256)
    parser.add_argument("--max-tokens", type=int, default=200_000)
    parser.add_argument("--fake", action="store_true", help="Offline deterministic fake (smoke only).")
    parser.add_argument("--out", required=True, help="Output directory for raw JSON + REPORT.md.")
    args = parser.parse_args(argv)

    task_ids = [int(t) if t.isdigit() else t for t in args.task_ids.split(",") if t.strip()]
    run_arms(
        benchmark_path=Path(args.benchmark),
        task_ids=task_ids or None,
        arms=[a.strip() for a in args.arms.split(",") if a.strip()],
        rounds=args.rounds,
        seed=args.seed,
        max_calls=args.max_calls,
        max_tokens=args.max_tokens,
        fake=args.fake,
        out_dir=Path(args.out),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
