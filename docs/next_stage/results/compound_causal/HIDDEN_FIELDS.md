# Compound-causal cases — what is hidden from the agent

Lane: `lane-compound-causal` (base commit `c33715e`, dev). This page documents
exactly which fields are sealed (never visible to a target/investigator) and
where the ground truth lives, for the two new cases verified by `run_verification.py`.

## Oracle isolation (same rule as P02/P06 contract §6)

- The sealed ground truth lives in each case's `oracle/oracle.json` and is
  read by **exactly one module**: the case's `judge.py`
  (`flowmeter_single_cause/judge.py`, `drift_sign_and/judge.py`), invoked only
  through `Case.judge_arm`. No arm code path (`data/`, `case.py`) references
  the oracle file.
- The judge's in-memory judgment carries the sealed fields for internal
  validation, but `Case.public_judgment_drop` (per case) names them and
  `_base.persist_arm` / `_base.write_case_manifest` strip them before any
  byte is persisted. The verifier's leak-check re-scans every persisted
  artifact for those field names and fails on any hit (0 hits recorded in
  `verification_matrix.json`).

## Case `flowmeter_single_cause_v1` — SINGLE-CAUSE

Frozen input (visible): `data/meter_window.json` (sha256
`b619445bf76764b5ae7b779aeac4ab366fcf64fcc2905f7657378f3f5a0377b1`) — 14 days
of pulse counts + the meter's own dropped-event counter (0 all window) + log
lines. All per-arm configs and measured outputs are visible.

**Hidden (oracle-only, stripped from all persisted artifacts):**

| field | meaning |
|---|---|
| `true_cause` | `stale_pulse_calibration` — the ONE injected latent cause |
| `cause_set` | `["stale_pulse_calibration"]` |
| `injected_defect` | defect id + description (shipped 0.0472 vs correct 0.05 L/count) |
| `expected_total_liters` | 101417.35 (2028347 pulses × 0.05) |
| `tolerance_abs_liters` | 0.5 |
| `abs_diff` | |measured − expected| (would let an agent invert the expected value) |
| `per_arm_expected_outcome` | pre-declared pass/fail per arm |
| `oracle_schema` | `repliclaw.sealed_oracle/v1` marker |

Note: the correct calibration value 0.05 L/count is *visible* in the
`I1_fix_calibration` arm config (documented firmware 3.4.1 release note) —
what is sealed is which defect was injected and the ground-truth outcome.

## Case `drift_sign_and_v1` — COMPOUND (AND-interaction)

Frozen input (visible): `data/batch_assay.json` (sha256
`cbd0982a3dfb1bec1ce4c995022d7dcab1826771218174713caaffe1f21408a4`) — 32
samples with `raw_counts` and per-sample `reference_drift_counts` (nonzero,
uncalibrated state) + log lines. Gain `k = 96.0` counts/(µg/mL) is visible in
every arm config.

**Hidden (oracle-only, stripped from all persisted artifacts):**

| field | meaning |
|---|---|
| `true_cause` | `correction_sign_error AND uncalibrated_instrument` |
| `cause_set` | `["correction_sign_error", "uncalibrated_instrument"]` |
| `injected_defects` | both defect ids + descriptions |
| `expected_mean_concentration` | 479.706706 µg/mL (healthy-pipeline truth) |
| `tolerance_abs_umg_ml` | 0.05 |
| `abs_diff` | as above |
| `per_arm_expected_outcome` | pre-declared pass/fail per arm |
| `oracle_schema` | marker |

## Verified causal structure (observed, seed 0 — see `verification_matrix.md`)

| case | arm | observed |
|---|---|---|
| flowmeter_single_cause_v1 | I0_baseline (as-shipped) | **mismatch** (95737.9784 L vs sealed 101417.35 L) |
| flowmeter_single_cause_v1 | I1_fix_calibration (fix THE cause) | **pass** (101417.35 L) |
| flowmeter_single_cause_v1 | I2_account_dropped (non-cause, no-op on data) | **mismatch** (95737.9784 L) |
| drift_sign_and_v1 | I0_baseline (both causes) | **mismatch** (485.178711 µg/mL) |
| drift_sign_and_v1 | I1_fix_sign (fix A only; B present) | **pass** (479.706706 µg/mL) |
| drift_sign_and_v1 | I2_recalibrate (fix B only; A present) | **pass** (479.706706 µg/mL) |
| drift_sign_and_v1 | I3_fix_both (sanity) | **pass** (479.706706 µg/mL) |

Replay authenticity: both cases `True` (stored artifacts match pinned
sha256 AND a clean re-execution reproduces every pinned hash).

## Freshness

Both cases are new data (deterministic LCG generation, seeds 20261012/20261013,
2026-10-12) in new domains (flow-meter totalization; QC batch-assay drift).
They were never used in any prior experiment round; the frozen P08 case
(`policy_rag_v1`) and P06 case (`tox21_ar_agonist_v1`) are untouched and not
re-exposed.
