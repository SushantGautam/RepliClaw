# RepliClaw: Evidence-Escrow Scientific Swarm (EESS)
Status: PROPOSED RESEARCH DIRECTION, 2026-10-08. **No novel performance result or scientific advantage is claimed yet.**
Owners: team to confirm with Hans, Michael, Sushant. Respect Hans's original "Decentralized Hypothesis Swarm" concept and authorship; this is an integration proposal, not an agreed team decision.

## High-stakes question
Can independently reasoning scientific agents **causally diagnose why an AI system fails**—not merely guess or agree—by committing to competing predictions, running reproducible counterfactual experiments, exchanging only authenticated observations, and choosing follow-up investigations locally? Under an equal budget, does this produce better validated explanations, fewer false-consensus failures, or faster decisions than a strong adaptive central manager?

## One-line pitch
**A swarm that must predict before it believes, experiment before it concludes, and show exactly which evidence changed its mind.**

## Essential scientific insight: evidence sharing vs epistemic independence
- Hans (slides 2, 3, 6, 7): agents share a living evidence map; local priorities adapt while other agents investigate. Static DAGs and a strong adaptive manager are the necessary comparators.
- RepliClaw prototype: independent investigators, hash commitments, evidence and verdicts; however currently centrally fulfilled follow-ups, context-only isolation, unfair baselines and toy evaluation.
- Combined novel *candidate*, not novel-by-declaration: an **evidence-escrow protocol for decentralized causal investigation** in which preliminary hypotheses/predictions remain private until independently committed; execution-verified observations then enter a common ledger and change autonomous next-action selection. Study whether preventing premature social influence changes scientific reliability while permitting efficient information sharing.

## Specific mechanism — agents self-direct, not a hidden central planner
Run a fixed, documented AI failure case with >=3 plausible and experimentally distinguishable causes.
1. **Initial problem and hidden evaluator**: Provide only complaint, relevant public system artifacts and allowed tools. Keep oracle causes, implanted faults and held-out labels in evaluator-only storage (never in prompts, evidence map or agent tools).
2. **Hypothesis proposals**: H1/H2/H3 are explicit falsifiable statements. Record predictions for alternative interventions. Require concrete observation that would refute each hypothesis, not just narratives.
3. **Before seeing a peer's unpublished finding**, each investigator privately commits a canonical packet: hypothesis ID/version, proposed intervention, predicted outcomes / discriminating evidence, estimated cost, competing explanation and prior evidence snapshot hash. Publish only commitment hash/time until the phase boundary. Signature/secure timestamp if practical; SHA-256 alone proves content integrity, not trusted wall-clock ordering, independent cognition or process isolation.
4. **Local experiment selection**: Each worker reads public verified evidence + published unmet needs; estimates experiment utility for itself, considers alternative-hypothesis coverage, duplication/crowding, cost and epistemic uncertainty; selects or claims a task using an atomic lease. Service **enforces** duplicate/lease/budget rules but does **not rank scientific options or assign questions**. Agents can reject tasks, propose competing tasks or choose diverse strategies. Track why each chose its experiment and what new observation changed that choice. Explicit counterfactual replay from same evidence snapshot allows checking that evidence changes priorities.
5. **Actual interventions**: Execute through frozen SimpleAudit runs or an equally reproducible runner. First use a controlled policy-retrieval assistant fixture; manipulate only one factor at a time: relevant document presence, retrieved snippet order, instruction conflict, evaluator rubric/ground-truth reference (without contaminating target); compare target outputs and auditor judgments. Obtain hashes, configs, seeds, tool traces, logs and results from the runner; ignore LLM-self-reported "executable=true".
6. **Publish observed evidence** with data lineage, run IDs, independent reproducibility flag and scope. After reveal verify commitments and preserve original predictions. Do not rewrite hindsight predictions. Promote evidence to public only after objective checks; unsupported interpretations remain hypotheses.
7. **Reallocation**: Others independently respond to evidence by picking a new experiment or continuing a rival hypothesis. Show at least one *observed* evidence-induced pivot, not a hand-scripted stage. Track no-change choices and redundant pursuits too.
8. **Resolve or abstain**: Output supported / contradicted / unresolved hypotheses and provenance, effect sizes/uncertainty, counterevidence, budget/stall stop reason and next unanswered need. "Confidence" is a heuristic unless validated/calibrated.

