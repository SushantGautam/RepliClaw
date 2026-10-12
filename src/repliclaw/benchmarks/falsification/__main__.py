"""CLI for the 4-arm matched falsification comparison.

Usage:
    uv run python -m repliclaw.benchmarks.falsification \
        --claims C1,C2,C3 \
        --arms escrowed_independent,open_sharing,central_adaptive,single_investigator \
        --out <dir> [--dry-run]

A LIVE run (no ``--dry-run``) refuses to start if no LLM API key is set
(``REPLICLAW_LLM_API_KEY`` / ``CUSTOM_SIMULACHAT_KEY``). ``--dry-run`` uses a
deterministic mock LLM (no network) and is a HARNESS CHECK only — never a
scientific result.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from .arms import ARM_NAMES
from .evidence import claim_ids
from .runner import run_comparison


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repliclaw.benchmarks.falsification",
        description="Matched 4-arm comparison: independent evidence escrow vs pooled analysis.",
    )
    parser.add_argument(
        "--claims",
        default=",".join(claim_ids()),
        help="Comma-separated claim IDs (default: all 7).",
    )
    parser.add_argument(
        "--arms",
        default=",".join(ARM_NAMES),
        help=f"Comma-separated arm names (default: all). Valid: {', '.join(ARM_NAMES)}.",
    )
    parser.add_argument("--out", required=True, help="Output directory for results + receipts.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use a deterministic mock LLM (offline harness check, NOT a scientific result).",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    claims = [c.strip() for c in args.claims.split(",") if c.strip()]
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    if not claims:
        parser.error("no claims selected")
    if not arms:
        parser.error("no arms selected")

    valid_claims = set(claim_ids())
    for c in claims:
        if c not in valid_claims:
            parser.error(f"unknown claim {c!r}; valid: {sorted(valid_claims)}")
    for a in arms:
        if a not in ARM_NAMES:
            parser.error(f"unknown arm {a!r}; valid: {list(ARM_NAMES)}")

    try:
        run_comparison(claims, arms, Path(args.out), dry_run=args.dry_run)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"Results written to {args.out}/results.json")
    print(f"Summary:      {args.out}/summary.md")
    if args.dry_run:
        print("NOTE: --dry-run is a harness check (mock LLM), NOT a scientific result.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
