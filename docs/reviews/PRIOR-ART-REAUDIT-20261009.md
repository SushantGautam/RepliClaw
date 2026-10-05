# Independent Prior-Art Re-Audit — EESS Novelty Claims (2026-10-09)

> **Reviewer:** general-purpose research agent `e1df7b0a` (read-only, adversarial mandate)
> **Method:** all four named systems verified from primary sources fetched 2026-10-09 (both Nature
> papers from article HTML via curl; AutoScientists full PDF + repo protocol files; AgentRx README +
> arXiv v2) + fresh adversarial sweep for new art. Evidence cached in `artifacts/dev/priorart/`.
> **Verdict: NOVEL WITH DISCLOSURES X** — the (a)∧(b)∧(c)∧(d) conjunction survives; element (b) has
> **NEW material prior art (CAR, arXiv 2606.08275)** the 2026-10-08 gate missed → gate updated same day.

---

 Audit complete. All four named systems verified against primary sources today, plus a fresh adversarial sweep. Full deliverable below.
 
 ---
 
 # Independent prior-art re-audit — RepliClaw (EESS) novelty claims
 **Auditor: independent, adversarial. All sources fetched 2026-10-09.**
 
 Method note: `web_fetch` got HTTP 406 from Nature; direct `curl` with a browser user-agent succeeded, so **both Nature papers were verified from the actual article HTML** (not fallback snippets). AutoScientists was checked beyond the abstract: full paper PDF (13 pp.), repo README, `PHASES.md`, `ROLE-TEAM.md`. AgentRx verified via README + arXiv v2 abstract.
 
 ## 1. Mechanism-by-mechanism table
 
 Legend: **Yes** / **Partial** / **No**.
 
 | System | (a) Escrow: hashed/crypto pre-outcome commitments + machine-verified reveal | (b) Counterfactual interventions on frozen audit artifact as primary evidence substrate | (c) Decentralized local experiment selection via need-market, atomic claiming | (d) Matched-budget strong adaptive central manager comparator | Closest-overlap note |
 |---|---|---|---|---|---|
 | **AutoScientists** (Gao, Fang, Zitnik; arXiv 2605.28655) | **Partial** — `create_team(hypothesis, prediction, falsification)` records a pre-experiment prediction and abandon-criterion, but it is **public from creation** (post → peer critique → execute), no hashing, no sealed reveal, no forecast scoring. 0 hits for hash/escrow/cryptographic in paper | **No** — one-factor-at-a-time champion *training optimization*; no intervention-based causal diagnosis, no frozen audit artifact | **Partial — strongest overlap found.** Public proposal + dedup checks + GPU agent **claims/releases from `queue.md` via read-modify-PUT with If-Match (optimistic locking)**, dead-ends registry. But it's compute-job claiming for optimization runs, not agent-owned utility scoring over scientific *unmet needs* | **No** — comparators are prior AI agents (Biomni, Autoresearch, single-agent) at matched compute, not a same-tools adaptive central manager | Debatable decentralized self-organizing teams + pre-compute predictions + atomic claiming + shared failures under matched budgets. The gate's characterization is accurate but understates that their predictions are *public, not sealed* — that's your differentiator, and it's thin on its own |
 | **Co-Scientist** (Google DeepMind; Nature s41586-026-10644-y) | No | No | **No** — a central **Supervisor** agent dynamically allocates work to specialized workers on an async queue (i.e., the *opposite* architecture) | **No** — baselines are single-LLM outputs (Gemini 2.0 Pro/Flash, o1, o3-mini, DeepSeek R1), expert best-guess, plus component ablations; no manager-vs-swarm comparator | Tournament/debate/evolution for hypothesis *generation*; no intervention, no commitments, centralized by design |
 | **Robin** (FutureHouse; Nature s41586-026-10652-y) | No | No — real wet-lab experiments (in-vitro validation), not counterfactual interventions on a frozen artifact | No — coordinated agent pipeline (literature agents + Finch analysis agent), human-in-the-loop | No — single-system demonstration, no comparator arms at all | End-to-end iterative hypothesis→experiment→analysis loop; the paper contains zero comparator/ablation machinery relevant to (d) |
 | **AgentRx** (Microsoft; arXiv 2602.02475, EMNLP Findings 2026) | No | **Partial — material.** Synthesizes executable constraint/invariant checks, evaluates them step-by-step, emits an **auditable validation log with evidence**, LLM judge localizes the critical step. But it is *one-shot analysis of a fixed trajectory* — no re-execution, no do-intervention, no competing-hypothesis discrimination, no substrate beyond the trajectory | No | No — compared against prior diagnostic methods (step-localization accuracy), no manager comparator | The "executable constraint checks + auditable log on agent failures" element is prior art here; must be cited whenever (b) is described, even though CAR (below) is the closer match for the intervention half |
 
 **None of the four does all of (a)–(d), and none does the conjunction.** (d) in particular — a matched-budget *strong adaptive central manager as a first-class comparator arm* — appears in no surveyed system.
 
 ## 2. VERDICT on the joint claim
 
 > **"Novel with disclosure X."**
 
 The conjunction (a)∧(b)∧(c)∧(d) was **not found in any single system as of 2026-10-09**, and I actively searched for the killer — including the new hits below — and the conjunction survives. However, **two individual elements have *new* prior art the existing gate analysis missed** (the 2026-10-08 gate predates or overlooked these):
 
 - **Element (b) is now partially anticipated.** *Causal Agent Replay (CAR)* (arXiv 2606.08275, 2026-06-06, open source) does exactly "intervene on a frozen recorded agent run, re-execute under the same stochastic policy, measure outcome-distribution shift" — with a full intervention algebra (`do_resample`, `do_action`, `do_observation`, `do_context`, `do_policy`), budget-bounded Shapley attribution, and confidence intervals. Combined with AgentRx's executable constraint logs, the *primitive* of intervention-based causal diagnosis of LLM-agent failure is published prior art. Your defensible residue: CAR is **single-agent, step-level, on the agent's own trajectory**; you target **external system factors of an audited AI system (retrieval / policy-instruction / evaluator-judge) via competing multi-agent hypotheses over a frozen SimpleAudit artifact**. That's a real difference — but it must be *stated*, not assumed.
 - **Element (a) has a motivating position paper**: *Preregistration for Experiments with AI Agents* (arXiv 2606.11217, ICML 2026) argues agents must commit before reveal — it's a human-facing template, not a machine-verified agent protocol, so (a) as implemented (hashed packets, phase-boundary reveal, tamper detection) stands as a demonstrated combination.
 
 **Required disclosures (X):** AutoScientists (public pre-compute predictions + atomic queue claims + matched-budget eval), **CAR (intervention-based causal attribution — new, must be added to the gate)**, AgentRx (executable constraint checks), the ICML-2026 preregistration position paper, Dubova et al. (already in gate).
 
 **Residual adversarial risk (honest):** an aggressive reviewer can still argue your (c) is "AutoScientists with a rename" *and* your (b) is "CAR multi-agent-ified." The only things that actually kill that argument are the *no-escrow ablation delta*, the *unscripted pivot with snapshot hash*, and the *matched-budget manager result* — i.e., the pending live runs (N1/N2/N4 gates). The claim is novel **as demonstrated here only if those gates pass**; until then it is novel *in design*, which is a weaker sentence and should be the one used externally.
 
 ## 3. NEW prior art found (beyond the four named)
 
 1. **Causal Agent Replay (CAR)** — https://arxiv.org/abs/2606.08275 + https://github.com/jaineet17/causal-agent-replay — **material overlap with (b); verified from primary sources 2026-10-09.**
 2. **zkAgent** — https://eprint.iacr.org/2026/199 — SNARK-verified agent execution, tool observations bound to authenticated runs. Overlaps only the "machine-verified" vocabulary; it proves *execution integrity*, not pre-outcome forecasts. Note in one sentence, don't weight.
 3. **Preregistration for Experiments with AI Agents** — https://arxiv.org/abs/2606.11217 (ICML 2026) — motivates commit-before-reveal for agent experiments; human researcher template, no machine protocol. Cite to preempt "obvious from prereg" objection.
 4. **P2PCLAW / OpenCLAW-P2P v7.0** — https://arxiv.org/abs/2604.19792 — decentralized AI peer-review/publishing network (reference verification, scoring). Low overlap: no experiment selection, no predictions, no interventions. *(Caveat: self-published, journal-less preprint; low evidentiary weight — mention only as "decentralized research collectives exist.")*
 5. **VIGIL: Verify-Before-Commit** (ACL 2026) — https://aclanthology.org/2026.acl-long.443/ — verified: despite the name, a *prompt-injection security* protocol (speculative generation + intent verification), not a research-forensics escrow. **Name-collision hazard only** — do not let anyone conflate your "commit/reveal" with VIGIL's; a footnote may help.
 6. **AI Agent Swarms as Researchers** — https://arxiv.org/abs/2609.35719 — swarm coding agents doing real research; no escrow/market/interventions. Context for "decentralized swarms exist."
 7. **SwarmHarness** — https://arxiv.org/abs/2605.28764 — decentralized compute-swarm task routing (DHT + utility-based router + credit staking). Near-(c) in mechanics but for compute jobs, and routing is centrally computed — the opposite of agent-owned choice.
 8. **SCOPE benchmark** — https://arxiv.org/abs/2608.03501 — LLM experimental-design benchmark; no mechanism overlap.
 9. (Minor, from search: Coscientist chemistry agents, Virtual Lab nanobodies, AutoLLMResearch MDP-based experiment selection — closed-loop single-pipeline labs; no escrow/market/comparator; not material.)
 
 ## 4. Three most defensible one-sentence claims + wording to avoid
 
 **Defensible (cross-checked against the gate's prohibited list):**
 1. *"We demonstrate a demonstrated-to-date combination: sealed, hash-verified pre-outcome prediction commitments, counterfactual interventions on a frozen reproducible audit artifact, agent-owned local experiment selection over a need market, and a matched-budget strong adaptive central manager comparator, applied jointly to causal diagnosis of AI-system failure — and we evaluate the combination, not any single element."*
 2. *"On a frozen preregistered failure case, we test whether decentralized agents that commit to competing predictions before seeing peers' results, and re-select experiments locally after execution-verified evidence, discriminate root-cause factors (retrieval vs. policy vs. evaluator) better or cheaper than a matched-budget adaptive central manager — reporting null or negative results as first-class outcomes."*
 3. *"We introduce an evidence-escrow protocol for multi-agent diagnosis — sealed forecast packets, phase-boundary machine-verified reveal, no post-hoc amendment — as a testable control on false consensus, with a no-escrow ablation measuring whether it changes outcomes at all."*
 
 **Wording to AVOID** (first five are on the gate's prohibited list; the last three are new hazards this audit found):
 - ❌ "First decentralized AI scientist / agent swarm / self-organizing scientists" → AutoScientists, swarm-research literature, P2PCLAW.
 - ❌ "First counterfactual / intervention-based causal diagnosis of agent failure" → **CAR** now kills this outright; AgentRx kills the executable-checks variant.
 - ❌ "First pre-outcome / preregistered prediction in agent experiments" → ICML-2026 position paper; and AutoScientists' public `prediction`/`falsification` fields undercut "pre-compute predictions are novel" — your differentiator is *sealed + machine-verified + scored*, say exactly that.
 - ❌ "Cryptographic guarantees of reasoning independence / secrecy" → hash proves later consistency only (gate-prohibited; unchanged).
 - ❌ "Proven to beat central workflows" → only offline deterministic parity exists; live matched-budget result is pending (gate-prohibited; unchanged).
 - ❌ "Novel experiment-selection algorithm" → the utility heuristic is explicitly not a claim (gate-prohibited; unchanged).
 - ❌ Unqualified "predict before we believe" as a novelty hook → AutoScientists predicts before spending compute too; always qualify as *sealed, escrow-gated, machine-verified* pre-outcome commitments.
 - ❌ "Novel commit/reveal protocol" without qualification → VIGIL (verify-before-commit) and zkAgent make bare "commit/reveal" / "machine-verified agent execution" sound pre-claimed; specify *research-forecast escrow*.
 
 **Bottom line:** the conjunction survives, but the *existing gate is stale* — it must be updated with **CAR (arXiv 2606.08275)** before any external submission; that single addition is the difference between "defensible" and "refutable." The four named systems were correctly identified; the danger was in the 2026-06 counterfactual-attribution literature the team hadn't scanned. (All fetched evidence cached under gitignored `artifacts/dev/priorart/`: both Nature articles, AutoScientists paper PDF + protocol files, AgentRx README, zkAgent and P2PCLAW abstracts.)