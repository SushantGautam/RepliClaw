# Monte-Carlo Power for the Frozen V3 Bootstrap — SIMULATION-ONLY

**Status:** DRAFT for J-SCI amendment A3 (replaces the two-sided normal-approximation power formula in `statistical_protocol_v3.md` §4.2, which is demoted to a planning heuristic per F3). **This document is a SIMULATION on synthetic Bernoulli data. It characterizes the operating behavior of the frozen analysis procedure; it is NOT a measurement of RepliClaw, contains no live-run data, and no number here is evidence about any real system.**

- **Date:** 2026-10-10
- **Author:** Monte-Carlo power worker (Stage 2, Wave 1)
- **Code:** `/Users/sushantgautam/Documents/stg2-worktrees/statistics/monte_carlo_power.py` (scratch; scratch dir also holds `cluster_bootstrap.py` verbatim)
- **Full grid results:** `.../stg2-worktrees/statistics/monte_carlo_power_v3_results.json` and `.md` (scratch)
- **Run log:** `.../stg2-worktrees/statistics/monte_carlo_power_v3_run.log`

## 1. Method

### 1.1 Exact procedure simulated (frozen, verbatim)
For each Monte-Carlo (MC) replication of a heldout experiment:

1. Generate N synthetic cases, k=2 seeds (24 sensitivity cells use k=3/4), two arms (D-E, C-EQ). Per case c: C-EQ baseline success probability `p_c ~ U[lo, hi]` (between-case variance; two levels below); D-E probability `min(1, p_c + Δ)` (forced to 1.0 for cases flagged saturated). Each seed is an independent Bernoulli draw (ITT: every run scored 0/1, no censoring).
2. Compute per-case differences `d_c = p̂_c(D-E) − p̂_c(C-EQ)` (with k=2, `d_c ∈ {−1, −0.5, 0, 0.5, 1}`).
3. **CI step: `cluster_bootstrap.cluster_bootstrap_ci` (L5) called VERBATIM, once per replication**: B = 10,000 case-cluster resamples, `numpy.random.default_rng(20261009)` (PCG64), percentile 95% — exactly the frozen §2.2 constants. The L5 function is *called as-is* (no vectorized stand-in on the decision path). Separately, a pure-Python **twin** of the frozen call pattern was asserted bit-identical to the L5 function on 40 random (cell, rep) pairs before the grid ran. Scope of the guarantee (J-SCI W1 S8): the L5 function itself is verbatim; the twin check covers 40 sampled pairs; one grid cell (cell 0) was independently reproduced bit-exactly by the Science Judge under a pinned numpy 1.26.4 venv; the rest of the grid is reproducible to the third decimal via per-cell MC SE.
4. **Decision rule §2.3:** verdict `MEANINGFUL_POSITIVE` iff percentile-CI lower endpoint > 0 (one-sided, as frozen). Additionally reported: the J-SCI A1 pending-floor variant, `MEANINGFUL_POSITIVE` iff lower CI > 0 **and** point estimate ≥ Δ_min = 0.10 (A1 default, not yet frozen).

### 1.2 Grid definition
| Axis | Values |
|---|---|
| N cases | 12, 16, 20, 24, 30 |
| k seeds/case | 2 (main), 3, 4 (sensitivity) |
| True Δ | 0.00 (type-I), 0.10, 0.15, 0.20, 0.30 |
| Between-case variance | `low`: p_c(CEQ) ~ U[0.20, 0.50] (σ_Δ ≈ 0.12); `mid`: U[0.05, 0.65] (σ_Δ ≈ 0.18) |
| Ceiling-saturation regime | none; `both`: s of cases at p=1.0 for BOTH arms (erases Δ on those cases); `de_only`: s of cases at p=1.0 for D-E only (Δ preserved); s ∈ {0.25, 0.50, 0.75} |

**254 cells × 10,000 MC reps each = 2.54M simulated experiments.** Per-cell MC seed `numpy default_rng(20261009 + cell_index)`; full run ≈ 86 min, numpy as pinned by the environment. All estimates carry MC standard error `√(p(1−p)/(R−1))`, reported in every table (typical ±0.002–0.005, so grid values are reproducible to the third decimal).

Sanity brackets passed: (a) **Δ=0 type-I** at N=24 mid variance = 0.026 (see §3.1); (b) **Δ=0.30 strong effect** at N=24 mid = 0.884, at N=30 = 0.940 (§3.3). The L5 reference self-test (`python cluster_bootstrap.py`) passes.

## 2. Headline results

### 2.1 Type-I error at Δ=0: **≤ 0.05 — passes, conservatively**

