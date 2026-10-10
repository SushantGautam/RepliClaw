# rule_a1 sensitivity at Δ_min = 0.15 — N=24, k=4 slice (SIMULATION-ONLY)

**Worker:** W2k (mandatory pre-freeze stat computation, J-SCI W1/W2 flag)
**Date:** 2026-10-10
**Runs:** `scripts/mc_rule015.py` in worktree `w2/rule015` (dev @ a716a85), numpy 1.26.4 (matches the 254-cell run), full table in `artifacts/mc_rule015_results.md` (untracked), log in `artifacts/mc_rule015_run.log` (untracked).

**Label: SIMULATION-ONLY.** Synthetic Bernoulli data characterizing the frozen bootstrap procedure; no live RepliClaw data.

## 1. What was run

Decision-relevant slice of the 254-cell V3 power grid: **N=24, k=4**, all 5 true Δ (0.00, 0.10, 0.15, 0.20, 0.30) × 2 variance levels (low: p_c(CEQ)~U[0.20,0.50]; mid: U[0.05,0.65]) × 4 saturation levels (none / both-arm ceiling s=0.25, 0.50, 0.75) = **40 cells × R=10,000 MC reps** (≈12 min). Three verdict rules per cell:

- `base`: MEANINGFUL_POSITIVE iff percentile-CI lower endpoint > 0 (frozen S2.3 as-is);
- `a1_010`: base AND point estimate θ̂ ≥ 0.10 (the variant simulated in the 254-cell grid; superseded candidate D-V3-007, retained for comparison);
- `a1_015`: base AND θ̂ ≥ 0.15 (**the AMENDED A1 freeze candidate, D-V3-008** — this run exists so the prereg can cite the exact frozen variant).

Everything else is inherited verbatim from the frozen 254-cell scheme: pinned L5 `cluster_bootstrap.cluster_bootstrap_ci` (imported from `src/repliclaw/benchmarks/common/cluster_bootstrap.py` via `PYTHONPATH=src`, **not re-implemented**) called once per rep — B=10,000, `default_rng(20261009)`, PCG64, percentile 95%; per-cell MC seed `default_rng(20261009 + cell_index)`; identical data model.

**Seed assignment.** The 254-cell grid contains only 2 k=4 cells in this slice (Δ∈{0.15, 0.20}, mid variance, no saturation, original indices **247** and **253**). Those two cells keep their original indices (cell-by-cell comparable). The other 38 cells (all Δ=0/0.10/0.30 rows, all saturation rows) did not exist in the 254-cell grid and were assigned fresh indices **254–291** in slice order; they are new simulation cells with the same seed scheme, not reinterpretations of stored cells.

## 2. Reproduction check (gate, passed)

Before any new numbers, overlapping cell **247** (N=24, k=4, Δ=0.15, mid, no-sat, seed 20261256) was re-run at R=10,000 under the OLD rule set:

| quantity | stored (254-cell run) | recomputed (this run) | match |
|---|---|---|---|
| power (CI lower > 0) | 0.6151 | 0.6151 | exact |
| power (base & θ̂≥0.10) | 0.6144 | 0.6144 | exact |
| θ achieved | 0.14917 | 0.14917 | exact |

L5 pin also verified byte-identical (sha256 `e14d28add0ceb27b…` == the scratch reference that produced the grid) and `pytest tests/benchmarks/test_l5_pin.py` → **5 passed**. No test files touched.

## 3. Key results (N=24, k=4, mid variance)

MC SE ≈ 0.004–0.005 at these magnitudes.

| Δ | sat@s | θ | base | a1@0.10 | **a1@0.15** | cost vs base |
|---|---|---|---|---|---|---|
| 0.00 (type-I) | none | +0.001 | 0.027 | 0.026 | **0.009** | −0.018 (not a cost: floor *reduces* type-I false-fire) |
| 0.15 | none (idx 247) | +0.149 | 0.615 | 0.614 | **0.484** | **−0.131** |
| 0.15 | both@0.25 | +0.113 | 0.502 | 0.482 | **0.248** | **−0.254** |
| 0.20 | none (idx 253) | +0.199 | 0.839 | 0.838 | **0.756** | **−0.083** |
| 0.20 | both@0.25 | +0.149 | 0.723 | 0.711 | **0.478** | **−0.245** |

Low-variance and s=0.50/0.75 rows follow the same pattern (full 40-cell table in `artifacts/mc_rule015_results.md`). Type-I at Δ=0 is ~2.6% for `base` (consistent with the 254-cell grid's ~2.5% note) and falls further under the floor.

## 4. Conclusion

At N=24, k=4 the 0.15 floor **does cost meaningful power exactly at the Δs that matter**. At Δ=0.15 (true effect equals the floor), attained θ̂ is centered at ≈0.149 — just *below* the floor — so `a1@0.15` catches only ~79% of reps that `base` catches: power drops **0.615 → 0.484 (−0.13)** with no saturation, and **0.502 → 0.248 (−0.25)** once a 25% ceiling-saturation level is present. At Δ=0.20 the cost is smaller but still material: **0.839 → 0.756 (−0.08)** no-sat, **0.723 → 0.478 (−0.25)** at s=0.25. The floor's main benefit is that it converts these losses into *honest tiering* (POSITIVE_SUBTHRESHOLD instead of an over-claimed MEANINGFUL_POSITIVE) and it trims type-I/weak-signal false-fires (0.027 → 0.009 at Δ=0), trimming 21% of base's verdicts at Δ=0.15 no-sat (0.615 → 0.484) and 51% at Δ=0.15/s=0.25 (0.502 → 0.248), which is precisely the guard the S-sat amendment relies on. Net: freezing Δ_min=0.15 is coherent with the D-V3-008 rationale — at Δ=0.15 the design is under-powered anyway (≤0.615 base, 0.484 with floor), so the floor does not push the design below what it can resolve; but the prereg must state that **for a true Δ≈0.15 effect the primary verdict MEANINGFUL_POSITIVE fires only ~48% of the time (no-sat) at this N and k**, and that 0.15-detectability at ≥80% power still requires the larger design already flagged in D-V3-008.
