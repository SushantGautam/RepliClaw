# V3 DRAFT — externally benchmarked intervention-matched RepliClaw experiments

Status: **PROPOSED, NOT PREREGISTERED, NOT APPROVED FOR LIVE CAMPAIGN**; prepared 2026-10-09. A frozen, timestamped V3 + independent Science-Judge sign-off + explicit human authorization are mandatory before holdout/live experiments. P08 files and measurements remain immutable; do not revise old P08 results.

## Primary causal question and estimand (interactive track I)

For independent fault scenarios (not repeated model rolls on one case), at a fixed per-case action/token/time/intervention **cap**, compare:
- **D-E (RepliClaw)**: decentralized investigator choice + independent pre-outcome escrow + shared verified observations.
- **C-EQ (intervention-matched adaptive centralized manager)**: an honestly strong central planner coordinating the same number of investigators and same permissible diagnostic/intervention tools, including adaptivity after each observation; no artificial fixed script.
**Primary estimand:** case-level paired difference in successful root-cause diagnosis, D-E minus C-EQ, aggregated with equal case weighting. Failed or abstained trials count as non-success for the primary ITT metric. Run-level seeds are nested within cases; case—not sample rollout—is the unit for CI/generalization.

**Decision rule to freeze BEFORE heldout:** meaningful positive if a paired cluster bootstrap 95% CI of the per-case difference lies entirely above zero; otherwise not established. This is a design proposal, NOT a currently established victory. Report effect and interval regardless. Pin bootstrap RNG/replicate count before final. Specify multiplicity approach for any co-primary outcomes; all others descriptive or multiplicity-adjusted. Do not claim a powered null-equivalence test without preplanned equivalence margin/power.

## Secondary mechanism arms (all can intervene in track I)

- **D-N**: same decentralized action/selection policy but no escrow (pass-through).
- **D-R**: escrow intact but random admissible next-test selection (seeded), subject to identical constraints.
- **C-NE**: centralized manager without escrow, standard strong baseline; C-EQ by default uses best-performing fair central protocol and the same observational timing; do NOT impose artificial escrow on central just to make names symmetrical.
- **S-I**: strong single investigator, can run same causal tools; tokens/tool-call cap equal, note parallelism as an intrinsic architectural effect.
- Optional **C-OracleSelection** (upper-bound selection-only diagnostic) NOT leaderboard entry and NEVER allowed oracle during a primary run; may be computed only in evaluator after all runs.
- **No-intervention** arm is explanatory only, NOT the main fairness comparator; label it explicitly as mechanism-access contrast.
- **CAR** replay comparator only when faithful replay semantics, action set and outcomes are genuinely identical; otherwise report a separate CAR protocol.

Main hypotheses: H1 D-E improves case-level root-cause success vs C-EQ; H2 D-E vs D-N changes false consensus, independent forecast disagreement and detection/recovery on ambiguity; H3 D-E vs D-R improves verified information gain / causal discrimination per intervention; H4 D-E vs C-EQ improves efficiency or cost-to-quality under comparable ceilings. H1 is primary; freeze metric names, denominators and signs. Negative/null results fully acceptable.

## Benchmark tracks: do not mix estimands

### O-A: AgentRx observational generalization
- Use the released dataset labels for critical-step localization and released taxonomy category, not five-way P08 labels.
- Reproduce original AgentRx first where permitted, plus same-model zero-shot/CoT prompting, trace-only strong central and RepliClaw's multi-investigator observational variant.
- No executable intervention => RepliClaw escrow/selection mechanisms can be measured as process, **cannot** claim benefits from counterfactual execution or head-to-head causal control.
- Register exact accessible subset; official HF microsoft/AgentRx requires human click-through access; paper 115 trajectories may not equal any mirror; document coverage. Evaluate classification + critical-step accuracy with official scripts if present and inspect annotation agreement and inconclusives.
- Do not use test labels in adaptive prompts; no benchmark item IDs in prompts if they can retrieve published answers.

### O-R: RCAEval observational transfer
- Original official root-cause service/fault indicator and ranking top-k, Avg@5 where applicable. Use original evaluator and run at least one named official RCA baseline (BARO or suitable multi-source baseline) with *the same cases*.
- Start with a **stratified representative pilot** across service, fault type and microservice system; selection manifest frozen before reading labels. Then expand to multiple systems/suites to assess generalization.
- Dataset is recorded fault-injection telemetry; running code over traces does NOT mean counterfactual experiment on that historical incident.
- Telemetry quotas, context windows and retrieval must be matched. Different access modalities (metrics-only vs logs+traces) are separate subtasks.

### I: AIOpsLab executable counterfactual diagnosis
- Choose only built-in registered detection/localization/diagnosis problems with documented labels/evaluators. Reuse official Orchestrator; do not invent truth labels.
- **Feasibility barrier:** prove deterministic-equivalent restart/snapshot, independent isolate per arm, replay observation fidelity, ability to run controlled alternative interventions safely, per-arm identical interface, and evaluator oracle not agent visible. AIOpsLab supplies injection but does NOT automatically guarantee meaningful reversible causal replay for any specific problem.
- Intervention matching means matching **available action vocabulary, authorization, max number of tests, environment reset state, cumulative compute budget, information timing and simulator access**; not forcing both strategies to choose the same intervention in every run (selection is the treatment). Add a separate **fixed evidence tape** test for pure aggregation/escrow effects: same intervention results disclosed to all arms in a randomized standardized order.
- Capture observed output changes + unchanged-input/byte identity controls; separate correlations from causal claims when assumptions fail.

