# RepliClaw — public project description & FAQ (draft)
**Status: DRAFT ONLY / NOT PUBLISHED / TEAM DETAILS TO CONFIRM.** Prepared 2026-10-08. (This document began life as an event application draft; the project is now an independent public research project, and this file is kept as the canonical public description and FAQ.) No "100% guaranteed" outcome exists; this version is written against published criteria and avoids fabricated results.

## Naming
Project: **RepliClaw: an Evidence-Escrow Scientific Swarm**
Short claim: "Autonomous scientists that predict before they believe, intervene before they conclude, and show which evidence changed their minds."
Challenge area: decentralized scientific collectives / open scientific challenge.
Keep Hans's Decentralized Hypothesis Swarm attribution in team docs.

## Problem statement
AI systems can fail for multiple plausible reasons—wrong retrieval, conflicting instructions, flawed reasoning, or even a mistaken evaluator—yet existing audits often report a score without discovering which mechanism actually caused the failure. A single confident explanation can be wrong; a group of agents sharing early conclusions can amplify that mistake. We propose RepliClaw, a decentralized scientific investigation collective that diagnoses AI failures through independently predicted, executable counterfactual tests. Agents create competing falsifiable hypotheses, commit to expected outcomes before seeing peers' unpublished findings, run controlled experiments, and publish verified evidence that changes what other agents choose to investigate. Using SimpleAudit, we will demonstrate a reproducible investigation of an AI failure, distinguish rival root-cause explanations using controlled interventions, and produce a portable regression test and provenance-backed report. The underlying scientific problem is whether autonomous evidence-driven coordination improves *validated explanations* rather than just increasing persuasive agreement.

## What we have built so far
Our team combines AI-safety and multimodal-AI research, auditing infrastructure, agent engineering, and scientific/product design. At SimulaMet, we have developed SimpleAudit and SimpleAuditStudio for reproducible AI-system auditing, with scenario-based evaluation, run tracking and evidence analysis. We also have an initial working RepliClaw prototype with independent investigators, hash-based commitment/reveal, evidence-linked verdicts, a CLI verification surface and deterministic tests/benchmarks. Those are foundations rather than proof of scientific superiority: existing toy cases are limited and our saved live-model comparison does **not** yet demonstrate an advantage. We will reuse that tested infrastructure rather than spend the campaign rebuilding an orchestration platform, focusing effort on real executable interventions, autonomous evidence-dependent decisions and rigorous validation. [Before publication: confirm exact teammate backgrounds and achievements; insert concrete, independently verifiable public links rather than unsupported metrics.]

## Why a decentralized agent collective?
A trustworthy diagnosis needs competing causal explanations tested without premature convergence. Different agents can specialize in retrieval, policy reasoning, evaluator validity and statistical testing, with distinct tools and partial knowledge. One agent's controlled experiment changes the value of experiments other agents are considering; decentralized agents can locally decide to replicate, falsify, or explore alternatives instead of following a fixed DAG. We introduce *evidence escrow*: agents commit to their predictions independently, publish only execution-verified results to a shared ledger, and then choose their next experiments from the updated evidence. A shared service controls budgets and atomic task claims but never prescribes the research trajectory. We will directly compare against a strong **adaptive central manager** with the same evidence, tools, concurrency and budget, as well as single-agent and open-sharing swarms. Ablations will tell us whether independent commitments and local selection actually help; if not, we will report the limitation.

## Team capabilities
Relevant, confirmed team capabilities: AI / Machine Learning; Agentic Systems; Software / Coding; Data Science; Scientific Research / Experimentation; optionally Product / Entrepreneurship or Design / UX **only for actual team member skills**. Do not invent backgrounds.

## Complementary expertise sought
A collaborator with experimental-design/causal-inference expertise, red-team evaluation, or a scientific domain with controlled reproducible interventions would strengthen independent validation and external stress-testing. We also welcome external teams to use our portable verification endpoint, which would test whether our component contributes beyond this project.

## Publication verification checklist — do not fabricate
- [ ] Confirm every contributor's consent and public attribution details.
- [ ] Review all long-form descriptions for accuracy; no invented prizes, titles, benchmark wins or external users.
- [ ] Clearly distinguish work **already built** from work **proposed next**.
- [ ] Add a demonstrable technical proof/link if public and safe.
- [ ] Verify every claim against reproducible artifacts before release, with human confirmation.
- [ ] Preserve confirmation/receipt records in private storage (no personal data in public repo).
- [ ] Before ANY result is reported: fold the P1 attribution disclosures (A9.4 / S-1 / N-2 / R-2 — `docs/application/P1_RESULT_DISCLOSURES_DRAFT.md`, science-round-3 MUST-1) into the result statement per `docs/DEMO_AND_FINAL_HANDIN_V2.md` § "P1 result statement — mandatory disclosures".
Do not assert publication or release until it actually happens.

## Claim-boundary guardrail (mandatory per science round 3, A9.4/C7 — 2026-10-09)
Any result statement (project description update, demo, or final report) MUST:
1. Attribute a P1-SUPPORTED outcome (if reached) to the **counterfactual-intervention identifiability mechanism** on the **single seeded case** `policy_rag_v1` — **not** to "decentralized autonomy" or "decentralization" in the abstract.
2. Disclose the base-case **retrieval-vs-judge confound** (base data alone cannot distinguish `retrieval_omission` from `judge_stale` — both point at 14 days; only the S5 interventions I_R/I_J/I_P disambiguate), so a comparator scoring M1 ≈ 0 is a valid scientific result, not "starvation".
3. Disclose that M1 is a **5-way exact-match classification** with the shared defect taxonomy given to ALL arms equally (a menu, not the answer), and that this is a **single seeded case — no generalization**, no "autonomy beats central workflows" claim.
Full text: `docs/application/P1_RESULT_DISCLOSURES_DRAFT.md` (S-1 deterministic-arm fixture stand-in; N-2 strategy budget-ledger granularity; R-2 token floors).
