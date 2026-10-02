"""P08 — oracle-gated offline scorer for the matched-budget EESS campaign.

This is the ONLY code path in the codebase allowed to read a sealed oracle
file (judge Q12, layer 3).  Every other module — arms, runners, slice,
replay — must stay oracle-free.  The scorer opens the oracle only AFTER it
has walked ``runs_dir`` and confirmed that every run directory under every
arm carries a complete, sealed artifact set.  If any run directory is
incomplete, the scorer crashes with a clear error and writes nothing, so the
oracle can never be read while runs are still in flight.

The oracle gate is the load-bearing safety property of P08 (science judge
2026-10-08, BLOCKER ITEM 1 / Q12): it is the only thing that both (a)
computes M1–M11 and (b) is the only oracle-isolation layer 3.

See :mod:`repliclaw.p08.score` for the CLI and the metric implementation.
"""
from __future__ import annotations

from repliclaw.p08.score import ScoreError, score_runs

__all__ = ["ScoreError", "score_runs"]
