#!/usr/bin/env python3
"""SIMULATION-ONLY: rule_a1 re-run at Delta_min=0.15 for the N=24, k=4 slice.

Amendment AMEND_V3_FREEZE item 1 / J-SCI W1-W2: the frozen-candidate
decision rule is MEANINGFUL_POSITIVE iff percentile-CI lower endpoint > 0
AND point estimate >= Delta_min. The 254-cell grid (2026-10-10, numpy
1.26.4) simulated the floor variant only at Delta_min=0.10; this script
re-runs the decision-relevant N=24, k=4 slice at both 0.10 and 0.15 so
the prereg can cite the exact frozen variant.

Cell/seed scheme is inherited verbatim from the original 254-cell run
(scratch: stg2-worktrees/statistics/monte_carlo_power.py, READ-ONLY
reference, not imported):
  - per-cell MC seed = numpy default_rng(20261009 + cell_index)
  - cells that exist in the original 254-cell grid keep their original
    index (directly comparable cell-by-cell); cells NEW to this slice
    (k=4 with saturation, which the 254-cell grid did not simulate) get
    index 254 + position in the slice, documented in the output.
  - data model, B=10000, PCG64, percentile 95 all unchanged.

CI step: imports the PINNED L5 function
repliclaw.benchmarks.common.cluster_bootstrap (repo src/, PYTHONPATH=src)
and calls cluster_bootstrap_ci verbatim once per MC rep. Not re-implemented.

Reproduction gate (before any new numbers): one overlapping cell
(N=24, k=4, d=0.15, mid, no-sat; original index 247) is re-run at
R=10000 with the OLD rule set (base + floor 0.10) and must match the
stored values in monte_carlo_power_v3_results.json exactly. If not, the
script aborts without writing results.

Rules computed per cell:
  base      : lo > 0
  a1_010    : lo > 0 and theta_hat >= 0.10
  a1_015    : lo > 0 and theta_hat >= 0.15
"""
import hashlib
import json
import sys
import time

import numpy as np

sys.path.insert(0, "src")  # run from the worktree root: PYTHONPATH=src
from repliclaw.benchmarks.common import cluster_bootstrap as cb  # pinned L5

# Frozen constants (must match the 254-cell run; asserted where possible).
assert cb.N_BOOT == 10_000, "frozen B changed"
assert cb.BOOTSTRAP_SEED == 20261009, "frozen bootstrap seed changed"
MC_SEED_BASE = 20261009
R_REPS = 10_000

VARIANCE_LEVELS = {
    "low": (0.20, 0.50),
    "mid": (0.05, 0.65),
}
FLOORS = {"a1_010": 0.10, "a1_015": 0.15}

STORED = ("/Users/sushantgautam/Documents/stg2-worktrees/statistics/"
          "monte_carlo_power_v3_results.json")
PIN_SHA_SRC = None  # filled at runtime; scratch reference for equivalence


def pin_sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def pin_equivalence():
    """Prove the imported L5 file is byte-identical to the scratch copy
    that produced the 254-cell grid."""
    src = "src/repliclaw/benchmarks/common/cluster_bootstrap.py"
    ref = "/Users/sushantgautam/Documents/stg2-worktrees/statistics/" \
          "cluster_bootstrap.py"
    s_src, s_ref = pin_sha(src), pin_sha(ref)
    assert s_src == s_ref, (
        f"L5 pin drifted: src={s_src[:12]}… scratch={s_ref[:12]}…")
    print(f"L5 pin sha256 == scratch reference: {s_src[:16]}… OK",
          flush=True)


# Original 254-cell grid, rebuilt verbatim from the scratch generator so
# existing cells keep their exact (index, mc_seed).
N_CASES = [12, 16, 20, 24, 30]
DELTAS = [0.00, 0.10, 0.15, 0.20, 0.30]
SAT_CELLS = [("both", 0.25), ("both", 0.50), ("both", 0.75),
             ("de_only", 0.25), ("de_only", 0.50), ("de_only", 0.75)]
SAT_NULL_CELLS = [("both", 0.50), ("both", 0.75), ("de_only", 0.50)]


def original_grid():
    cells = []
    for delta in DELTAS:
        for n in N_CASES:
            for var in VARIANCE_LEVELS:
                cells.append(dict(N=n, k=2, delta=delta, variance=var,
                                  sat="none", s=0.0))
    for delta in (0.15, 0.20, 0.30):
        for n in N_CASES:
            for var in VARIANCE_LEVELS:
                for sat, s in SAT_CELLS:
                    cells.append(dict(N=n, k=2, delta=delta,
                                      variance=var, sat=sat, s=s))
    for n in (12, 24):
        for var in VARIANCE_LEVELS:
            for sat, s in SAT_NULL_CELLS:
                cells.append(dict(N=n, k=2, delta=0.0, variance=var,
                                  sat=sat, s=s))
    for delta in (0.15, 0.20):
        for n in (16, 20, 24):
            for k in (3, 4):
                cells.append(dict(N=n, k=k, delta=delta,
                                  variance="mid", sat="none", s=0.0))
    assert len(cells) == 254, len(cells)
    return cells