## Candidate experiment-choice policy (test, do not assume optimal)
A transparent local utility heuristic might be:
  U_i(a) = EIG_i(a | verified public evidence) / estimated_cost(a)
           + λ * diversity_or_dissent_bonus(a)
           - μ * duplicate_or_crowding_penalty(a)
subject to agent-owned expertise/tool constraints and global resource limits.
EIG means estimated expected reduction in uncertainty over competing hypotheses, **not** simply entropy of a model response. LLM forecasts require calibration checks; a random/exploration policy is a mandatory cheap comparator because greedily confirming leading hypotheses can bias discovery.
Compare this with:
- no utility scoring (random valid action);
- greedy shared global score (non-agent-specific);
- an adaptive central manager with exactly the same interventions, evidence and limits.
Do not call this utility formula novel. The specific scientific contribution must be demonstrated by comparative evidence and credible literature differentiation.

## Scope control: what to build for the event
**Hero vertical slice**: policy/return-advice assistant failure with controlled retrieval and judge interventions, *plus* a second held-out AI-audit case of a different failure family if feasible. A live public-real case (not implanted) is desirable but separate labeled from controlled truth-set. Convert checked findings into repeatable SimpleAudit regression scenarios.
Must show: different agents, independent predictions/commitments, true verified experiment output, shared evidence, an unscripted subsequent choice, bounded cost, final supported/contradicted/unresolved explanations, and a successful comparison trial.
Do not scope-creep to general business due diligence, full literature scientist, blockchain, fancy UI, new database, permanent distributed infrastructure, physical wet lab or unvalidated cross-domain claims.

## High-value novel proof (observable, falsifiable)
- Agents are *not* identical "lenses": distinct data/tool capability, hypothesis ownership or allowed experiments.
- Real autonomous decision: counterfactual replay of an evidence-map snapshot alters task preference/claim; a test asserts the difference, not a hard-coded follow-up.
- Prequential prediction: record what agent predicted **before** intervention result (pre-reveal); score forecast against actual result.
- Honest intervention: changing retrieval/policy/judge factor affects observed outcome and competing explanations, with relevant confound controls.
- Causal role of blind commitments: run *no-escrow* ablation with same compute to detect premature convergence / duplicated experiments, rather than asserting it helps.
- ScienceClaw native "unmet need" objects/ArtifactReactor can mediate shared tasks, no bespoke coordination platform unless necessary.
- Third-party entrypoint: a tiny independently usable audit/verification API, with usage measured only if an external team really uses it.

## Failure conditions (equally valuable scientifically)
If the centrally managed baseline is equally strong at lower cost, report that decentralization offered no observed benefit on the tested workload. If public sharing worsens correlated errors, report and test escrow effect. If agents don't change choices following evidence, the project **has not demonstrated adaptive decentralization**. If experiments cannot distinguish hypotheses, label them unresolved rather than manufacturing a plausible root cause.

## Rubric evidence obligations
Problem significance 20%: high-impact AI failure diagnosis; Impact 25%: confirmed counterfactual failure finding and executable regression; Decentralized agency 20%: autonomous task choice + verified leases/pivots; Collective capability 25%: budget-matched baseline and ablations; Execution 10%: reproducible audit; +10 possible from actual other-team reuse. Official https://scienceclawhack.ai/ (accessed 2026-10-08).

## Origin
Hans Christian Ekne, *Suggestion for Hackathon Project: Decentralized hypothesis swarm*, slides 2–8, 10–11 and speaker notes (2026-10-07 HTML shared by team); existing RepliClaw code/prototype reviewed 2026-10-08. Do not treat the slides as implemented or team-approved.
