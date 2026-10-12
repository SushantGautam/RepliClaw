"""Canonical-run entrypoint for the flow-meter single-cause case.

Usage (from the worktree root)::

    uv run python -m repliclaw.counterfactual.cases.flowmeter_single_cause \
        docs/next_stage/results/compound_causal/artifacts/flowmeter_single_cause_v1

Runs every arm offline and pins the case-level manifest + per-arm artifacts.
"""
from __future__ import annotations

import sys
from pathlib import Path

from repliclaw.counterfactual.cases._base import run_canonical
from repliclaw.counterfactual.cases.flowmeter_single_cause import load_case

_DEFAULT_OUT = "docs/next_stage/results/compound_causal/artifacts/flowmeter_single_cause_v1"


def main(argv: list[str]) -> int:
    out = Path(argv[1]) if len(argv) > 1 else Path(_DEFAULT_OUT)
    runs = run_canonical(load_case(), out, seed=0)
    for arm_id in sorted(runs):
        r = runs[arm_id]
        print(
            f"{arm_id:20s} total_volume_liters={r.target_output['total_volume_liters']:.6f} "
            f"severity={r.severity}"
        )
    print(f"manifest: {out / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