def slice_cells():
    """N=24, k=4: all 5 d x 2 variance x 4 s (s=0.0 -> no saturation,
    s>0 -> 'both'-arm ceiling saturation). 40 cells; d=0 rows are the
    type-I rows."""
    cells = []
    for delta in DELTAS:
        for var in VARIANCE_LEVELS:
            for s in (0.0, 0.25, 0.50, 0.75):
                sat = "none" if s == 0.0 else "both"
                cells.append(dict(N=24, k=4, delta=delta, variance=var,
                                  sat=sat, s=s))
    assert len(cells) == 40, len(cells)
    return cells


def generate_data(rng, n, k, delta, vlevel, sat, s):
    """One MC table of R_REPS datasets -> per-case diffs d (R, N),
    multiples of 1/k. Identical to the scratch generator."""
    lo, hi = VARIANCE_LEVELS[vlevel]
    q = rng.uniform(lo, hi, size=(R_REPS, n))
    mask = rng.random((R_REPS, n)) < s
    if sat == "both":
        p_ceq = np.where(mask, 1.0, q)
        p_de = np.where(mask, 1.0, q + delta)
    elif sat == "de_only":
        p_ceq = q
        p_de = np.where(mask, 1.0, q + delta)
    else:
        p_ceq = q
        p_de = q + delta
    p_de = np.clip(p_de, 0.0, 1.0)
    s_de = (rng.random((R_REPS, n, k)) < p_de[:, :, None]).sum(axis=2)
    s_ceq = (rng.random((R_REPS, n, k)) < p_ceq[:, :, None]).sum(axis=2)
    return (s_de - s_ceq) / k


def run_cell(cell, index):
    rng = np.random.default_rng(MC_SEED_BASE + index)  # frozen per-cell seed
    d = generate_data(rng, cell["N"], cell["k"], cell["delta"],
                      cell["variance"], cell["sat"], cell["s"])
    base = a1_010 = a1_015 = 0
    theta_sum = 0.0
    lo_sum = 0.0
    t0 = time.time()
    for r in range(R_REPS):
        lo, _, th = cb.cluster_bootstrap_ci(d[r])
        if lo > 0:
            base += 1
            if th >= 0.10:
                a1_010 += 1
            if th >= 0.15:
                a1_015 += 1
        theta_sum += th
        lo_sum += lo
        if (r + 1) % 2000 == 0:
            el = time.time() - t0
            print(f"  cell {index} rep {r + 1}/{R_REPS} "
                  f"(+{el / (r + 1) * (R_REPS - r - 1):.0f}s left) "
                  f"running base={base / (r + 1):.3f}", flush=True)
    p_base, p_010, p_015 = base / R_REPS, a1_010 / R_REPS, a1_015 / R_REPS
    return {
        **cell, "index": index, "mc_seed": MC_SEED_BASE + index,
        "R": R_REPS,
        "power_base": round(p_base, 5),
        "power_base_se": round(float(np.sqrt(p_base * (1 - p_base)
                                             / (R_REPS - 1))), 5),
        "power_a1_010": round(p_010, 5),
        "power_a1_010_se": round(float(np.sqrt(p_010 * (1 - p_010)
                                               / (R_REPS - 1))), 5),
        "power_a1_015": round(p_015, 5),
        "power_a1_015_se": round(float(np.sqrt(p_015 * (1 - p_015)
                                               / (R_REPS - 1))), 5),
        "theta_achieved": round(float(d.mean()), 5),
        "theta_mean_of_boot": round(theta_sum / R_REPS, 5),
        "lo_mean": round(lo_sum / R_REPS, 5),
    }


