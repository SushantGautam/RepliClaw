"""Run V4 D-E vs C-EQ arms against live AIOpsLab fault-injection problems.

Usage:
    PYTHONPATH=.../AIOpsLab:$PYTHONPATH \
    .venv/bin/python -m repliclaw.experiments.v3.run_aiopslab_v4 \
        --problem astronomy_shop_ad_service_high_cpu-localization-1 \
        --arms D-E C-EQ --seeds 20261013 20261014
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

# Ensure AIOpsLab is importable
AIOPSLAB_ROOT = os.environ.get(
    "AIOPSLAB_ROOT", "/Users/sushantgautam/Documents/stg2-worktrees/AIOpsLab"
)
if AIOPSLAB_ROOT not in sys.path:
    sys.path.insert(0, AIOPSLAB_ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="V4 x AIOpsLab live experiment")
    parser.add_argument("--problem", required=True, help="AIOpsLab problem ID")
    parser.add_argument("--arms", nargs="+", default=["D-E", "C-EQ"])
    parser.add_argument("--seeds", type=int, nargs="+", default=[20261013])
    parser.add_argument("--out-dir", default="/tmp/v4_aiopslab_run")
    parser.add_argument("--envelope-tokens", type=int, default=150_000)
    args = parser.parse_args()

    # Load our modules
    from repliclaw.experiments.v3.aiopslab_adapter import (
        AIOpsLabCaseRunner, LiveTelemetrySandbox, AIOpsLabToolSandbox, load_aiopslab,
    )
    from repliclaw.experiments.v3.telemetry_arms import (
        make_simula_client, _Envelope, MAX_TOKENS_PER_RUN, LLMToolSession,
    )
    from repliclaw.experiments.v3.run_aiopslab_v4 import _make_live_arms
    LiveDEArm, LiveCEQArm = _make_live_arms()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== V4 x AIOpsLab LIVE EXPERIMENT ===")
    print(f"Problem: {args.problem}")
    print(f"Arms: {args.arms}")
    print(f"Seeds: {args.seeds}")
    print(f"Output: {out_dir}")
    print("=" * 60)

    # Setup AIOpsLab case (injects fault)
    runner = AIOpsLabCaseRunner(args.problem)
    case = runner.setup()
    print(f"[setup] Fault injected in namespace '{case.namespace}'")
    print(f"[setup] Task description ({len(case.task_description)} chars):")
    print(f"  {case.task_description[:500]}...")
    print()

    # Create client
    raw_client = make_simula_client(model="default", timeout=120.0)

    class _ChatAdapter:
        def __init__(self, completions):
            self._completions = completions
        def create(self, **kwargs):
            return self._completions.create(**kwargs)

    client = SimpleNamespace(chat=_ChatAdapter(raw_client.chat.completions))
    envelope = _Envelope(max_tokens_per_run=min(args.envelope_tokens, MAX_TOKENS_PER_RUN))

    results = []

    try:
        for seed in args.seeds:
            for arm_name in args.arms:
                tag = f"{seed}/{arm_name}"
                arm_out = str(out_dir / str(seed) / arm_name)
                print(f"\n--- Running {tag} ---")

                t0 = time.monotonic()
                try:
                    def sbx_factory():
                        live_sbx = case.sandbox.__class__(case.sandbox._actions, namespace=case.namespace)
                        return LiveTelemetrySandbox(
                            live_sbx, namespace=case.namespace,
                            task_description=case.task_description,
                        )

                    if arm_name == "D-E":
                        arm = LiveDEArm(
                            client=client, registry=None, opaque_id=args.problem,
                            out_dir=arm_out, seed=seed, envelope=envelope,
                            live_sandbox_factory=sbx_factory,
                        )
                    else:  # C-EQ
                        arm = LiveCEQArm(
                            client=client, registry=None, opaque_id=args.problem,
                            out_dir=arm_out, seed=seed, envelope=envelope,
                            live_sandbox_factory=sbx_factory,
                        )

                    result = arm.run()
                    wall = time.monotonic() - t0

                    # Evaluate using AIOpsLab's evaluator
                    eval_results = runner.evaluate(case, result.submitted_ranking)

                    rec = {
                        "seed": seed, "arm": arm_name, "problem": args.problem,
                        "status": result.status, "wall_s": round(wall, 1),
                        "ranking": result.submitted_ranking,
                        "tokens_total": result.tokens_total,
                        "tool_calls": result.tool_calls,
                        "llm_calls": result.llm_calls,
                        "crash": result.crash_error,
                        "warnings": list(result.warnings),
                        "eval": eval_results,
                    }
                    top1 = result.submitted_ranking[0] if result.submitted_ranking else None
                    acc = eval_results.get("Localization Accuracy", 0)
                    print(f"  Status: {result.status}, Top-1: {top1}, "
                          f"Accuracy: {acc}%, Tokens: {result.tokens_total:,}, "
                          f"Wall: {wall:.1f}s")

                except Exception as e:
                    wall = time.monotonic() - t0
                    print(f"  EXCEPTION: {e}")
                    import traceback; traceback.print_exc()
                    rec = {
                        "seed": seed, "arm": arm_name, "problem": args.problem,
                        "status": "exception", "wall_s": round(wall, 1),
                        "ranking": None, "tokens_total": 0, "tool_calls": 0,
                        "llm_calls": 0, "crash": str(e), "warnings": [], "eval": {},
                    }

                results.append(rec)
                with open(out_dir / "results.jsonl", "a") as f:
                    f.write(json.dumps(rec) + "\n")

    finally:
        runner.teardown(case)
        print(f"\n[teardown] Fault recovered.")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY:")
    for r in results:
        acc = r.get("eval", {}).get("Localization Accuracy", "?")
        print(f"  {r['seed']}/{r['arm']}: {r['status']} acc={acc}% "
              f"tok={r['tokens_total']:,} wall={r['wall_s']}s")

    return 0


if __name__ == "__main__":
    sys.exit(main())


# ---------------------------------------------------------------------------
# Arm subclasses that inject LiveTelemetrySandbox instead of TelemetrySandbox
# ---------------------------------------------------------------------------

def _make_live_arms():
    """Return (LiveDEArm, LiveCEQArm) classes wired to AIOpsLab."""
    from repliclaw.experiments.v3.det_deadline import DetelemDetArm, CEQDetArm
    from repliclaw.experiments.v3.aiopslab_adapter import LiveTelemetrySandbox, AIOpsLabToolSandbox

    class LiveDEArm(DetelemDetArm):
        def __init__(self, *args, live_sandbox_factory, **kwargs):
            self._live_sbx_factory = live_sandbox_factory
            super().__init__(*args, **kwargs)

        def _new_sandbox(self):
            sbx = self._live_sbx_factory()
            self.sandboxes.append(sbx)
            return sbx

    class LiveCEQArm(CEQDetArm):
        def __init__(self, *args, live_sandbox_factory, **kwargs):
            self._live_sbx_factory = live_sandbox_factory
            super().__init__(*args, **kwargs)

        def _new_sandbox(self):
            sbx = self._live_sbx_factory()
            self.sandboxes.append(sbx)
            return sbx

    return LiveDEArm, LiveCEQArm