| N | k | var | P(lower CI > 0) (MC ± se) |
|---|---|---|---|
| 12 | 2 | low | 0.034 ± 0.002 |
| 12 | 2 | mid | 0.032 ± 0.002 |
| 16 | 2 | low/mid | 0.029 / 0.030 ± 0.002 |
| 20 | 2 | low/mid | 0.027 / 0.028 ± 0.002 |
| **24** | 2 | low/mid | **0.026 / 0.026 ± 0.002** |
| 30 | 2 | low/mid | 0.027 / 0.025 ± 0.002 |

**Blunt answer: yes, type-I stays ≤ 0.05 — in fact ~2.5–3.4%, about half the nominal 5%.** This is expected and NOT a bug: the frozen rule ("lower endpoint of a two-sided 95% percentile CI > 0") is a one-sided rule run at an effective α ≈ 2.5% on a discrete, small-N statistic. No amendment is needed to protect against false positives; if anything, the rule is *more conservative* than the §4.2 normal formula assumed. (The converse — loss of power, §2.2 — is the real cost.)

**CRITICAL ADJACENT FINDING (not type-I in the usual sense, a design-level one):** under **one-arm ceiling saturation** (D-E alone at p=1.0 on 50% of cases) with **true Δ = 0**, the decision rule still fires **MEANINGFUL_POSITIVE 83% of the time** (N=24, both variances; 54% at N=12). Saturated D-E cases mechanically lift θ to ≈ s (the saturated fraction) regardless of C-EQ, so "D-E wins by the saturated fraction" is scored as evidence. **The §2.3 rule cannot distinguish a genuine capability difference from one arm running out of difficulty.** §4 below turns this into a mandatory saturation gate. (Two-arm saturation at Δ=0, by contrast, is harmless: type-I = 0.019–0.030.)

### 2.2 Attained power vs the §4.2 planning formula: **the formula understates power, badly, for this rule**

MC empirical power (rule as frozen: lower CI > 0), no saturation, k=2:

| N | Δ=0.10 (low/mid) | Δ=0.15 (low/mid) | Δ=0.20 (low/mid) | Δ=0.30 (low/mid) |
|---|---|---|---|---|
| 12 | 0.12 / 0.13 | 0.20 / 0.22 | 0.32 / 0.34 | 0.57 / 0.62 |
| 16 | 0.14 / 0.15 | 0.24 / 0.26 | 0.38 / 0.41 | 0.69 / 0.73 |
| 20 | 0.15 / 0.17 | 0.27 / 0.31 | 0.44 / 0.48 | 0.78 / 0.82 |
| **24** | **0.17 / 0.19** | **0.32 / 0.35** | **0.51 / 0.56** | **0.84 / 0.88** |
| 30 | 0.20 / 0.22 | 0.39 / 0.42 | 0.60 / 0.64 | 0.92 / 0.94 |

(All ± ≤ 0.005 MC se; A1-floor variant is identical to 3 decimals for every Δ > 0 cell — with positive Δ, θ̂ ≥ 0.10 whenever the lower CI clears 0 at these effect sizes.)

The §4.2 formula `N ≈ 7.85·σ_D²/MDE²` with σ_D = 0.18 (mid variance) and MDE = 0.15 gives N ≈ 15.8 → "80% power" — **but the MC grid requires N ≈ 55 (quadratic fit through N = 12–30) for 80% power at Δ=0.15, mid variance, k=2**. The formula *understates required N by ~3.4×*. Root cause, exactly as F3 predicted: with k=2, `d_c` is a 5-point discrete variable whose within-case Bernoulli noise **dwarfs** the between-case variance the formula plugs in. Measured directly from the simulated Δ=0 data, the standard deviation of the per-case difference is ≈ 0.44 (mid variance, k=2), not the 0.18 between-case σ — the between-case variance alone accounts for only ~15% of Var(d_c). Feeding the *correct* σ_eff ≈ 0.44 into the (still two-sided) formula gives N ≈ 69 for 80% power at MDE = 0.15 — already 4× the draft's 16; the MC grid's ≈ 55 is lower again because the actual rule is one-sided (and the normal approximation is imperfect at N in the 20s–50s). Any power statement built on between-case variance alone is an artifact of pretending the k seeds measured p_c without noise.

The two errors in the §4.2 formula act in *opposite* directions and neither is small: (i) the two-sided constant 1.96 is **conservative** for the actual one-sided rule (MC Δ=0 type-I is ~2.6%, not 5% — §2.1); (ii) the between-case-only σ is **anti-conservative** in exactly the wrong way — it makes the design look better powered than it is. **Net: in the region that matters (MDE 0.15–0.20) the formula promises 80% power at N≈16–24 that the actual procedure does not deliver (MC: 0.17–0.35 at N=24).** This is precisely why A3 mandates Monte Carlo; the MC grid in this document is now the only valid power basis.

