"""Canonical-run entrypoint for the drift-sign AND-interaction case.

Usage (from the worktree root)::

    uv run python -m repliclaw.counterfactual.cases.drift_sign_and \
        docs/next_stage/results/compound_causal/artifacts/drift_sign_and_v1

Runs every arm offline and pins the case-level manifest + per-arm artifacts.
"""
from __future__ import annotations

import sys
from pathlib import Path

from repliclaw.counterfactual.cases._base import run_canonical
from repliclaw.counterfactual.cases.drift_sign_and import load_case

_DEFAULT_OUT = "docs/next_stage/results/compound_causal/artifacts/drift_sign_and_v1"


def main(argv: list[str]) -> int:
    out = Path(argv[1]) if len(argv) > 1 else Path(_DEFAULT_OUT)
    runs = run_canonical(load_case(), out, seed=0)
    for arm_id in sorted(runs):
        r = runs[arm_id]
        print(
            f"{arm_id:16s} mean_concentration_umg_ml={r.target_output['mean_concentration_umg_ml']:.6f} "
            f"severity={r.severity}"
        )
    print(f"manifest: {out / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
