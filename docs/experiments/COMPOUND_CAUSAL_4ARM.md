# CompoundCausal-32 Four-Arm Experimental Protocol

Version: 1.0 (frozen). Benchmark: `src/repliclaw/benchmarks/compound_causal/core.py`
(`compound_causal_32/v1`, 32 cases, balanced 2x2: {shared, distributed} x {simple, compound}).
Development dataset: `.artifacts/compound-causal-dev` (seed 20261012, already generated;
fixed seed is development-only — never publish it as a heldout claim).

## 1. Arms (identical tool access and budgets for all)

Every arm interacts with each case **only** through `BenchmarkSession` methods
`card()`, `observe(channel)` [max 4 reads], `commit(agent_id, predicted_causes,
planned_repairs, probability_incident)` [seals pre-outcome forecast],
`intervene(repairs)` [max 6 interventions, max 2 repairs each], and
`public_history()`. No arm may read gold, oracles, simulator internals, or another
arm's session state.

1. **adaptive_central** — mandatory strong S3 comparator. Single decision loop /
   one manager agent (`agent_id="central"`). Sequential counterfactual experiment
   design: after each `intervene()` outcome it updates its belief state, then either
   commits a new falsifiable forecast via `commit()` before the next planned
   intervention or terminates. Must commit at least one forecast per case before
   first intervention where a non-trivial hypothesis exists.
2. **replclaw_escrow** — decentralized evidence-escrow RepliClaw, **N=4 agents**
   (`agent_id="rc-a".."rc-d"`). Each agent commits blind sealed forecasts via
   `session.commit()`; experiments are executed only **after** commitment (the
   session enforces this); outcomes are revealed post-experiment via
   `revealed_forecasts`. Follow-up experiment choices are reallocated among agents
   based on revealed evidence (evidence-driven handoff of the "next experiment"
   role). Agents share no conclusions before reveal.
3. **open_sharing** — same N=4 agents, but every agent sees prior agents' revealed
   conclusions (their committed packets once revealed, plus their textual
   conclusions shared openly in the shared transcript) before acting. `commit()`
   is still called identically; there is no escrow sealing discipline — sharing
   precedes further action.
4. **random** — seeded random selection from the same legal action space
   (`random.Random(20261012 + case_index)`): random channels for `observe`, random
   repair subsets (size 0–2) for `intervene`, random submissions. Same budgets.

All arms run all 32 cases. One fresh `BenchmarkSession` per (arm, case).

## 2. Fixed case priority order

Cases are processed in this stratum order (order within a stratum = file order in
`public/cases.jsonl`):

1. `distributed/compound` (8)
2. `distributed/simple` (8)
3. `shared/compound` (8)
4. `shared/simple` (8) — controls last.

Stratum labels come from the private gold (`stratum` field) which the **orchestrator
(harness)** may use to order cases; strategies themselves never see strata. The
harness writes the fixed ordered case list to
`.artifacts/compound-causal-4arm/case_order.json` before any arm runs.

## 3. Submission schema (per case, frozen)

Each arm emits exactly one submission per case, appended to
`predictions/<arm>.jsonl` **before** scoring is invoked:

```json
{"case_id": "CC-...", "predicted_causes": ["retrieval"], "predicted_logic": "single"}
```

- `predicted_causes`: subset of `["retrieval","tool_data","policy","judge"]`,
  sorted by that canonical order, no duplicates.
- `predicted_logic`: one of `clean | single | or | and | abstain`.
- `abstain` = "no defect / cannot conclude"; must be paired with empty
  `predicted_causes`. Any other logic pairs with a non-empty cause set consistent
  with the logic (`single`: 1 cause; `or`/`and`: 2 causes).

Freeze rule: predictions files are closed (read-only) before the scoring step;
scoring uses `score_predictions()` only.

## 4. Metrics (exact definitions)

Per case, per arm:

1. **exact_cause_set**: `set(predicted_causes) == set(gold.hidden_causes)` AND
   `predicted_logic != "abstain"`.
2. **interaction_correct**: on gold `causal_logic in {"or","and"}` cases,
   `predicted_logic == gold.causal_logic` (AND vs OR specifically identified).
   Reported as correct/total over the 16 compound-interaction cases.
3. **abstention_correct**: on gold `clean` cases, `predicted_logic == "abstain"`.
   **false_conclusion**: on gold `clean` cases, `predicted_logic != "abstain"`;
   additionally counted separately as `wrong_nonclean` when a non-clean case gets a
   cause-set or logic mismatch. Primary accuracy metric:
   `cause_and_logic_exact` (both match), reported overall and per stratum.
4. **forecast_brier**: mean Brier score over all *committed and revealed*
   forecasts in `public_history().revealed_forecasts` (i.e., forecasts whose
   `planned_repairs` were actually executed), averaged per case then across cases.
   Cases with zero revealed forecasts contribute 0 and are tracked as
   `no_forecast_cases`. Also report `forecasts_committed` count per arm.
5. **experiment_count**: number of `intervene()` calls per case (summed per arm).
   **duplication_rate**: fraction of interventions (across an arm's cases) whose
   `(case_id, tuple(sorted(repairs)))` repeats an earlier identical intervention
   in the same case.
6. **tokens_proxy** (deterministic proxy, NOT LLM usage): fixed cost per API call
   type — `observe`=50, `commit`=80, `intervene`=120, `final_submission`=100.
   Summed over all calls per case and per arm. Documented clearly as a proxy for
   interaction volume.
7. **wall_clock_ms**: wall-clock time from session creation to frozen submission,
   measured by the harness per (arm, case).
8. **completion_rate**: fraction of 32 cases where the arm produced a valid frozen
   submission passing schema validation. Target: 1.0 for all arms; any failure is
   a protocol bug to fix, not a score.

## 5. Isolation rules

- `private/oracles.jsonl` (and `channel_evidence` beyond what `observe()` returns)
  is readable **only** by the scoring step and the case-ordering orchestrator.
  Never mounted in any strategy workspace, never imported by strategy code.
- Strategies operate solely through `BenchmarkSession`; the trusted host exports
  method results only.
- Predictions are frozen to JSONL (files made read-only) **before**
  `score_predictions()` runs. Scorer raises on duplicate/unknown case IDs.
- Arms never share sessions, RNGs, or process memory.

## 6. Anti-tuning rule

No case-specific tuning, no per-case-id branching, no iteration on this dev
dataset until results are written to `report.md` verbatim. Negative and null
results are reported as-is. Strategy code is version-pinned (git SHA recorded in
`scores.json`) before the run starts.

## 7. Artifacts layout

```
.artifacts/compound-causal-4arm/
  case_order.json                 # fixed stratum-ordered case list
  predictions/
    adaptive_central.jsonl        # one submission per line, frozen
    replclaw_escrow.jsonl
    open_sharing.jsonl
    random.jsonl
  traces/
    <arm>/<case_id>.json          # public_history() snapshot + wall_clock_ms + tokens_proxy
  scores.json                     # score_predictions() output per arm + metric tables + git SHAs
  report.md                       # final results table, verbatim metrics, limitations
```

## 8. Execution notes

- Harness pseudocode: for arm in ARMS: for case in case_order: create session →
  run arm policy → validate+freeze submission → save trace → (after all arms)
  score. Random arm seed: `20261012 + index_in_case_order`.
- A valid `commit()` requires the planned intervention not yet executed in that
  case; escrow arm should exploit this by committing before executing.
- `intervene([])` (repair nothing) is legal and useful as a baseline probe;
  allowed for all arms.
- Budget exhaustion raises `ValueError`; arms must catch and submit best-effort.
