# AMEND_NULL_MODEL_CORRECTION — null-model interpretation correction (2026-10-11)

**Worker:** FF-03 (scientific-integrity reviewer)
**Repo/worktree:** `RepliClaw-ff03` (branch `ff03-null-model`, based on `dev` @ `c0cda69`)
**Date:** 2026-10-11
**Status: DRAFT — pending independent science signoff.** This is a *prospective* amendment on the pre-specified amendment path. It corrects a statistical **interpretation** only. It changes **NO** frozen simulation constant, **NO** frozen protocol rule, **NO** stop rule, and **NO** archived review. Frozen files (`design/v3_prereg_final_freeze.md`, `design/v31_prereg_freeze.md`, `design/v32_prereg_freeze.md`, P08 statements) and archived reviews (`docs/next_stage/reviews/*`) are **untouched**. No human approval is claimed.

## 1. The misconception (stated precisely)

The live guidance carries the phrasing that a **forced one-arm saturation with equal nominal Δ=0 is a "null" (type-I) condition** — e.g. "one-arm saturation at **true Δ=0** fires MEANINGFUL_POSITIVE ~83% of the time at s=0.5" (protocol) and "one-arm s=0.25 already gives ~30–40% **false-fire at Δ=0**" (pilot spec).

This is a misconception. Forcing **one** arm to a success ceiling (p=1.0) on a fraction `s` of cases while the other arm stays at its base per-case probability `p_c` does **NOT** preserve a true zero effect. On the ceiling cases the per-case difference is `1.0 − p_c` (not 0), so the **realized** treatment effect is ≈ `s·(1 − p̄_c) > 0`, not 0. The "Δ=0" label refers only to the *nominal* added effect (the `delta` parameter in the generator), **not** to the *realized* per-case difference. An arm-only ceiling therefore **changes the treatment effect** and is, at minimum, an **estimand / selection issue**: the estimand is no longer the equal-case-weighted paired difference under a common null, because the ceiling cases are selected into a different regime for one arm only. A **significant contrast under such a setup is NOT by itself a type-I error** — it is the expected rejection of a rule that is correctly detecting a non-zero realized effect. Calling it a "false-fire" / "type-I at Δ=0" conflates a design artifact (one-arm ceiling) with a null hypothesis.

The **valid** type-I measurement is the **no-saturation Δ=0 cell** (equal arm probabilities, no ceiling), where the realized effect is genuinely 0. The protocol's "Type-I at Δ=0 measured 0.026 (≤ 0.05, conservative)" refers to that clean null and **remains valid**; it is not the target of this correction.

## 2. Correct null generation (type-I under H0, paired case-cluster comparison)

To assess type-I under H0 for the paired case-cluster comparison, the MC null must generate **equal arm probabilities conditional on each case**: `p_c(D-E) = p_c(C-EQ)` for every case `c`, so the per-case difference is 0 in expectation for every case. Where ceiling cases are included, they must be set **symmetrically across arms** (both arms at p=1.0 on the *same* masked cases) so the ceiling contributes 0 to the per-case difference.

This is exactly what the pinned L5 self-test does (`src/repliclaw/benchmarks/common/cluster_bootstrap.py`, `self_test` Case 2: "true null (both arms, same per-case success prob p)") and what `scripts/mc_rule015.py`'s `slice_cells()` uses for its d=0 rows (`sat="both"` or `sat="none"`, **never** `de_only`). The original 254-cell grid's `de_only` Δ=0 cell (see `SAT_NULL_CELLS` in `scripts/mc_rule015.py::original_grid`) is the flawed one and **must not be cited as a type-I / null condition**.

## 3. Explicit status: simulation-only, not confirmatory

- The MC guidance **N=24, k=4, MDE=0.20** is **SIMULATION-ONLY** (synthetic Bernoulli data, frozen percentile bootstrap). It is **NOT a confirmatory sample size** and confers no power guarantee on the real heldout. A confirmatory sample size requires a prospective power recomputation with pilot-estimated σ̂_D and approved resources (G4 gate).
- **24 × 4 × 2 rollouts (192) are NOT 192 independent cases.** Seeds are nested within cases; the **unit of inference is the case** (the cluster bootstrap resamples cases with all their seeds attached). The effective sample size for the primary estimand is **N=24 cases**, not 192 rollouts. Do not report or reason as if 192 independent observations exist.

