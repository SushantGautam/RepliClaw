# Active plan v2 — RepliClaw Evidence-Escrow Scientific Swarm
Revision 2026-10-08; **proposal pending team alignment, NOT a guarantee of winning**. This plan supersedes v1 task sequencing after safe checkpoint/migration. Source scope: Hans's Oct 7 slide deck (shared HTML), ScienceClaw official 2026 rubric and submission, recent primary prior art, existing RepliClaw implementation.

## Research mission and novelty guard
**Core experiment**: decentralized agents form and independently precommit predictions about competing explanations for an AI system failure, execute frozen SimpleAudit counterfactuals, publish evidence, and self-allocate subsequent experiments. Demonstrate actual evidence-induced choice changes under a controlled comparison against a **strong adaptive central manager**. Read docs/EVIDENCE_ESCROW_SWARM.md and docs/PRIOR_ART_NOVELTY_GATE.md before implementing. AutoScientists 2026 already does decentralized scientific search; do not claim that alone as new.

## Immediate rule for agents already running the old seed
Do not cancel their uncommitted work blindly. First send the checkpoint prompt in docs/AGENT_MIGRATION.md. Migration owner inventories live sessions/worktrees/WIP and maps old tickets. A new v2 seed is in SEED_PROMPT_V2.md; root SEED_PROMPT.md also points there. Single writer for state, reviews and merges.

## Priority board / wave schedule
| Ticket | Priority / Wave | Owner lane / paths (indicative) | Dependencies | Acceptance: observed trace, not narrative | Current status |
|---|---|---|---|---|---|
| P00 migrate & G0 | CRITICAL / NOW | orchestrator; docs/checkpoints, state only | pre-pivot checkpoint | salvage WIP inventory, current HEAD, pytest/ruff/mypy results with command and real output; note unknown sessions | NOT_STARTED |
| P01 novelty and contracts | CRITICAL / NOW | read-only science reviewer + technical architect; docs/design | none | review AutoScientists, Co-Scientist, Robin, AgentRx, ScienceClaw primitives; predeclare accepted vocabulary, schema contracts and benchmark parity | NOT_STARTED |
| P02 frozen SimpleAudit causal experiment | CRITICAL / A | separate worker; new adapters + experiments tests | P00, minimal P01 contract | counterfactual control actually changes one experimental variable; machine-produced hashes/logs; clean replay; actual causal alternatives | NOT_STARTED |
| P03 hypotheses, forecasts, escrow | CRITICAL / A | separate worker; new schema/ledger modules + tests | P01 | versioned H/claims/outcomes, per-agent pre-outcome SHA commitments, monotonic events, pre-reveal isolation negative tests, verified reveal | NOT_STARTED |
| P04 autonomous local choice & ScienceClaw need market | CRITICAL / A/B | design spike first, then independent worker; need/discovery modules | P01, P03 minimal interface | real different agent claims via atomic lease/retry; no central role chooser; snapshot replay changes agent-ranked choice after evidence | NOT_STARTED |
| P05 fair strong comparators | CRITICAL / A | existing F01/F03 WIP worker lane; strategy/bench tests | P00 | actual open-debate contexts, true vote, strong equal-concurrency S3 adaptive manager, real cost caps, parity proofs | NOT_STARTED |
| P06 controlled and held-out cases | CRITICAL / A | science/data worker; experiments/fixtures, sealed evaluator | P01,P02 design | same allowed information all strategies; evaluator oracle truly inaccessible; distinct retrieval/reasoning/judge faults; known data rights | NOT_STARTED |
| P07 integrate full vertical slice | CRITICAL / B | integration owner; cross-module glue | P02,P03,P04,P06 | 3+ agents; commit→execute→verified reveal→dynamic task choice→validated output→counterevidence/stop reason | NOT_STARTED |
| P08 real experimental baselines and ablations | CRITICAL / B | experiment engineer + science judge | P05,P06,P07 | preregistered S0/S3/S4/S5, no-escrow and random policy, negative findings preserved, sample/CI/denominator truth | NOT_STARTED |
| P09 application package | CRITICAL / A | human team review; docs/APPLICATION_V2.md | P01, team agreement | exact three mandatory answers, verified biographies/links, deadline Oct 16, actual submission confirmation from human; not an agent-autosubmit | NOT_STARTED |
| P10 reproducibility/demo | HIGH / C | demo worker + code/science judges | P07,P08 | fresh install, saved replay, authentic live bounded run, 3–4 minute *proposed* narrative, inspectable timestamps and artifacts | NOT_STARTED |
| P11 external-team reuse | HIGH/BONUS / C | small integration worker | P07 | verified another team runs CLI/API and benefits; otherwise mark not achieved | NOT_STARTED |
| P12 event final submission | CRITICAL / EVENT | human/lead | P09,P10 | official latest final instructions verified; packaging/upload as specified; evidence and limitations; do not invent form/time | NOT_STARTED |

