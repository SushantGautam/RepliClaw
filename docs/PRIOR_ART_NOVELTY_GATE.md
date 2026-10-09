# Novelty gate — no wheel reinvented (2026-10-08)
Status: preliminary targeted prior-art review, not proof of an unclaimed invention. Before claiming "first", run a broader paper/code/implementation search and get skeptical independent science review.

## Closest, most dangerous prior work
| Work | Already does | What our proposed experiment must contribute beyond it |
|---|---|---|
| **AutoScientists** (Gao, Fang, Zitnik, May 2026; arXiv:2605.28655; github.com/mims-harvard/AutoScientists) | **Decentralized** long-running agents self-organize around hypotheses, share experimental state, reallocate/reorganize, run controlled budget experiments with ablations. Its stated results include cross-domain scientific optimization. Directly overlaps Hans's core decentralized swarm. | Scientific **causal attribution of AI failure** with controlled competing interventions + sealed *pre-outcome* predictions, evidence escrow, source-traceable diagnosis, explicitly measured social contagion; show which mechanisms help relative to AutoScientists-inspired open-sharing policy. Never pitch local task choice alone as novel. |
| **Co-Scientist** (Google DeepMind, Nature May 2026; doi:10.1038/s41586-026-10644-y) | Asynchronous specialized agent coalition, debate/tournaments/reflection/evolution; central supervisor and empirical validations. | Independent prequential diagnostic interventions, evidence exchange protocol and transparent local reallocation, rather than another hypothesis tournament. |
| **Robin** (FutureHouse, Nature May 2026; doi:10.1038/s41586-026-10652-y) | End-to-end iterative scientific hypothesis, experiment design, data analysis and updated hypotheses. | Reproducible automated *AI-failure* interventions, trust/independence and controlled comparison of decentralized science vs adaptive central manager. |
| **AgentRx** (Microsoft Research, March 2026; github.com/microsoft/AgentRx) | Debugging agent trajectories by executable constraint checks, fault localization and classification; benchmark of failed trajectories. | Active **counterfactual experiments** that distinguish causal alternatives across audited runs, not merely localizing critical steps from a fixed trajectory. Reuse its taxonomy/tests where appropriate; compare against trajectory-only diagnosis when feasible. |
| **SimpleAudit / RepliClaw existing** | Scenario auditing, model comparisons, blind commit/reveal integrity, CLI verify and evidence-weighted verdict path. | Reuse these; add actual local task choice, executed interventions and controlled generalization. Baseline 6 deterministic toy cases are not a scientific result. |
| **Experiment-selection theory** (Dubova et al., 2026, doi:10.1177/26339137261421577) | Random experiment selection can outperform purely theory-confirming/falsifying choices in a studied multi-agent model. | Include cheap random/diversity baselines and don't assume greedy information gain wins. |
| **Causal Agent Replay (CAR)** (arXiv:2606.08275, 2026-06-06, github.com/jaineet17/causal-agent-replay) — **ADDED 2026-10-09 by independent re-audit (docs/reviews/PRIOR-ART-REAUDIT-20261009.md); material overlap with element (b)** | Intervene on a **frozen recorded agent run** and re-execute under the same stochastic policy, with a full intervention algebra (`do_resample`/`do_action`/`do_observation`/`do_context`/`do_policy`), budget-bounded Shapley attribution, confidence intervals. | CAR is **single-agent, step-level, on the agent's own trajectory**; EESS targets **external system factors of an audited AI system (retrieval / policy-instruction / evaluator-judge) via competing multi-agent hypotheses over a frozen SimpleAudit artifact**. State this difference explicitly; NEVER claim "first counterfactual/intervention-based causal diagnosis of agent failure". |
| **Preregistration for Experiments with AI Agents** (arXiv:2606.11217, ICML 2026) — ADDED 2026-10-09 | Argues agent experiments must commit before reveal (human-facing template). | Our (a) stands only as **hashed packets + phase-boundary sealed reveal + tamper detection + machine-scored forecasts**; always qualify as *sealed, escrow-gated, machine-verified* pre-outcome commitments — never "first pre-outcome prediction". |
| **zkAgent** (IACR ePrint 2026/199) + **VIGIL: Verify-Before-Commit** (ACL 2026) + **P2PCLAW/OpenCLAW-P2P v7.0** (arXiv:2604.19792) — ADDED 2026-10-09, LOW weight | SNARK-verified agent execution (zkAgent); prompt-injection verify-before-commit protocol (VIGIL — name-collision hazard only); decentralized peer-review/publishing network (P2PCLAW — self-published, low evidentiary weight). | One-sentence footnote each; do not weight. Avoid unqualified "novel commit/reveal protocol" or "machine-verified agent execution" wording — specify *research-forecast escrow*. |