## 4. Scope: live docs carrying the flawed phrasing + erratum applied

Live (non-frozen, non-archived) docs in the bound search set that carry the flawed phrasing:

| # | File | Section / line | Flawed phrasing | Action taken |
|---|------|----------------|-----------------|--------------|
| 1 | `docs/next_stage/EXPERIMENT_PROTOCOL_V3_DRAFT.md` | "Scientific design", D-V3-008 bullet → "Mandatory S-sat stop rule" sub-bullet (line 64) | "one-arm saturation at **true Δ=0** fires MEANINGFUL_POSITIVE ~83% of the time at s=0.5" | **ONE-LINE ERRATUM pointer added** (single most misleading LIVE location) |
| 2 | `docs/next_stage/design/g3_pilot_spec_draft.md` | §5 Stop rules, rule 1 (S-sat) "Source" clause (lines 256–257) | "one-arm s=0.25 already gives ~30–40% **false-fire at Δ=0**, N=12–24" | Carries the phrasing; corrected **by reference to this doc** (no in-file edit — the single erratum pointer is kept at location #1 to honor "one line only") |
| 3 | `docs/next_stage/design/v3_prereg_final_freeze.md` | S-sat guard note (lines 191–192) | "the one-arm s = 0.25 ceiling-saturation trip probability **at Δ=0** is the reason S-sat exists" | **FROZEN — NOT edited** (read-only). Recorded here for traceability; any correction requires a versioned amendment + re-freeze with independent signoff. |
| 4 | `docs/next_stage/science/monte_carlo_power_v3.md` | §2.1 CRITICAL ADJACENT FINDING (line ~49); §4.1 S-sat rationale (line ~112) | "with **true Δ = 0**, the decision rule still fires MEANINGFUL_POSITIVE 83% of the time"; "s=0.5 → 83% false-fire at N=24" | **IN-BOUND, LIVE simulation-authority doc (S4 per v3 freeze line 14) — NOT edited** (DRAFT revision, FF06 condition C1, 2026-10-12): same forced-ceiling mislabel as locations #1–#3. Carried for traceability under this same amendment; no in-file edit (single erratum pointer stays at location #1). The underlying SIMULATION result (one-arm ceiling ⇒ contrast dominated by difficulty mismatch) remains valid and unchanged — only the "Δ=0 null" framing is corrected, exactly as for #1–#3. |

The **single one-line erratum pointer** was added at location **#1** (the most misleading LIVE location — the primary protocol's mandatory S-sat rule). Its exact text:

> `  - **ERRATUM (2026-10-11, FF-03):** the parenthetical "one-arm saturation at true Δ=0" mislabels a forced one-arm ceiling as a null (Δ=0) condition — a one-arm ceiling changes the realized treatment effect, so its significant contrast is not by itself a type-I error; correct null generation (equal arm probabilities per case, symmetric ceilings) and the full correction are in `AMEND_NULL_MODEL_CORRECTION_20261011.md` (DRAFT, pending independent science signoff). The S-sat stop rule above is unchanged.`

Locations #2 and #3 are documented for traceability; #3 is frozen and untouched. No other file in the bound search set was edited. `amendments_AMEND_V3_FREEZE_20261010.md` line 21 ("type-I 0.026") refers to the **valid** clean-null type-I and is not flawed; left unchanged. `scripts/mc_rule015.py` and `scripts/t05_pilot_sigma_mc.py` docstrings were reviewed: `mc_rule015.py`'s d=0 rows use symmetric (`both`) or no saturation (a valid null) and `t05_pilot_sigma_mc.py` has no saturation cells — **no flawed phrasing, no edit needed**.

**Frozen rules unchanged:** the S-sat stop rule (threshold 25%, either arm), the model-capability floor gate, all simulation constants (`N_BOOT=10,000`, `BOOTSTRAP_SEED=20261009`, PCG64, percentile 95, N=24, k=4), and all stop rules are **unchanged**. This amendment corrects interpretation only.

## 5. Contamination canary (independent, 2026-10-11)

**Canary 1 — pytest leak/parity/label/scorer canaries (D-E vs C-EQ interface): PASS.**

Command: `uv run python -m pytest tests/benchmarks tests/experiments -q`
Summary line (verbatim): `================== 180 passed, 23 skipped, 3 xfailed in 5.28s ==================` (exit 0)

> **Snapshot footnote (FF06 condition C2, 2026-10-12):** the counts above are a dated snapshot from the 2026-10-11 canary run. Re-verified on 2026-10-12 at dev@5ec0152 (after FF-05 harness fixes 5f78c82 + resume guard eebde20 added tests): the same two canary directories now yield `tests/experiments` = 113 passed / 3 skipped / 2 xfailed and `tests/benchmarks` = 91 passed / 11 skipped (exit 0); full repo suite = 468 passed / 23 skipped / 2 xfailed. Same canary files, all green; the deltas vs the 180/23/3 snapshot are the new budget-exhaustion-parity, recovery and resume-guard tests. The original snapshot is preserved verbatim for traceability.

Key canary files (verbatim per-file result lines from the verbose run):
- `tests/benchmarks/test_rcaeval_leak.py ..x` — leak guard: 2 passed, 1 xfailed (xfail = intentional G2-hardening canary tracking the `rcaeval/manifest.py` module-docstring closure; not a failure)
- `tests/experiments/test_v3_ceq_parity.py ...........` — payload parity canaries: 11 passed
- `tests/benchmarks/test_ground_truth_gate.py ...........` — label / ground-truth gate: 11 passed
- `tests/experiments/test_v3_g2_canaries.py ..x.x.` — G2 canaries (scorer-only resolve gate, oracle isolation, no-fixed-script, replay determinism): 4 passed, 2 xfailed (both xfails are documented intentional canaries, not failures)
- `tests/experiments/test_v3_ceq_no_fixed_script.py ..` — no fixed script: 2 passed
- `tests/experiments/test_v3_ceq_budget.py ....` — budget-cap canary: 4 passed

The 23 skips are data-availability skips on this host (pilot case data / `baro_feasibility.json` / pilot telemetry not on disk), not canary failures. No leak, parity, label-gate, or scorer-only-resolve canary failed.

**Canary 2 — offline no-LLM pilot canary: PASS (pilot data present in the main checkout).**
The ff03 worktree itself lacks `.artifacts/rcaeval/pilot`, but the main checkout on this host (`/home/susan/projects/RepliClaw/.artifacts/rcaeval/pilot`) contains the pilot data, so the canary was run from the worktree with an explicit `--data-root`. Flags verified first via `uv run python scripts/pilot_run.py canary --help` (subparser `canary` with `--data-root`, `--out`).

Command: `uv run python scripts/pilot_run.py canary --data-root /home/susan/projects/RepliClaw/.artifacts/rcaeval/pilot --out /tmp/ff03-canary` (exit 0)
Results (verbatim, per check): `PASS  both_arms_complete`, `PASS  payload_parity`, `PASS  scorer_path`, `PASS  label_gate`, `PASS  reset`. The two `[D-E-TELEM]`/`[C-EQ-TELEM] expected crash (label gate)` lines are the label gate's **intentional** negative checks (forbidden literal `re1ob_adservice_cpu_1` in a D-E payload → expected crash; manager two-consecutive-malformed action outputs → expected crash), not failures. Report: `/tmp/ff03-canary/canary_report.json`.

**VERDICT: PASS** — the D-E/C-EQ interface contamination canary (leak guards, payload parity, label gate, scorer-only resolve gate; subset 180 passed, 23 skipped, 3 xfailed; full suite `tests -q` 447 passed, 32 skipped, 3 xfailed) and the offline no-LLM pilot canary (both_arms_complete, payload_parity, scorer_path, label_gate, reset) both pass with no failures on 2026-10-11.

## 6. Signoff

**DRAFT — pending independent science signoff.** Pre-specified amendment path; frozen rules unchanged. No human approval claimed. This document and the single one-line erratum pointer are the complete, prospective correction of the null-model interpretation; they do not alter any frozen constant, rule, or archived review.
