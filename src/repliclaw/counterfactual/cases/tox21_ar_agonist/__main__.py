"""Canonical-run entrypoint for the Tox21 AR-agonist P06 case.

Usage (from the worktree root)::

    .venv/bin/python -m repliclaw.counterfactual.cases.tox21_ar_agonist \
        artifacts/science/p06-hero-canonical

Runs every arm offline and pins the case-level manifest + per-arm artifacts.
This is the command ``replay.sh`` and the manifest's ``reproduce`` field point
to.
"""
from __future__ import annotations

import sys
from pathlib import Path

from repliclaw.counterfactual.cases._base import run_canonical
from repliclaw.counterfactual.cases.tox21_ar_agonist import load_case

_DEFAULT_OUT = "artifacts/science/p06-hero-canonical"


def main(argv: list[str]) -> int:
    out = Path(argv[1]) if len(argv) > 1 else Path(_DEFAULT_OUT)
    runs = run_canonical(load_case(), out, seed=0)
    for arm_id in sorted(runs):
        r = runs[arm_id]
        print(
            f"{arm_id:12s} "
            f"mean_delta_logp={r.target_output['mean_delta_logp']:+.6f} "
            f"severity={r.severity}"
        )
    print(f"manifest: {out / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