## Prohibited novelty claims
- "First decentralized AI scientist", "first agent swarm doing hypothesis generation", "first self-organizing scientist", "first scientific multi-agent debate" — contradicted by documented prior work.
- **"First counterfactual / intervention-based causal diagnosis of agent failure" — contradicted by CAR (arXiv:2606.08275, added 2026-10-09) + AgentRx's executable constraint checks.**
- **"First pre-outcome / preregistered prediction in agent experiments" — contradicted by the ICML-2026 preregistration position paper (arXiv:2606.11217) + AutoScientists' public `prediction`/`falsification` fields.**
- **Unqualified "novel commit/reveal protocol" or "machine-verified agent execution" — VIGIL (ACL 2026) + zkAgent (IACR 2026/199); specify *research-forecast escrow*.**
- "Proven to beat central workflows" — not yet empirically supported by RepliClaw live demo.
- "Cryptographic guarantees of reasoning independence" — a hash proves later consistency of a packet, not isolation, secrecy or epistemic independence.
- "Actual causal proof" from LLM opinions alone — require controlled interventions and limitations.
- Novel algorithms claimed without theoretical/experimental novelty evidence.

## Candidate defensible contribution (conditional)
**Evidence-escrow + prequential counterfactual investigation**: independent, time-ordered hypothesis/forecast commitments *before* peers' interpretations and intervention outputs are revealed; verified SimpleAudit interventions and shared evidence lead to independently chosen next tests. Test whether this prevents false consensus and improves *measured* causal diagnosis quality/efficiency.
The originality may be in the rigorous *combination, application and evaluation*, not new atomic primitives; characterize claims accordingly. Alternative title if novelty weak: "A controlled empirical study of evidence escrow and decentralization in agentic AI auditing." This is scientifically defensible even if no superiority.

## Kill gates and team decision
N0 Literature check: 4+ primary papers/repositories above, current implementations, summarized direct overlap and honest claims.
N1 Mechanism check: experiments exhibit at least one genuine non-scripted evidence-driven agent reallocation and verified pre-outcome commit. If not, demonstrate architecture as exploratory and avoid claims.
N2 Result check: on blinded held-out controlled cases, measure meaningful effect or honest failure relative to adaptive central manager and independent/open-sharing variants.
N3 Demo check: show what additional knowledge the system created; a pretty swarm animation alone fails.
N4 Review check: skeptic must be able to argue this is an AutoScientists clone. Provide a specific mechanism, provenance, measured difference or narrow domain finding that rebuts it.
If none passes within the campaign window (original gate date 2026-10-15), prioritize a smaller legitimate science-audit result for publication, not an unfinished platform.

## Primary sources checked 2026-10-08
- https://arxiv.org/abs/2605.28655
- https://github.com/mims-harvard/AutoScientists
- https://www.nature.com/articles/s41586-026-10644-y
- https://www.nature.com/articles/s41586-026-10652-y
- https://www.microsoft.com/en-us/research/blog/systematic-debugging-for-ai-agents-introducing-the-agentrx-framework/
- https://github.com/microsoft/AgentRx
- https://journals.sagepub.com/doi/10.1177/26339137261421577