def main():
    pin_equivalence()
    orig_keys = {tuple((c["N"], c["k"], c["delta"], c["variance"], c["sat"], c["s"])): i
                 for i, c in enumerate(original_grid())}
    cells = slice_cells()

    # Assign indices: overlapping cells keep their 254-run index; new
    # cells extend from 254 in slice order. Deterministic, printed.
    idx_of = {}
    new_pos = 0
    for cell in cells:
        key = (cell["N"], cell["k"], cell["delta"], cell["variance"],
               cell["sat"], cell["s"])
        if key in orig_keys:
            idx_of[key] = orig_keys[key]
        else:
            idx_of[key] = 254 + new_pos
            new_pos += 1

    stored = {
        (c["N"], c["k"], c["delta"], c["variance"], c["sat"], c["s"]): c
        for c in json.load(open(STORED))["cells"]
    }

    # ---- Reproduction gate: overlapping cell 247 (N=24 k=4 d=0.15 mid
    # no-sat) must match the stored 254-cell run at the OLD rule set.
    rep_key = (24, 4, 0.15, "mid", "none", 0.0)
    assert rep_key in stored, "repro cell missing from stored results"
    assert rep_key in idx_of and idx_of[rep_key] == 247, idx_of.get(rep_key)
    ref = stored[rep_key]
    print(f"REPRODUCTION CHECK: cell index {idx_of[rep_key]} (seed "
          f"{MC_SEED_BASE + idx_of[rep_key]}), R={R_REPS} …", flush=True)
    rep = run_cell([c for c in cells
                    if (c["N"], c["k"], c["delta"], c["variance"], c["sat"],
                        c["s"]) == rep_key][0], idx_of[rep_key])
    print(f"  stored: power_lo_gt_0={ref['power_lo_gt_0']} "
          f"power_a1_floor={ref['power_a1_floor']} "
          f"theta_achieved={ref['theta_achieved']}", flush=True)
    print(f"  recomputed: power_base={rep['power_base']} "
          f"power_a1_010={rep['power_a1_010']} "
          f"theta_achieved={rep['theta_achieved']}", flush=True)
    assert rep["power_base"] == ref["power_lo_gt_0"], (
        f"REPRO FAILED (base): {rep['power_base']} != "
        f"{ref['power_lo_gt_0']} — STOP, do not trust this run")
    assert rep["power_a1_010"] == ref["power_a1_floor"], (
        f"REPRO FAILED (a1@0.10): {rep['power_a1_010']} != "
        f"{ref['power_a1_floor']} — STOP, do not trust this run")
    assert rep["theta_achieved"] == ref["theta_achieved"], (
        f"REPRO FAILED (theta): {rep['theta_achieved']} != "
        f"{ref['theta_achieved']} — STOP, do not trust this run")
    print(f"  REPRODUCTION OK (exact match, numpy {np.__version__})",
          flush=True)

    done = {idx_of[rep_key]: rep}
    for ci, cell in enumerate(cells):
        key = (cell["N"], cell["k"], cell["delta"], cell["variance"],
               cell["sat"], cell["s"])
        if key in done:
            continue
        idx = idx_of[key]
        print(f"cell {ci + 1}/40: N={cell['N']} k={cell['k']} "
              f"d={cell['delta']:.2f} var={cell['variance']} "
              f"sat={cell['sat']}@{cell['s']:.2f} idx={idx} …", flush=True)
        res = run_cell(cell, idx)
        done[idx] = res
        save(results_by_cell_order(cells, done))
    results = results_by_cell_order(cells, done)
    save(results)
    write_markdown(results)
    print(f"DONE: {len(results)} cells x {R_REPS} reps", flush=True)


def results_by_cell_order(cells, done):
    out = []
    for cell in cells:
        key = (cell["N"], cell["k"], cell["delta"], cell["variance"],
               cell["sat"], cell["s"])
        res = [v for v in done.values()
               if (v["N"], v["k"], v["delta"], v["variance"], v["sat"],
                   v["s"]) == key]
        if res:
            out.append(res[0])
    return out


def save(results):
    meta = {
        "label": ("SIMULATION-ONLY: synthetic Bernoulli data; N=24 k=4 "
                  "slice, rule_a1 at 0.10 vs 0.15 vs base; no live "
                  "RepliClaw data"),
        "ci_step": ("pinned L5 cluster_bootstrap_ci called verbatim once "
                    f"per MC rep: B={cb.N_BOOT}, seed={cb.BOOTSTRAP_SEED} "
                    "(numpy PCG64), percentile 95%"),
        "rules": {"base": "CI lower > 0",
                  "a1_010": "CI lower > 0 and theta_hat >= 0.10",
                  "a1_015": "CI lower > 0 and theta_hat >= 0.15"},
        "mc_seed_scheme": "default_rng(20261009 + cell_index); original-"
                          "grid cells keep their 254-run index, new cells "
                          "extend from 254 in slice order",
        "reps_per_cell": R_REPS,
        "numpy_version": np.__version__,
    }
    with open("artifacts/mc_rule015_results.json", "w") as f:
        json.dump({"meta": meta, "cells": results}, f, indent=1)


def write_markdown(results):
    hdr = ("| idx | N | k | Δ | var | sat@s | θ | power_base (±se) | "
           "power_a1_010 (±se) | power_a1_015 (±se) |")
    sep = "|---|---|---|---|---|---|---|---|---|---|"

    def row(r):
        return (f"| {r['index']} | {r['N']} | {r['k']} | {r['delta']:.2f} "
                f"| {r['variance']} | {r['sat']}@{r['s']:.2f} "
                f"| {r['theta_achieved']:+.3f} | "
                f"{r['power_base']:.3f} (±{r['power_base_se']:.3f}) | "
                f"{r['power_a1_010']:.3f} (±{r['power_a1_010_se']:.3f}) | "
                f"{r['power_a1_015']:.3f} (±{r['power_a1_015_se']:.3f}) |")

    with open("artifacts/mc_rule015_results.md", "w") as f:
        f.write("# mc_rule015_results (SIMULATION-ONLY, N=24 k=4 slice)\n\n"
                "Rules: base = CI lower > 0; a1_010 = base & θ̂≥0.10; "
                "a1_015 = base & θ̂≥0.15. Per-cell seeds identical to the "
                "254-cell run for overlapping cells.\n\n")
        f.write("\n".join([hdr, sep] + [row(r) for r in results]) + "\n")


if __name__ == "__main__":
    main()
