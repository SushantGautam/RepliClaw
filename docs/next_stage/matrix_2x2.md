# 2×2 experimental matrix — evidence architecture × cause structure

Short and executable. Claim strengths stay separated: observational cells
make an **access-matched diagnosis** claim only; executable-counterfactual
cells make a **causal-mechanism** claim. Never merge across classes in one
aggregate row (the scorecard enforces this).

## Cells

| | SINGLE cause | COMPOUND cause |
|---|---|---|
| **SHARED evidence** | C-EQ-TELEM (manager owns the union view) — observational | C-EQ (P08 intervention executor, manager-owned) — executable |
| **DISTRIBUTED evidence** | D-E-TELEM (3 private investigators, escrow commit-reveal) — observational | D-E (independent investigators, per-agent counterfactual slots) — executable |

## Per-cell spec

### Cell 1 — SHARED × SINGLE (observational)
- Arms: `C-EQ-TELEM` (`src/repliclaw/experiments/v3/telemetry_arms.py`).
- Cases: existing RCAEval pilot roster `RCA-P-01..10` (`data/cases.parquet`,
  hash-verified) or the 150K single-case runs; reuse existing artifacts where
  present — do not rerun unchanged.
- Metrics: top-1, exact-set (vs 1-element GT), Jaccard, completion,
  tokens, wall, time-to-verdict, premature stops, false consensus, protocol
  violations. Verified interventions: N/A.
- Decision question: does a single manager over the shared union view beat
  the distributed committee on correct completions per token, within the
  same observational access? (Cell 1 vs Cell 2, paired at case level.)

### Cell 2 — DISTRIBUTED × SINGLE (observational)
- Arms: `D-E-TELEM` (same module; 3 private sandboxes + escrow + committee).
- Cases: same set as Cell 1 (paired).
- Metrics: identical to Cell 1.
- Decision question: is the phase-1 sequential bottleneck a real cost — i.e.
  do completion rate / time-to-verdict / tokens differ from Cell 1 on
  identical cases?

### Cell 3 — SHARED × COMPOUND (executable-counterfactual)
- Arms: `C-EQ` (`src/repliclaw/experiments/v3/ceq.py`, P08 executor).
- Cases: the new compound-causal cases (2 co-occurring injected causes) being
  built in the causal lane; must be genuinely unexposed to experiment tuning.
  Until ≥1 case runs: report as pending, not as zero evidence.
- Metrics: top-1 + exact-set + Jaccard **against the full GT cause set**,
  verified-intervention fraction (executed slots verified + flipped GT),
  completion, cost, failure rates.
- Decision question: with compound causes, does the centralized planner
  verify a counterfactual that flips the GT, and at what cost? A single
  working case is a one-case mechanism demo, not a multi-case effect.

### Cell 4 — DISTRIBUTED × COMPOUND (executable-counterfactual)
- Arms: `D-E` (`eess_live` arm via the same P08 executor; same reset/
  snapshot, caps, scorer as Cell 3).
- Cases: same compound set as Cell 3 (paired with Cell 3).
- Metrics: identical to Cell 3, including per-investigator verified
  interventions.
- Decision question: does decentralized investigation with per-agent
  counterfactual slots verify interventions on compound causes that the
  centralized planner misses (or vice versa), at matched cost?

## Global rules
- Pair analysis is at CASE level, within one evidence class only.
- Non-completions are failures, never dropped; `aborted_budget` is a frozen
  outcome, `crashed` is a harness failure — both reported separately.
- Log per run: repo SHA, model id, case id + hash, seed, caps, tokens, wall.
- Scorecard: `python -m repliclaw.experiments.v3.scorecard <out_root>
  --truth <truth.json> --json out.json --md out.md`
  (run dirs = anything containing `status.json`, `final_verdict.json`, or a
  generic `run.json` with `evidence_class`).
- No p-values from reused exploratory cases; if only the old P08 case works
  in Cell 3, the result is a one-case demo and must be labeled as such.