### 2.3 Ceiling saturation: effect on power (Δ > 0)

| regime | s | N=12 | N=24 | N=30 | mechanism |
|---|---|---|---|---|---|
| Δ=0.15, `both` | 0.25 | 0.16 | 0.28 | 0.35 | vs unsaturated 0.20/0.32/0.39 at mid→low; θ shrinks to (1−s)·Δ |
| Δ=0.15, `both` | 0.50 | 0.10 | **0.20** | 0.23 | θ → 0.075; power roughly halves again |
| Δ=0.15, `both` | 0.75 | 0.02 | **0.10** | 0.12 | θ → 0.038 ≈ type-I level; metric dead |
| Δ=0.20, `both` | 0.50 | 0.14 | 0.22 | 0.35 | same mechanism |
| Δ=0.30, `both` | 0.75 | 0.06 | 0.27 | 0.37 | even a strong effect is cut to ~θ=0.075 at s=0.75 |
| Δ=0.15, `de_only` | 0.50 | 0.75 | **0.96** | 0.99 | D-E saturation *increases* θ to ≈ s; the rule fires almost always |
| Δ=0.15, `de_only` | 0.75 | 0.95 | 0.999 | 1.000 | verdict ≈ a coin of the saturation fraction |

Two distinct failure modes, both severe:

- **Two-arm saturation erases the contrast** (θ → (1−s)Δ): at s=0.5 the population is only "half" differentiable; at s=0.75 a 0.15 effect is undetectable at any feasible N. "Not established" there is a **ceiling artifact, not a scientific finding** — the §4.3 carve-out ("declare population too easy") must be triggered, but §2 must not *depend on* that human judgment (§4 gate).
- **One-arm saturation manufactures the contrast**: §2.1's critical finding. Any campaign where D-E (or C-EQ) saturates at 100% on a material case share while the other arm does not produces verdicts that measure the *differing saturation fractions*, not a capability difference at matched difficulty.

## 3. Recommended design for the stage-2 heldout

### 3.1 Is "N ≥ 24 cases, MDE 0.15, 80% power" achievable? **No — not at k=2, not plausibly at k=3.**

- N=24, k=2, mid variance: power at Δ=0.15 is **0.346** (low variance 0.318). At Δ=0.20: **0.555** (low 0.512).
- k=3, N=24: Δ=0.15 → **0.506**; Δ=0.20 → **0.731**.
- k=4, N=24: Δ=0.15 → **0.615**; Δ=0.20 → **0.839**.

### 3.2 Recommendation

**N = 24 cases (keep the V3 floor), k = 4 seeds/case, predeclared MDE = 0.20 (absolute per-case success difference), decision rule unchanged.**

Justification (one line): k=4 is the only configuration that reaches ~84% power at MDE 0.20 within the 24-case budget (vs 73% at k=3 and 56% at k=2), and k only multiplies run cost linearly while the §2.2 rationale already accepts nested seeds as cheap.

Conditional refinements, to be locked in prereg after the pilot:

1. **If the pilot estimate of between-case σ_D(D-E, C-EQ) is ≤ 0.12** (the "low" variance band, i.e., cases behave more homogeneously), k=3 suffices for MDE 0.20 (power 0.73 at N=24 low is still short — use k=4, or note the attained power honestly).
2. **MDE = 0.15 is NOT a defensible primary target at k ≤ 4 and N ≤ 24** (max attained power 0.615). If the program insists on MDE 0.15, the honest choices are (a) N ≈ 45–55 cases (extrapolated from the grid; ~2.5× the budget), (b) k ≥ 6, or (c) re-scope MDE = 0.15 to a *secondary, hypothesis-generating* question and run the primary at MDE 0.20. Report the chosen tradeoff in prereg; do not silently borrow the §4.2 formula.
3. **Attained-difference reporting (per §4.3):** prereg must state "with N=24, k=4, mid variance, the design has 84% power for Δ=0.20; the maximum Δ detectable at 80% power is ≈ 0.18", recomputed with pilot σ̂_D via this MC script (seed scheme + cells are reproducible; a pilot-σ variant cell set is a 10-line extension, to be run post-pilot, before prereg freeze).
4. **Type-I note for prereg:** the frozen rule is empirically ~2.5% (not 5%) at Δ=0 on this grid; state that. If the program later wants the full 5% one-sided envelope, that is a *rule change* (lower endpoint > 0 of a *one-sided* 97.5% bound, etc.) and must be an explicit amendment — do not imply the current rule spends 5%.

## 4. Mandatory ceiling-saturation gate (replaces the judgment-based §4.3 trigger)

