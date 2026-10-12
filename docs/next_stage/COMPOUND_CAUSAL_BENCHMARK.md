# CompoundCausal-32 — the custom problem family RepliClaw should try to solve

**Status:** Implemented, synthetic exploratory benchmark, NOT an observed RepliClaw win.
**Implementation:** `src/repliclaw/benchmarks/compound_causal/`.
**Isolation:** This benchmark is on its own integration branch. Do not rewrite the prior RCAEval results or the original frozen P08 study.

## Exactly what questions the dataset tests

**Question A — multi-cause discovery:** Can an agent identify **all** contributing failure factors when repairing one subsystem alone is insufficient? A top-5 service ranking is not the goal: agents must return a set of causes, not one plausible guess.

**Question B — causal interaction:** Can an agent distinguish `OR` (both broken subsystems must be repaired to resolve the incident) from `AND` (either subsystem's repair resolves the incident), using executed counterfactual experiments rather than interpreting logs? The simulator recomputes the response to each repair.

**Question C — distributed evidence:** When retrieval, tool, policy and judge observations are spread across four separately queryable channels, can independently committed investigators combine those clues better or faster than an equally empowered central manager that can query *all four channels*?

**Question D — false consensus and escrow:** Does sealing hypotheses and forecast probabilities *before* seeing experiment outcomes improve calibration and robustness over open sharing, or does it only add overhead? The API provides a timestamp/order-enforced commitment boundary; the agents must implement their own honest coordination and baseline comparisons.

**Question E — when NOT to use a swarm:** Are clean negative controls and one-obvious-cause cases cheaper and equally accurate with a strong central manager? A scientifically credible benchmark needs tasks on which RepliClaw can *lose*.

## Dataset / ground truth design

Exactly **32 independent synthetic worlds** per generated suite, randomized opaque IDs, balanced factorial design:

| Evidence | Cause regime | Cases | Oracle type |
| --- | --- | ---: | --- |
| shared | simple | 8 | 6 single-fault, 2 clean |
| distributed | simple | 8 | 6 single-fault, 2 clean |
| shared | compound | 8 | 4 OR pairs, 4 AND pairs |
| distributed | compound | 8 | 4 OR pairs, 4 AND pairs |

**Public agent-facing card:** neutral domain context (e.g. policy returns, accounts, payments), candidate factor names, channel names, budgets, and possibly the noisy initial channel signals in shared cases. No gold fault set, interaction type, stratum label, or seed is included. Signals can be false-positive or false-negative, so static observations are not a reliable oracle.

**Private evaluator-only gold:** planted fault set (among retrieval / tool_data / policy / judge), causal logic, evidence readings, and a private 128-bit nonce. The private file must be hosted outside any agent workspace or tool filesystem, preferably behind a separate trusted tool/evaluator process. Same-process Python access is NOT a secure sandbox.

**Interventions:** `intervene(repairs=[])` gives a baseline; `intervene(repairs=["retrieval"])` actively recomputes a repaired world; `intervene(repairs=["retrieval","judge"])` tests a compound repair. Six calls, four evidence-channel reads, and max two repaired factors per intervention, identical across all strategies. Results include a content-hashed receipt and an explicit tag `deterministic_synthetic_structural_intervention`. They are **simulation outcomes, not SimpleAudit target-LLM reruns or actual production faults**.

**Pre-outcome commitments:** `commit(agent_id, predicted_causes, planned_repairs, probability_incident)` returns a salted hash only. The commitment and its Brier score are revealed after the matching intervention executes. This enables but does not automatically prove independent reasoning/escrow benefit.

**Scoring:** exact hidden fault-set match; stricter exact fault-set + interaction-class match; abstention rate; optionally (from the runner's public_history + receipts) intervention count, channel reads, repeated/duplicate experiments, elapsed time, actual model tokens, and forecast Brier. Score **all attempts**, including failures. Never infer independent-case sample size from many LLM seeds on one world.

## Concrete problem archetypes

1. **Stale retrieval + incorrect judge reference (OR).** Repairing retrieval alone leaves the judge defect; repairing the judge alone leaves the retrieval failure; test both and discover the full set. (A candidate example; exact random pair assignments vary.)
2. **Policy conflict + unreliable tool data (AND).** Each repair independently removes the observed failure, so a single successful test does not identify the interaction.
3. **False evaluator alarm (single judge).** Target behavior may be acceptable; changing the evaluator alone resolves the reported incident.
4. **No true fault (clean negative control).** Noisy observations can still look suspicious; the correct causal answer is empty / no defect.
5. **Retrieval-only failure with shared evidence.** A central manager should plausibly be as good or cheaper; this is essential anti-cherry-pick control.
6. **Distributed contradictory evidence over policy, tool, retrieval and judge.** Investigator A's clue can conflict with B's; the winning strategy must spend interventions discriminatively and verify, not merely vote.
7. **Two independent faults requiring a paired repair (OR).** Single-factor interventions may seem ineffective and trigger false premature consensus that the failure is unfixable.
8. **A synergy case (AND).** Both conditions contribute, yet a single fix resolves; multiple tested counterfactuals and forecast revision reveal the interaction.

These are purpose-built **diagnostic regimes**, not observed benefits for RepliClaw. The synthetic structural equations are simplified monotone Boolean causal models. Real-world transfer requires executable target-system reruns (e.g. P08/SimpleAudit or a resettable AIOpsLab environment).

## Commands — no external dependencies

```bash
# From repo root, with package installed or PYTHONPATH=src.
PYTHONPATH=src python -m repliclaw.benchmarks.compound_causal generate \
  --out .artifacts/compound-causal-dev --seed 20261012

# Execute baseline + five real synthetic interventions on one generated case.
PYTHONPATH=src python -m repliclaw.benchmarks.compound_causal smoke \
  --root .artifacts/compound-causal-dev \
  --out .artifacts/compound-causal-dev/smoke-public-history.json

# Evaluator ONLY after predictions are frozen. File is JSONL:
# {"case_id":"CC-...", "predicted_causes":["retrieval","judge"], "predicted_logic":"or"}
PYTHONPATH=src python -m repliclaw.benchmarks.compound_causal score \
  --root .artifacts/compound-causal-dev --predictions /path/to/frozen_predictions.jsonl \
  --out /path/to/private_scores.json

# Fresh prospective local suite: OMIT seed; store private/ outside agent access.
PYTHONPATH=src python -m repliclaw.benchmarks.compound_causal generate \
  --out /private/evaluator-only/compound-causal-fresh

# Fast scoped check
pytest -q tests/benchmarks/test_compound_causal.py
```

## Experiment design (not automatically run by the dataset)

Strategies: strong adaptive central manager (may read *all* channels and run experiments in parallel), D-E escrow swarm, D-N open-sharing swarm, optionally random adaptive experiment choice. Same tool menu, same simulated intervention budget, same actual model/token/time caps. Only compare within the same evidence/complexity cell; model the 2x2 interaction instead of cherry-picking compound/distributed cells.

For a quick *development* run, use these generated cards openly and inspect trajectories. For confirmatory claims, freeze a fresh private generator seed and keep gold inaccessible to all agent tool contexts; new human-approved spend/prereg/signoff rules still apply. Always record generator commit and raw receipts.

**Kill criterion:** If the adaptive central manager is as accurate and cheaper in compound/distributed cases, RepliClaw has not demonstrated a coordination advantage. The benchmark is still a useful scientific result. Do not edit cases or heuristics in response to heldout outcomes.
