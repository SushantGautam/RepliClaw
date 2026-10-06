# RCAEval lane (observational track O-R)

Pinned upstream: `phamquiluan/RCAEval` @ `259ea4167160256a74ad30004aa3d96a998c846e`
(735 cases: RE1 375 / RE2 270 / RE3 90). See `docs/next_stage/adapters/rcaeval_contract.md`.

## What this is

RCAEval is an **observational (O-R) track**: each case is a *recorded failure
episode* (metrics/logs/traces captured after a fault was injected). A recorded
failure is **NOT counterfactual replay** — the system cannot be re-run with a
different candidate root cause, so no counterfactual intervention claims are
supported from this lane alone.

## W1 / J-SCI A6: heldout CANDIDATE manifest (not frozen)

Science judge finding F7 (SCIENCE_JUDGE_WAVE0_20261009, amendment A6): the
heldout must span RE1/RE2/RE3. A baseline that scores 1.0 on the cheapest
RE1-CPU stratum is an easy-stratum smoke, not evidence of generalization.

The selection rule is frozen in `manifest.py` (`QUOTA_TABLE`, seed `20261009`
reserved; ordering is total — lowest repetition first, case-name tie-break,
services alphabetical) and is **label-mask-safe**: `select_heldout_cases`
touches only the stratum columns (`suite`, `system`, `root_cause_service`,
`fault`, `repetition`, `dataset`); the annotation column
(`fault_description`) is read only by the scorer, and
`tests/benchmarks/test_rcaeval_strata.py` proves the selection is invariant
when all non-stratum columns are masked to NaN or shuffled.

**Quota table (42 heldout candidate cases):**

| suite | system | fault | per-service cap | cases |
|-------|--------|-------|-----------------|-------|
| RE1   | OB     | mem   | 2               | 10    |
| RE2   | OB     | cpu   | 2               | 10    |
| RE2   | OB     | mem   | 2               | 10    |
| RE3   | SS     | f1    | 2               | 6     |
| RE3   | SS     | f3    | 2               | 6     |

This manifest is a **CANDIDATE, pending freeze at gate G4**. Downloaded case
files (142 files, 209.5 MiB, per-file sha256) live in
`.artifacts/rcaeval/download_manifest.json` (excluded from git).

## Baseline smokes — stratum feasibility, not generalization

| run | stratum | Avg@5 | Chance@5 | Lift@5 | status |
|-----|---------|-------|----------|--------|--------|
| L2  | RE1-OB cpu, 10 cases | 1.00 | 0.23 | 0.77 | easy-stratum smoke |
| W1  | RE2-OB cpu, 10 cases | **0.66** | 0.25 | **0.41** | easy-stratum smoke |

**Caveat (both rows):** single-stratum, 10-case feasibility/variance data
points from the official BARO baseline (metrics-only mode, CPU). They are NOT
generalization claims and NOT heldout evaluations. Notably the RE2-CPU stratum
already drops BARO well below saturation (5/10 cases miss), which is the
expected signature of a non-trivial stratum. Run log:
`.artifacts/rcaeval/baro_re2ob_cpu_smoke.log`
(sha256 `9293ede0051e8164ceb51e2e8411f9ce297033a1d6b798687172565afcd29012`).

## Tests

`tests/benchmarks/test_rcaeval_strata.py` — cases.parquet hash verify
(`c49a2889…`), 735-case counts, selection/stratum checks, label-mask
invariance, determinism under row/column reordering, CaseManifest round-trip.
Requires pyarrow ≥ 25 (contract §2 quirk); fixture: `data/cases.parquet`.
