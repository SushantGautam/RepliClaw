"""L5 statistics pin tests (J-SCI W1 S2, C-SCI-2).

Guarantees the frozen L5 cluster-bootstrap procedure in
``repliclaw.benchmarks.common.cluster_bootstrap`` is still byte-identical
to the preregistered scratch implementation, that its deterministic
output is frozen, and that the scratch Monte-Carlo generator (pinned by
sha256 only, not copied into src) has not drifted.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from repliclaw.benchmarks.common import cluster_bootstrap as cb
from repliclaw.benchmarks.common.power_pin import (
    BOOTSTRAP_B,
    BOOTSTRAP_SEED,
    CLUSTER_BOOTSTRAP_SHA256,
    MONTE_CARLO_POWER_SHA256,
    PERCENTILE_ALPHA,
    SCRATCH_DIR,
    PowerPinError,
    verify_cluster_bootstrap_pin,
    verify_power_pin,
)

PINNED_PATH = (
    Path(__file__).resolve().parents[2]
    / "src" / "repliclaw" / "benchmarks" / "common" / "cluster_bootstrap.py"
)

# Frozen expectation (b). Reference self-test input: fixed 24-case diff
# array (values in the k=2 case-diff lattice {0, 0.5, 1.0}), frozen
# cluster_bootstrap_ci defaults (B=10000, seed 20261009, percentile 95%).
# Computed and verified bit-identical under BOTH numpy 1.26.4 (environment
# of record, judge reproduction) and numpy 2.4.6 (repo venv, Python 3.11.7)
# on 2026-10-10: default_rng PCG64 streams, float64 mean and linear
# percentile are unchanged across these versions for this input, so the
# constant is version-stable. The test asserts the constant only (no
# live recompute) per the pin requirement.
FIXED_INPUT = [
    0.5, 1.0, 0.0, 1.0, 0.5, 1.0, 0.5, 1.0, 0.0, 1.0,
    0.5, 1.0, 0.5, 1.0, 0.0, 1.0, 0.5, 1.0, 0.5, 1.0,
    0.5, 1.0, 0.5, 1.0,
]
FROZEN_CI = (0.5416666666666666, 0.8125, 0.6873125)


def _sha256_of(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_pinned_cluster_bootstrap_sha256() -> None:
    """(a) Pinned L5 bytes equal the preregistered scratch bytes."""
    assert _sha256_of(PINNED_PATH) == CLUSTER_BOOTSTRAP_SHA256 == (
        "e14d28add0ceb27bdef73daab268bf07041bd857d34ebd477e2793e0aa96258c"
    )
    assert verify_cluster_bootstrap_pin(PINNED_PATH) == CLUSTER_BOOTSTRAP_SHA256


def test_frozen_constants_match_prereg() -> None:
    """Frozen constants match statistical_protocol_v3.md S2.2/2.3."""
    assert cb.BOOTSTRAP_SEED == BOOTSTRAP_SEED == 20261009
    assert cb.N_BOOT == BOOTSTRAP_B == 10_000
    assert PERCENTILE_ALPHA == 0.05
    # RNG construction is PCG64 via default_rng (frozen call pattern).
    assert isinstance(np.random.default_rng(BOOTSTRAP_SEED).bit_generator,
                      np.random.PCG64)


def test_frozen_self_test_constant() -> None:
    """(b) Deterministic output on the fixed reference input.

    Asserts the frozen expectation constant only (version-stable across
    numpy 1.26.4 and 2.4.6 — see module constant docstring). The scratch
    file's own self_test() additionally verifies the decision rule and
    determinism, which is asserted here live because it is version-stable.
    """
    assert cb.cluster_bootstrap_ci(FIXED_INPUT) == FROZEN_CI
    assert cb.decision(FROZEN_CI) == "MEANINGFUL_POSITIVE"
    # Scratch __main__ self-test logic, deterministic parts, run live:
    assert cb.cluster_bootstrap_ci(FIXED_INPUT) == cb.cluster_bootstrap_ci(
        FIXED_INPUT
    )


def test_verify_power_pin_real_scratch() -> None:
    """(c) Scratch generator hash check passes on the real scratch dir."""
    if not SCRATCH_DIR.is_dir():
        pytest.skip(f"scratch dir not present on this machine: {SCRATCH_DIR}")
    assert verify_power_pin(SCRATCH_DIR) == MONTE_CARLO_POWER_SHA256


def test_verify_power_pin_fails_on_tamper(tmp_path: Path) -> None:
    """(c) Scratch generator hash check fails on a tampered copy."""
    generator = SCRATCH_DIR / "monte_carlo_power.py"
    if not generator.is_file():
        pytest.skip(f"scratch generator not present: {generator}")
    tampered = tmp_path / "monte_carlo_power.py"
    tampered.write_bytes(generator.read_bytes() + b"# tampered\n")
    with pytest.raises(PowerPinError, match="sha256 .* != pinned"):
        verify_power_pin(tmp_path)
