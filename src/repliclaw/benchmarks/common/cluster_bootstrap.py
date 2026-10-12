#!/usr/bin/env python3
"""SIMULATION-ONLY reference implementation: cluster (case-level) paired
bootstrap for the V3 primary estimand  theta = mean_c (p_c(DE) - p_c(CEQ)),
where p_c(arm) is the arm's success rate pooled over all seeds of case c.

Unit of resampling = CASE (all its seeds move together). This is a simulation
of the estimator on synthetic data; it is NOT a measurement of RepliClaw.
"""
import numpy as np

BOOTSTRAP_SEED = 20261009   # frozen; must equal preregistered constant
N_BOOT = 10_000             # frozen; must equal preregistered constant


def case_diffs(successes_de, successes_ceq, n_seeds):
    """Per-case paired difference. successes_* : (n_cases, n_seeds) of {0,1}."""
    de = successes_de.mean(axis=1)
    ceq = successes_ceq.mean(axis=1)
    return de - ceq


def cluster_bootstrap_ci(d, n_boot=N_BOOT, seed=BOOTSTRAP_SEED, alpha=0.05):
    """Percentile 95% CI of the equal-case-weighted mean of per-case diffs d."""
    d = np.asarray(d, dtype=float)
    n = d.size
    rng = np.random.default_rng(seed)            # numpy Generator, PCG64 default
    idx = rng.integers(0, n, size=(n_boot, n))   # resample cases w/ replacement
    stat = d[idx].mean(axis=1)
    lo, hi = np.percentile(stat, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi), float(stat.mean())


def decision(ci):
    lo, hi, _ = ci
    return "MEANINGFUL_POSITIVE" if lo > 0 else "NOT_ESTABLISHED"  # never "negative"


def self_test():
    rng = np.random.default_rng(1234)
    n_cases, k = 24, 3  # cases, seeds per case
    # Case 1: strong true effect -> CI must clear zero.
    de = (rng.random((n_cases, k)) < 0.90).astype(int)
    ceq = (rng.random((n_cases, k)) < 0.45).astype(int)
    d = case_diffs(de, ceq, k)
    ci = cluster_bootstrap_ci(d)
    assert decision(ci) == "MEANINGFUL_POSITIVE", ci
    # Case 2: true null (both arms, same per-case success prob p) -> CI must include 0.
    p = rng.random(n_cases) * 0.6 + 0.2
    s_de = (rng.random((n_cases, k)) < p[:, None]).astype(int)
    s_ceq = (rng.random((n_cases, k)) < p[:, None]).astype(int)
    ci0 = cluster_bootstrap_ci(case_diffs(s_de, s_ceq, k))
    assert ci0[0] <= 0.0 <= ci0[1], ci0
    # Case 3: determinism under fixed seed.
    assert cluster_bootstrap_ci(d) == cluster_bootstrap_ci(d)
    print("self-test PASSED")
    print(f"  effect case:  d_bar={d.mean():.3f}  CI95=({ci[0]:.3f}, {ci[1]:.3f})  -> {decision(ci)}")
    print(f"  null case:    CI95=({ci0[0]:.3f}, {ci0[1]:.3f})  -> {decision(ci0)}")


if __name__ == "__main__":
    self_test()