Add to the prereg as a **stop rule S-sat**, evaluated on the pilot before heldout and on the first 25% of heldout cases as a running canary:

> **S-sat.** Let `sat_A` be the fraction of pilot (or running heldout) cases on which arm A achieves 100% success (all k seeds succeed).
> (a) **Either-arm gate:** if `sat_D-E ≥ 0.25` or `sat_C-EQ ≥ 0.25`, the case population is **too easy or unsuitably stratified** — STOP, widen/re-balance strata (harder fault families, rarer failure modes, systems outside the pilot's) and re-pilot before holding out. Rationale: at one-arm saturation s, the verdict fires with probability ≈ P(θ̂ ≥ s) even at Δ=0 (this grid: s=0.5 → 83% false-fire at N=24); any s above 0.25 makes the primary contrast dominated by difficulty mismatch rather than capability.
> (b) **Two-arm dead-contrast gate:** if `sat_D-E + sat_C-EQ ≥ 1.0` on more than half of cases, the estimand θ is ≈ 0 *by construction* and the campaign must declare the population uninformative and re-stratify — do not run the full N and report "not established" on a dead metric.
> (c) **Disclosure:** per-arm saturation fractions and the joint-both-saturated fraction are mandatory report items in every verdict, alongside the §4.3 attained-difference statement, so a "not established" verdict can always be judged for ceiling-artifact content.

The 0.25 threshold is deliberate and conservative: the MC grid shows the false-fire rate at Δ=0 and one-arm s=0.25 is already ~30–40% at N=12–24 (θ̂ ≈ 0.25, right at the A1 floor). If the program prefers a single headline number matching the user-facing heuristic "if >50% of pilot cases are saturated for **both** arms, declare the population too easy" — that condition is **necessary but far from sufficient**; S-sat(a)/(b) above is the operative rule.

## 5. Scope, caveats, reproducibility

- **SIMULATION.** Bernoulli outcomes, i.i.d. within case, uniform between-case p, no case-order effects, no timeout/abstention behavior (ITT is trivially satisfied by construction). Real rollout noise (timeouts, abstinence, harness failures, correlated seed failures) can only *increase* effective σ_D or *decrease* effective k; treat all power numbers as optimistic-ish upper bounds for the between-case part and exact for the rule mechanics.
- The A1-floor variant (θ̂ ≥ 0.10) was reported everywhere; for Δ ≥ 0.15 it binds essentially never in this grid, but at Δ=0.10 and under saturation the floor removes the tail of sub-threshold "positives" (e.g., N=24, Δ=0.15, both@0.75: 0.098 → 0.080). Keep the A1 decision for the prereg floor vote.
- **Reproducibility:** `python monte_carlo_power.py` in the scratch dir re-runs the entire 254-cell grid deterministically (per-cell seed = 20261009 + cell index; CI seed 20261009 per replication; B=10,000). Runtime ≈ 86 min on the authoring machine (Apple Silicon, Python 3.13/numpy as installed). Incremental JSON is saved after every cell, so an interrupted run is resumable by hand-merging.
- **Code provenance (J-SCI W1 S2, recorded 2026-10-10):** the L5/MC generator code lives in the scratch worktree `~/Documents/stg2-worktrees/statistics/` (not yet in the repo; pinning into the repo is the C-SCI-2 action at G3). Frozen bytes, recorded for the prereg:
  - `cluster_bootstrap.py` — sha256 `e14d28ad d0ceb27b def73daa b268bf07 041bd857 d34ebd47 7e2793e0 aa96258c` (canonical: `e14d28add0ceb27bdef73daab268bf07041bd857d34ebd477e2793e0aa96258c`)
  - `monte_carlo_power.py` — sha256 `929d6fe9 9aed4700 80beb6df 344e11b7 34e97e0a c44d9036 bcc3abbd 6844662a` (canonical: `929d6fe99aed470080beb6df344e11b734e97e0ac44d9036bcc3abbd6844662a`)
  - Environment of record: Python 3.13 / numpy as installed in that worktree at run time (2026-10-09/10); judge-verified reproduction cell used Python 3.11.7 with numpy 1.26.4 and matched cell 0 bit-exactly.
- MC standard errors: all reported estimates carry ±√(p(1−p)/9999); maximum se on any cell is 0.005 (at p≈0.5), so no conclusion in §2–§4 rests on fewer than ~3 se of margin.
- Files (scratch, uncommitted): `monte_carlo_power.py`, `monte_carlo_power_v3_results.json` (254 cells + meta), `monte_carlo_power_v3_results.md` (tables), `monte_carlo_power_v3_run.log` (full run transcript). This doc: `docs/next_stage/science/monte_carlo_power_v3.md`.
