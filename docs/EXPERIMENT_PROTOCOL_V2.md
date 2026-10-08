# EESS experiment protocol v2 — preregister before scoring
Status PROPOSED, 2026-10-08. Hypotheses and comparison definitions must be frozen in a timestamped version before final held-out runs. The experiments and positive effects below **have not been run**.

## Research questions
RQ1: Relative to a **matched-resource adaptive central manager** with equal evidence/tools and concurrency, does independent local choice yield more correct falsifiable root-cause conclusions or lower time/cost at fixed quality?
RQ2: Does **independent pre-outcome evidence escrow** improve false-consensus resistance or unique evidence coverage compared with the *same swarm* sharing early interpretations freely?
RQ3: Do published, verified observations induce autonomous **reallocation** (test-choice changes), rather than scripted follow-up?
RQ4: How do exploration/diversity policies compare to greedy EIG and random choice? Report non-superiority honestly.

## Cases and independent oracle
Hero case: simulated/controlled returns-policy RAG/assistant failure: retrieval omission/truncation, policy-conflict or target instruction failure, judge-rubric error. Clean counterfactual modifications with one-factor interventions, plus interaction case(s). Separately seek a real-world, non-implanted AI safety audit whose reason can be independently evidenced; do not pretend it has an exact oracle if not verified.
- Build frozen dataset version including scenario + allowed artifacts, interventions, external oracle **in a separate sealed evaluator path**; hash manifest and record splits before testing.
- Include clean non-failures, multiple plausible causes, multi-cause interactions, judge mistakes and intentionally ambiguous cases; report controlled vs uncontrolled.
- Small demo target: >=1 executed causal test chain, >=3 agents, >=1 evidence-induced dynamic pivot, >=1 unsupported competing explanation refuted and >=1 final regression scenario.
- Evaluation planning target: 12–24 heterogeneous *held-out controlled* cases plus 2+ seeds/case if budget permits. These are **targets not claims**; smaller sample must be disclosed with uncertainty and no significance theater.
- Never include \`truth\`, \`reference_truth\`, \`seeded_fault\`, \`fault\` metadata, evaluator notes or target answer in investigator's prompt, workspace or agent-visible tool response.

## Systems to compare
S0 strong single agent with matched aggregate tokens/time/tools/interventions.
S1 fixed DAG with truthful tool transfer.
S2 isolated parallel investigators with genuine simple vote/aggregation.
S3 centrally adaptive planner/manager (same shared evidence as swarm, same number of parallel experiment slots, same tool/cost cap).
S4 open-sharing decentralized swarm (AutoScientists-inspired shared-state local decisions; no escrow).
S5 EESS full (blind forecasts + verified evidence escrow + local choice).
A1 EESS no escrow; A2 no local reassignment (fixed/central follow-up); A3 random/diversity experiment choice; A4 no verified executable evidence if ethically allowed only as negative/control.
Optional original RepliClaw no swarm as separate existing-method control. Keep S3 primary comparator; don't stack the deck by crippling the manager.

## Mechanistic trace assertions
T1. Two agents with independent private beliefs produce canonical pre-outcome commitments before seeing each other's predicted results (hash, monotonic phase events; time/order verifiable in process tests).
T2. An agent can publish a need and a **different eligible agent** independently claims it through atomic lease + expiry + retry. Server cannot choose research question/rank scientific ideas.
T3. An intervention run emits machine-created run ID, git/config/content hashes, snapshot, stdout/stderr/error, cost, model and prompt/tool traces; reviewer can rerun it.
T4. A counterfactual evidence snapshot changes at least one agent's next ranked valid action or selected experiment for a reason derived from the observation, without injecting ground truth; log policy RNG.
T5. No peer unpublished hypothesis content is visible to independent agents. Public raw observations are permitted at defined phase boundaries.
T6. Agent action/experiment is not prescribed in a closed hard-coded switch in orchestrator.
T7. A credible alternative remains open and final report includes contrary data and budget/stall reason.
T8. Experiment results and evaluation labels are never model-self-certified.
T9. Repeated same case, independent seed/run ID, no shared output file overwrite.
T10. Failure, abstention, and negative-results paths run end-to-end.

## Outcomes and denominators
Primary **validated root-cause accuracy**: correct hypothesis set (partial/multi-cause tracked separately), based on controlled-intervention oracle, not judge model agreement. Primary **resource-matched advantage vs S3**: paired difference in correctness at equal cap *or* time/cost to equal validated quality, preregister one for headline and label others secondary.
Secondary: conditional false-accept among false causes; conditional false-refute among true causes; unresolved/abstain; verified experiment coverage; causal discrimination power; contamination/false-consensus rate (shared errors not unique IDs); pre/post selection changes; executed task overlap and diversity; budget, LLM tokens, tool calls, model cost, wall clock (control parallel compute).
Prequential forecast score: Brier/log score only when probability forecasts honestly elicited and evaluated; otherwise report binary prediction hit rate, label "heuristic" not calibration.
Uncertainty: paired bootstrap/CIs across **cases** where appropriate; report tiny-n limitations; pre-register multiple-testing handling or call results exploratory.
Fairness: comparable data/tools and total budget; manager and swarm equal concurrency; actual model prompts available; no special pre-coded answer for EESS; same evaluator blinded to strategy; compare success-at-cost frontier; full token/CPU/GPU costs.

## Reproducibility artifact contract
\`artifacts/science/<run_id>/manifest.json\`: case ID/split/oracle reference (evaluator only), model ID/version, seeds, source hash, git SHA, budget and exact commands.
\`events.jsonl\`: monotonically ordered phase, worker and evidence events.
\`claims.jsonl\`: hypothesis revisions, predictions, commitment hashes, reveal validations.
\`interventions/\`: frozen audit configs, actual commands, inputs/outputs and run hashes.
\`metrics.json\`: metric definitions and denominator counts.
\`comparison.md\`: observed run results, CIs, failures, caveats and independent reviewer signatures/links.
Avoid changing public API or filesystem structures until design spike checks existing models and RepliClaw/ScienceClaw/SimpleAudit reuse.

## Pre-registration acceptance
Scientific judge **must** approve a minimal held-out manifest and S3 parity before expensive scoring. A second independent reviewer verifies T1–T8 against real traces. Don't make a final public claim from old six-fixture toy artifacts.

## References
docs/EVIDENCE_ESCROW_SWARM.md; docs/PRIOR_ART_NOVELTY_GATE.md; Hans slides 3, 6–8, 10–11; official https://scienceclawhack.ai/.
