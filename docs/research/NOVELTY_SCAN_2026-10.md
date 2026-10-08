# Novelty Scan — RepliClaw EESS (ScienceClaw 2026)

**Date:** 2026-10-08
**Scope:** Prior-art survey of autonomous-scientist / LLM-scientist agent systems and the closest threats to our claimed contribution.

**Our claimed novel mechanism (the thing we must defend):** independent scientific agents that (1) commit to pre-outcome falsifiable predictions in a tamper-evident escrow ledger, (2) run real SimpleAudit counterfactual interventions, (3) share only verified evidence, and (4) autonomously choose the next experiment from a decentralized need market with local (non-central) ranking — then measure the *difference* this makes against (a) a strong adaptive central manager, (b) an open-sharing swarm without escrow, and (c) a single agent.

**The novelty claim is specifically:** PRE-OUTCOME ESCROW + COUNTERFACTUAL INTERVENTIONS + MEASURED DIFFERENCE vs these baselines. We explicitly do **not** claim "decentralized swarms are new" (they are not).

---

## ⚠️ 2025–2026 items that could materially weaken our claim (flagged)

1. **"Preregistration for Experiments with AI Agents" (arXiv:2606.11217, 2026).** This is the single closest conceptual neighbor to our "pre-outcome commitment" idea. **However, it is a *methodology/standards* paper, not a system.** It argues AI-agent experiments should be pre-registered to curb "researcher degrees of freedom," and proposes pre-registration *templates* for journals/funders. It does **not** implement a tamper-evident escrow ledger, does **not** run counterfactual interventions, does **not** coordinate multiple agents, and does **not** measure a difference against baselines. It is a *normative* contribution; ours is a *mechanism + measurement* contribution. This is our strongest prior-art threat and must be cited and distinguished.

2. **"Falsifiable Commitment Planning for Self-Correcting Web Agents" (arXiv:2607.24167, 2026).** Uses the phrase "falsifiable commitment" for agents, but in the *web-agent self-correction* setting (agents commit to falsifiable sub-goals to detect and correct their own errors mid-task). It is a single-agent planning/self-correction technique, **not** a multi-agent escrow ledger, **not** counterfactual experimental intervention, and **not** a decentralized experiment-selection market. Overlaps on the word "falsifiable commitment" only; the mechanism and domain are different.

3. **Prediction-market-for-AI-agents industry activity (2025–2026, e.g., Chainlink, Gnosis, Polymarket/Kalshi AI agents).** These are *financial* prediction markets where AI agents trade on event outcomes. They are commitment devices in the economic sense but operate on *market price* signals, not on *pre-outcome falsifiable scientific predictions escrowed against experimental results*, and they do not run counterfactual interventions or select experiments. Relevant to cite as "adjacent, not the same mechanism."

**Bottom line:** No surveyed system combines all four of our elements. The two 2026 papers (2606.11217, 2607.24167) are the ones to cite and explicitly distinguish; neither implements the escrow+counterfactual+measured-difference mechanism.

---

## Per-system comparison table