## Scientific design

- Candidate **pilot**: 6–10 independent cases with 2 seeds each; ~4-6 arms; pilot is for feasibility/variance, **not confirmatory**. No "p < .05" claims from pilot; pilot cases segregated from final case-level test.
- Candidate **heldout**: target ≥24 distinct cases across ≥3 fault families and ≥2 systems with 2–3 predeclared seeds per case, if attainable. These are **planning targets not commitments or power proof**; independent statistician to estimate variance/power from pilot (not test), choose feasible target and lock exact N.
- Blocking/randomization: paired strategies run same case+seed and frozen upstream scenario; counterbalance execution order and isolate namespaces/workspaces; no shared cache, messages, oracle, directories or mutable service state. Record randomization order and reruns.
- Leakage: evaluator-only answers encrypted/isolated or stored outside agent context; scan prompts/retrieval/tools/artifacts. Benchmarks may be in training data, so measure contamination risks, not assert perfect secrecy.
- **Cost accounting**: total tokens (input/output/cached, where known), provider billable tokens, tool invocations, intervention count and cost, total GPU/CPU seconds, wall clock, queueing, recovery cost. A cap is NOT equal spend; include accuracy-at-cost and tokens-to-correct-conclusion curves.
- **Timeouts and failures**: pre-register unambiguous abort/error/abstain handling; include failures in ITT denominator, optionally report clean-run sensitivity separately; keep retries bounded and auditable.
- **Statistical analysis**: equal weighting by independent case; paired differences by case+seed, cluster bootstrap over cases with all seeds attached, confidence intervals. No run-level bootstrap as generalization claim; stratified faults/domains as predeclared; report raw case-level predictions and confusion matrices, practical significance, abstention and negative findings.
- **Falsification and calibration**: count correct refutation across *multiple* unsupported hypotheses/cases (avoid P08 near-vacuous denominator=1); record pre-outcome test forecasts and proper Brier score only where probabilistic, otherwise report hit rate honestly.
- **Scientific process**: quantify actual evidence-induced policy pivot, independent agent diversity, false-consensus, evidence sharing, experiment coverage, causal discrimination vs random/EIG, and treatment leakage.
- **No hindsight fixes**: failed metric definitions trigger transparent versioned amendment with severity/sign-off; do not tune prompts/scorers after observing heldout outcomes.

## Standardized outputs and evaluator contract

Canonical per-case outputs must preserve original labels and original benchmark evaluator; add an additive RepliClaw metadata sidecar without replacing official benchmark score. At minimum:
- benchmark/version/sha/license/source/split, case ID, domain/fault family, oracle ref (evaluator-only), strata
- model exact ID, serving config, temperature, seed, endpoint provider alias (NO credentials), prompt SHA, git SHA
- strategy, intervention executor and allowed action schema hash, budget cap and actual spend, concurrency, case reset hash
- per-agent commitments/hypotheses, shared evidence events, intervention choices + valid responses, decision/recovery timestamps
- diagnosis + uncertainty + abstention + root-cause rank where supported, validation receipts
- status/errors/retry history and reasoned negative results
- official metric score, novel secondary metrics and case-level paired score by independent sealed scorer

Test invariants before any holdout: same action schema and executor for D-E vs C-EQ, same budget/concurrency, scorer blind to arm and inaccessible during run, no preloading gold in prompts, reset stability, controlled error case, all outputs idempotent and resume safe. Fixtures ≠ real measurements.

## Execution governance and honest stop rules

G0 upstream contract/access/license review approved; G1 benchmark's own evaluator/strong baseline runs successfully; G2 intervention-matching and oracle-isolation canaries pass; G3 pilot and independent review pass; G4 V3 prereg frozen + science key APPROVE + explicit human key for exact benchmark/arms/N/model/spend; G5 heldout scored only at permitted step; G6 independent Code/Science judges review counterevidence and claims; G7 public release only by public-readiness gate.

If G1/G2 fail, **STOP that track** and document blocker; keep work in independent tracks. No "just simulate it" replacement inside an external-benchmark result. Never silently downgrade to unverified synthetic cases. No full live campaign, paid cluster deployment or >pilot token spend without explicit human authorization.

## Reproducibility procedure

1. Pin source versions, contracts and baseline commands; save manifest (no dataset leakage into git).
2. Build read-only adapters and sealed evaluator; write canary integration tests.
3. Produce one reproducible official baseline case and one cross-strategy parity case with independent review.
4. Run strictly bounded pilot; freeze revised prereg/holdout and obtain two keys.
5. Run paired heldout matrix, separately monitor execution integrity without inspecting interim advantage.
6. Score with canonical evaluator; publish all failure cases and uncertainty; if H1 unsupported, pivot questions rather than fabricate success.

## Relation to previous stage

P08 documents remain historically valid; **DO NOT** overwrite P08 score, silently change prereg v1.2, relabel previous P1 as proof of decentralization, or conflate a 120-rollout *single case* with 120 independent cases. This protocol creates **new prospective estimands** and independent results.
