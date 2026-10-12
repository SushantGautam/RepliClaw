#!/usr/bin/env python3
"""AgentRx G1 tiny smoke — SimulaChat model-substitution baseline (D-V3-010).

Contract §10 step 2: judge on 2 tau-retail trajectories, 1 iteration, with
ground truth. Runs against the READ-ONLY AgentRx@7a18c797 checkout via
``repliclaw.benchmarks.agentrx.agentrx_patch`` (no upstream file is modified).

USAGE (from the AgentRx checkout, using its venv so openai/azure/plot deps
resolve; our package is added via PYTHONPATH):

    SIMULACHAT_BASE_URL=... SIMULACHAT_API_KEY=... SIMULACHAT_MODEL=default \
    PYTHONPATH=/Users/sushantgautam/Documents/stg2-worktrees/w2-simula/src \
    /Users/sushantgautam/Documents/stg2-worktrees/agentrx-upstream/.venv/bin/python \
      <this script> --out .artifacts/agentrx/simula_tiny_smoke

Every artifact is stamped: "MODEL-SUBSTITUTION BASELINE (SimulaChat default,
Qwen3.8-27B) — NOT the official released AgentRx baseline".

Mechanical label gate (F-W2-10): the patched SimulaChat factories refuse
to serve completions until stamp_model_substitution_metadata() has been
called for the active run dir (REPLICLAW_RUN_DIR). This script stamps the
output dir BEFORE applying the patch, so the gate is satisfied.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

AGENTRX_ROOT = "/Users/sushantgautam/Documents/stg2-worktrees/agentrx-upstream"
TWO_TRAJECTORIES = [
    os.path.join(AGENTRX_ROOT, "trajectories", "tau-retail", "instruction_adherence_failure.json"),
    os.path.join(AGENTRX_ROOT, "trajectories", "tau-retail", "misinterpretation_tool_output.json"),
]
GROUND_TRUTH = os.path.join(AGENTRX_ROOT, "data", "ground_truth", "tau_ground_truth.json")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="output dir (e.g. .artifacts/agentrx/simula_tiny_smoke)")
    ap.add_argument("--agentrx-root", default=AGENTRX_ROOT)
    args = ap.parse_args()

    out = args.out
    os.makedirs(out, exist_ok=True)

    from repliclaw.benchmarks.agentrx.agentrx_patch import (
        ENDPOINT,
        apply_simula_patch,
        stamp_model_substitution_metadata,
        total_tokens_served,
    )
    from repliclaw.benchmarks.agentrx.simula import (
        MODEL_SUBSTITUTION_LABEL,
        load_config,
    )

    cfg = load_config()
    print(f"[smoke] {MODEL_SUBSTITUTION_LABEL}")
    print(f"[smoke] base_url={cfg.base_url} model={cfg.model} (key: configured, not printed)")

    # Read-only patch of AgentRx in-memory. Mechanical label gate
    # (F-W2-10): declare the active run dir and stamp the label BEFORE
    # running stages, so the routed SimulaChat factories will serve at all.
    os.environ["REPLICLAW_RUN_DIR"] = out
    stamp_model_substitution_metadata(out, extra={
        "trajectories": 2,
        "iterations": 1,
        "contract": "docs/next_stage/adapters/agentrx_contract.md §10 step 2",
    })

    state = apply_simula_patch(args.agentrx_root)
    tokens = {"completions": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    try:
        # 1. IR (LLM-free for tau, but run through the patched path anyway
        #    to exercise endpoint normalization; tau has a hand-written IR).
        import agentrx.ir.trajectory_ir as ir_mod
        import agentrx.judge.judge as judge_mod
        irs = []
        for path in TWO_TRAJECTORIES:
            raw = ir_mod.load_trajectories(path)
            irs.extend(ir_mod.tau_bench_ir(raw))
        ir_path = os.path.join(out, "trajectory_ir.json")
        with open(ir_path, "w", encoding="utf-8") as f:
            json.dump(irs, f, indent=2)
        print(f"[smoke] IR: {len(irs)} trajectories -> {ir_path}")

        # 2. Judge: 1 iteration, 2 trajectories, with ground truth.
        judge_mod.DOMAIN = "tau"
        judge_mod.ENDPOINT_USED = ENDPOINT
        judge_mod.PROMPT_MODE = "combined"
        judge_mod.EXECUTION_MODE = "violations-after"
        judge_mod.USE_GROUND_TRUTH = True

        gt_failures = judge_mod.load_failures_from_json(GROUND_TRUTH)
        print(f"[smoke] ground truth failures loaded: {len(gt_failures)}")

        # run_judge's model_name resolution: endpoint != "azure" →
        # g.TRAPI_DEPLOYMENT_NAME, which apply_simula_patch set to our model.
        judge_mod.run_single_iteration(
            run_number=1,
            base_output_dir=os.path.join(out, "judge_output"),
            ground_truth_failures=gt_failures,
            api_version="v1",
            model_name=cfg.model,
            log_file=ir_path,
        )
        run_json = os.path.join(out, "judge_output", "runs", "run1.json")
        if os.path.exists(run_json):
            summary = json.load(open(run_json)).get("summary", {})
            with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
            print("[smoke] summary.json written (model-substitution baseline; NOT official)")
        else:
            print("[smoke] WARNING: run1.json not found under judge_output/runs")
        tokens = total_tokens_served()
    finally:
        state.undo()
    print(f"[smoke] real token usage: {tokens}")

    # 3. Mandatory label in run metadata.
    stamp_model_substitution_metadata(out, extra={
        "trajectories": 2,
        "iterations": 1,
        "real_token_usage": tokens,
        "trajectories_used": [os.path.basename(p) for p in TWO_TRAJECTORIES],
        "ground_truth": os.path.basename(GROUND_TRUTH),
        "contract": "docs/next_stage/adapters/agentrx_contract.md §10 step 2",
    })
    print(f"[smoke] state.json stamped in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