| System | Venue / URL | Date | Mechanism (what it does) | Explicit gap vs our escrow + counterfactual + measured-difference contribution |
|---|---|---|---|---|
| **The AI Scientist (v1)** — Sakana AI / Oxford / UBC | arXiv:2408.06292 — https://arxiv.org/abs/2408.06292 | Aug 2024 | End-to-end single-agent pipeline: idea generation → code → experiments → manuscript → automated peer review. Produces full ML papers for <$15. | Single agent, no inter-agent commitment, no escrow ledger, no counterfactual interventions, no experiment-selection market, no measured comparison against decentralized/central baselines. |
| **The AI Scientist-v2** — FutureHouse | arXiv:2504.08066 — https://arxiv.org/abs/2504.08066 | Apr 2025 | Workshop-level automated discovery via **agentic tree search**; iterative experiment loops, code execution, paper writing. | Centralized agentic search, not a decentralized multi-agent market; no pre-outcome escrow of falsifiable predictions; no counterfactual intervention step; no measured difference vs baselines. |
| **Robin** — FutureHouse / Oxford / Fordham | arXiv:2505.13400 — https://arxiv.org/abs/2505.13400 ; Nature 2026 — https://www.nature.com/articles/s41586-026-10652-y ; GitHub — https://github.com/Future-House/robin | May 2025 (arXiv); Nature 2026 | **Multi-agent** scientific discovery: orchestrator + specialist sub-agents (Crow/Falcon for literature, Finch for analysis) run a lab-in-the-loop loop (lit review → hypothesis → experiment design → data analysis → refine). Demonstrated on dry-AMD / ripasudil. | **Centralized orchestrator** coordinates specialists — the opposite of our decentralized need market. No pre-outcome falsifiable predictions escrowed in a tamper-evident ledger; no counterfactual interventions; no measured difference vs central/open-swarm/single baselines. (This is the most prominent "Robin" for AI scientific agents; see note below.) |
| **Google AI co-scientist** | arXiv:2502.18864 — https://arxiv.org/abs/2502.18864 | Feb 2025 | Gemini-based multi-agent "co-scientist" for drug discovery: hypothesis generation, tournament-style ranking of hypotheses, iterative refinement with human-in-the-loop. | Centralized tournament/ranking of hypotheses by a coordinating model; no pre-outcome escrow ledger; no counterfactual interventions; no decentralized experiment-selection market; no measured difference vs baselines. |
| **Kosmos** — "An AI Scientist for Autonomous Discovery" | arXiv:2511.02824 — https://arxiv.org/abs/2511.02824 ; GitHub — https://github.com/jimmc414/Kosmos | Nov 2025 | Long-horizon autonomous agent (up to ~12h / 200 rollouts) with a **structured world model** shared between a data-analysis agent and a literature-search agent; cited, traceable reports. | A *single coordinated* agent with a shared world model, not independent agents with a decentralized need market; no pre-outcome escrow of falsifiable predictions; no counterfactual interventions; no measured difference vs baselines. |
| **AgentRx** — LLM agents for multimodal clinical prediction | arXiv:2605.10286 — https://arxiv.org/abs/2605.10286 ; PMLR v333 — https://proceedings.mlr.press/v333/al-jorf26a.html | 2026 (AHLI 2026) | Benchmark study of LLM agents for multimodal clinical (MIMIC/ICU) prediction; compares **single-agent vs multi-agent** frameworks. Finds single-agent outperforms naive multi-agent. | A *benchmark*, not a discovery system. No escrow ledger, no counterfactual interventions, no experiment-selection market. Notably, its finding that naive multi-agent underperforms single-agent is *motivating* for our measured-difference framing (we must show our mechanism beats the naive baseline). |
| **AIOS** — LLM Agent Operating System | arXiv:2403.16971 — https://arxiv.org/abs/2403.16971 ; GitHub — https://github.com/agiresearch/AIOS | Mar 2024 | OS-like kernel for LLM agents: scheduling, context/memory management, access control; SDK "Cerebrum." Up to 2.1× serving speedup. | An *infrastructure/serving* layer, not a scientific-discovery or commitment mechanism. No pre-outcome escrow, no counterfactual interventions, no experiment-selection market. |
| **ChemCrow** | arXiv:2304.05376 — https://arxiv.org/abs/2304.05376 ; Nat. Mach. Intell. 2024 | Apr 2023 | LLM augmented with 18 chemistry tools; plans/executes syntheses. | Single-agent tool-augmented LLM; no multi-agent commitment, no escrow, no counterfactual interventions, no market-based experiment selection. |
| **AgentNet** — Decentralized Evolutionary Coordination for LLM Multi-Agent Systems | arXiv:2504.00587 — https://arxiv.org/abs/2504.00587 (NeurIPS 2025) | Apr 2025 | Fully **decentralized** multi-agent coordination via a dynamically evolving DAG + RAG-enhanced memories; agents specialize and evolve without central orchestration. | **Closest on the "decentralized" axis.** But it is a general task-coordination framework, not a *scientific* system: no pre-outcome falsifiable predictions, no escrow ledger, no counterfactual interventions, no experiment-selection need market, no measured scientific-outcome difference. This is why we must NOT claim decentralization as novel. |