## Old WIP salvage map
- old F00 → P00, old F01 → P05, old F02 → P02, old F03 → P05/P08, old F04/F06 → P04, old F05 → P06 (old molecular case may remain secondary), old F07 → P03, old F08 → P08, old F09 → P11, old F10 → P09/P10/P12.
- Preserve source changes already made, assign contracts based on actual live diff; if worker implements a useful feature, finish its failing test rather than making it redo architecture.
- No concurrent code changes to overlapping paths. Freeze minimal interface contracts before parallel editing. ~3 editing workers plus read-only science/code judges and sole integration owner is a default, not a rigid cap.
- The docs in this PR are a **proposal**; Hans's team has not been documented as accepting it.

## Contract for agent assignment
Every ticket must have worker/session/worktree/branch/starting SHA, exact owned and forbidden paths, red/green tests, precise API/schema, budget, measurable acceptance, artifacts path, reviewer and merge strategy. If the harness cannot spawn independent worktree editing agents, implement sequentially and say so.
Suggested lanes: builder-a P02; builder-b P03; builder-c P05; read-only reviewer P01; design-only P04; data-science P06 separate branch when slots permit. Integration uses objective gates; single status writer.

## Milestones / verification checkpoints
G0 baseline: snapshot git and prior work; run actual tests; freeze old bench validity limitations.
G1 scientific/design gate: signed architecture and novel-candidate statement; case/oracle leakage prevention; strong S3 comparator spec.
G2 first causal intervention: repeatable SimpleAudit input change → actual output and stored traces, independent code review.
G3 reliable evidence escrow: two agents independently precommit before peer information; tamper/phase tests.
G4 genuine local agency: different worker claims need without central allocator; evidence-injection replay changes agent choice and produces trace.
G5 scientific validity: blinded controlled cases, S3 parity and no-escrow comparison, meaningful primary endpoint and honest intervals; science judge.
G6 end-to-end demo/submission: external rerun, real case regression, no fabricated claims, final official hand-in procedure checked.
After **every** gate save docs/checkpoints/CP-<date>-<ticket>.md with SHA, commands, observed outputs, negative findings, old/new mapping and next action, update PROGRESS.md append-only, and compact EXECUTION_STATE.md. If gates fail, correct issue; never weaken tests.

## Decision deadlines
- Oct 08–10: migrate and select one demonstrably differentiable root-cause case; submit team-aligned project framing early if available.
- Oct 11–15: first demonstrable causal loop, application review/submission (early deadline Oct 16), local choice prototype and baselines.
- Oct 16–23: fair held-out comparisons, upgrades for credible results, partner outreach.
- Oct 24–29: clean replay, reviewers, backup video, final guide; verify organizer instructions.
- Oct 30–Nov 01: ScienceClaw event and final deliverables.

## Cut scope aggressively if behind
P02 + P03 + P04 + P05 + P07 + one real controlled case + application before optional nice-to-have. If decentralized autonomy doesn't really emerge, report limits and prioritize a valid empirical result. Do not shift to broad Tox21 or due diligence unless there's a completed credible case and team approval. No blockchain or dashboards.

## Necessary provenance
- Official competition: https://scienceclawhack.ai/
- Application: https://scienceclawhack.ai/apply.html
- Prior work: https://arxiv.org/abs/2605.28655 ; https://www.nature.com/articles/s41586-026-10644-y ; https://www.nature.com/articles/s41586-026-10652-y ; https://github.com/microsoft/AgentRx
