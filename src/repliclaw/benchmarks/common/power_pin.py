"""Frozen Monte-Carlo power pin for the V3 decision rule (J-SCI W1 S2, C-SCI-2).

The frozen L5 inference procedure (``statistical_protocol_v3.md`` §2.2/§2.3)
is the cluster (case-level) paired bootstrap in
``repliclaw.benchmarks.common.cluster_bootstrap`` — pinned into the repo
BYTE-IDENTICAL to the scratch implementation whose bytes were recorded in
``docs/next_stage/science/monte_carlo_power_v3.md`` §7 (code provenance,
recorded 2026-10-10).

The scratch Monte-Carlo grid generator (``monte_carlo_power.py``) is a
one-shot simulation driver, NOT a library, so it is not copied into src.
Instead this module records its frozen bytes (sha256), scratch location,
and the environment of record, and offers :func:`verify_power_pin` for
future preregistration runs to confirm the scratch generator has not
drifted before re-running the grid.

All values below are frozen constants; changing any of them invalidates
the preregistered power analysis.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

#: Frozen CI constants (statistical_protocol_v3.md §2.2/§2.3).
BOOTSTRAP_B = 10_000          #: case-cluster resamples per CI
BOOTSTRAP_SEED = 20261009     #: numpy PCG64 seed, frozen in prereg
PERCENTILE_ALPHA = 0.05       #: percentile 95% CI
PERCENTILE_METHOD = "linear"  #: np.percentile default, as in L5

#: Frozen bytes of the pinned L5 reference implementation.
CLUSTER_BOOTSTRAP_SHA256 = (
    "e14d28add0ceb27bdef73daab268bf07041bd857d34ebd477e2793e0aa96258c"
)

#: Frozen bytes of the scratch Monte-Carlo grid generator (NOT in src).
MONTE_CARLO_POWER_SHA256 = (
    "929d6fe99aed470080beb6df344e11b734e97e0ac44d9036bcc3abbd6844662a"
)

#: Scratch worktree holding the (uncommitted) generator + run artifacts.
SCRATCH_DIR = Path("/Users/sushantgautam/Documents/stg2-worktrees/statistics")
SCRATCH_MONTE_CARLO_POWER = SCRATCH_DIR / "monte_carlo_power.py"

#: Environment of record (monte_carlo_power_v3.md §7): grid authored under
#: Python 3.13/numpy as installed in the scratch worktree at run time
#: (2026-10-09/10); the Science Judge's independent bit-exact cell-0
#: reproduction used Python 3.11.7 with numpy 1.26.4.
ENV_OF_RECORD = {
    "grid_authoring": "Python 3.13 / numpy as installed in scratch worktree (2026-10-09/10)",
    "judge_reproduction": "Python 3.11.7 / numpy 1.26.4 (cell 0 bit-exact)",
}


class PowerPinError(RuntimeError):
    """Raised when a pinned L5/MC file no longer matches its frozen sha256."""


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_cluster_bootstrap_pin(pinned_path: Path) -> str:
    """Re-hash the pinned ``cluster_bootstrap.py`` and raise on drift.

    Returns the verified sha256 on success.
    """
    digest = _sha256_of(pinned_path)
    if digest != CLUSTER_BOOTSTRAP_SHA256:
        raise PowerPinError(
            f"{pinned_path}: sha256 {digest} != pinned {CLUSTER_BOOTSTRAP_SHA256}"
        )
    return digest


def verify_power_pin(scratch_dir: Path = SCRATCH_DIR) -> str:
    """Re-hash the scratch ``monte_carlo_power.py`` and raise on drift.

    Live pre-check for future preregistration runs: call this before
    re-running the Monte-Carlo grid so any edit to the scratch generator
    is caught (the grid's frozen constants live in that file).

    Returns the verified sha256 on success.
    """
    path = Path(scratch_dir) / "monte_carlo_power.py"
    if not path.is_file():
        raise PowerPinError(f"scratch generator not found: {path}")
    digest = _sha256_of(path)
    if digest != MONTE_CARLO_POWER_SHA256:
        raise PowerPinError(
            f"{path}: sha256 {digest} != pinned {MONTE_CARLO_POWER_SHA256}"
        )
    return digest