> **Note on "Robin":** The most prominent public "Robin" for AI scientific agents is **FutureHouse's Robin** (arXiv:2505.13400, Nature 2026). There is no other widely-cited autonomous-research agent named "Robin" that supersedes it. I treat FutureHouse Robin as the intended referent.

---

## Closest prior art (ranked, 3 nearest threats)

1. **Preregistration for Experiments with AI Agents (arXiv:2606.11217, 2026)** — *nearest on the "pre-outcome commitment" axis.* It formalizes why AI-agent experiments need pre-registration (to bound researcher degrees of freedom) and proposes templates. **What it does NOT do:** it is a standards/methodology paper — it does not build a tamper-evident escrow ledger, does not run counterfactual interventions, does not coordinate multiple independent agents, and does not measure a difference against central/open-swarm/single baselines. Our contribution is the *mechanism and the measurement*; theirs is the *normative argument*. Cite it as the motivation our system operationalizes.

2. **AgentNet (arXiv:2504.00587, NeurIPS 2025)** — *nearest on the "decentralized multi-agent" axis.* A genuinely decentralized LLM multi-agent coordination framework (evolving DAG, no central orchestrator). **What it does NOT do:** it is not a scientific-discovery system; it has no pre-outcome falsifiable predictions, no escrow ledger, no counterfactual interventions, and no experiment-selection need market with local ranking. It confirms decentralization is prior art (so we don't claim it) while leaving our escrow+counterfactual+measured-difference combination open.

3. **Falsifiable Commitment Planning for Self-Correcting Web Agents (arXiv:2607.24167, 2026)** — *nearest on the "falsifiable commitment" phrasing.* Agents commit to falsifiable sub-goals to self-correct. **What it does NOT do:** single-agent web-task self-correction; no multi-agent escrow ledger, no counterfactual experimental interventions, no decentralized experiment-selection market, no measured difference vs baselines. Overlaps only on terminology.

**Honorable mention:** Robin (arXiv:2505.13400) and Google co-scientist (arXiv:2502.18864) are the most prominent *scientific* multi-agent systems, but both are **centrally coordinated** (orchestrator / tournament), which is the opposite of our decentralized need market, and neither has escrow, counterfactual interventions, or measured-difference baselines.

---

## Recommended novelty paragraph (drop-in, ~250 words)

> Across the surveyed autonomous-scientist and LLM-scientist systems — The AI Scientist (arXiv:2408.06292) and AI Scientist-v2 (arXiv:2504.08066), Robin (arXiv:2505.13400), the Google AI co-scientist (arXiv:2502.18864), Kosmos (arXiv:2511.02824), AgentRx (arXiv:2605.10286), AIOS (arXiv:2403.16971), ChemCrow (arXiv:2304.05376), and the decentralized coordination framework AgentNet (arXiv:2504.00587) — none combines the four mechanisms we study. Existing scientific agents are either single-agent pipelines (AI Scientist, ChemCrow, Kosmos) or centrally coordinated multi-agent systems (Robin's orchestrator, the co-scientist's hypothesis tournament), and none escrows pre-outcome falsifiable predictions in a tamper-evident ledger, runs counterfactual interventions, or measures the resulting difference against baselines. The two nearest 2026 works address only one axis each: "Preregistration for Experiments with AI Agents" (arXiv:2606.11217) makes a normative case for pre-registering AI experiments but builds no escrow mechanism, runs no counterfactual interventions, and coordinates no agents; "Falsifiable Commitment Planning for Self-Correcting Web Agents" (arXiv:2607.24167) uses falsifiable commitments for single-agent self-correction, not for multi-agent scientific verification. AgentNet (arXiv:2504.00587) demonstrates decentralized LLM coordination but in a general task setting, not science, and without prediction escrow or counterfactual intervention. Our contribution is therefore the specific conjunction — pre-outcome escrow of falsifiable predictions, counterfactual interventions, verified-evidence sharing, and decentralized local experiment-selection — **together with a measured difference** against a strong adaptive central manager, an open-sharing swarm without escrow, and a single agent. We do not claim decentralization itself is new; we claim the escrow + counterfactual + measured-difference combination is, to the extent covered by the surveyed systems.

---

## Full source list (all URLs verified to resolve)

1. The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery — https://arxiv.org/abs/2408.06292 (Aug 2024)
2. The AI Scientist-v2: Workshop-Level Automated Scientific Discovery via Agentic Tree Search — https://arxiv.org/abs/2504.08066 (Apr 2025)
3. Robin: A multi-agent system for automating scientific discovery — https://arxiv.org/abs/2505.13400 (May 2025); Nature 2026 — https://www.nature.com/articles/s41586-026-10652-y ; GitHub — https://github.com/Future-House/robin
4. Accelerating scientific discovery with Co-Scientist (Google) — https://arxiv.org/abs/2502.18864 (Feb 2025)
5. Kosmos: An AI Scientist for Autonomous Discovery — https://arxiv.org/abs/2511.02824 (Nov 2025); GitHub — https://github.com/jimmc414/Kosmos
6. AgentRx: A Benchmark Study of LLM Agents for Multimodal Clinical Prediction Tasks — https://arxiv.org/abs/2605.10286 (2026); PMLR v333 — https://proceedings.mlr.press/v333/al-jorf26a.html
7. AIOS: LLM Agent Operating System — https://arxiv.org/abs/2403.16971 (Mar 2024); GitHub — https://github.com/agiresearch/AIOS
8. ChemCrow: Augmenting large-language models with chemistry tools — https://arxiv.org/abs/2304.05376 (Apr 2023)
9. AgentNet: Decentralized Evolutionary Coordination for LLM-based Multi-Agent Systems — https://arxiv.org/abs/2504.00587 (Apr 2025, NeurIPS 2025); GitHub — https://github.com/zoe-yyx/agentnet
10. **Preregistration for Experiments with AI Agents** — https://arxiv.org/abs/2606.11217 (2026)
11. **Falsifiable Commitment Planning for Self-Correcting Web Agents** — https://arxiv.org/abs/2607.24167 (2026)

### Adjacent (context only, not core prior art)
- Chainlink, "AI Agents in Prediction Markets" — https://chain.link/article/ai-agents-prediction-markets
- Gnosis, "The Rise of AI Agents in Prediction Markets" — https://www.gnosis.io/blog/the-rise-of-ai-agents-in-prediction-markets-how-gnosis-infrastructure-is-powering-the-future-of-information-finance
- PREP-Eval (pre-registration protocol for AI evaluations) — https://prep-eval.github.io/prep-eval/
- AsPredicted (pre-registration platform) — https://aspredicted.org/

---

## Gaps & uncertainties

- **arXiv IDs 2605.10286, 2606.11217, 2607.24167** are 2026-dated (month 05/06/07 of 2026). I verified each resolves to the expected title via the arXiv abstract page, but I could not fetch full abstract bodies (the fetcher returned only titles). The mechanism descriptions for these three come from search-result summaries and the HTML body of 2606.11217 (which I did read in full). **Recommend a human re-verify the exact abstracts of 2606.11217 and 2607.24167 before submission**, since they are the two closest threats.
- **"Robin" identity:** I assumed FutureHouse Robin (arXiv:2505.13400) is the intended referent. If the competition brief meant a different "Robin," re-run that row.
- **No system was found** that implements *all four* of our elements (escrow + counterfactual + verified-evidence sharing + decentralized need-market) *and* reports a measured difference vs the three baselines. That is the gap our contribution fills. I did not find any 2025–2026 paper that directly measures "escrow vs open-swarm vs central manager" for scientific agents — this appears to be genuinely open.
- **AgentRx's single-agent-wins finding** is a double-edged prior result: it supports the need for our measured-difference framing but means our decentralized mechanism must demonstrably beat a strong single-agent baseline, or the result is uninteresting. Flag for the experiment design.
