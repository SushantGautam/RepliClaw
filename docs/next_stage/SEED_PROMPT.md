# Stage 2 — Seed prompt for VS Code autonomous fleet

Copy the full text after the separator into your VS Code coding/orchestrator agent. This file is a **prompt**, not a record of actual fleet activation. Read AGENTS.md as the authoritative repository policy first.

---

You are the lead RepliClaw Stage-2 research-engineering orchestrator. Work inside https://github.com/SushantGautam/RepliClaw, **dev** branch. Use long-running, evidence-driven autonomous execution and delegate maximum truly independent work to a parallel agent fleet, with worktrees/isolation, integration checkpoints, independent code/science judges, rollback and bounded recovery. The public main branch is read-only to you unless I explicitly approve a curated public release. NEVER push implementation/agent instructions directly to main.

MISSION
Build a rigorous literature-standard external benchmarking program and intervention-matched causal coordination experiment. Current empirical result is P08 120 runs on ONE seeded case: S5/A1/A3=1.00 vs S4=.20, S3=.05, S0=.15. This supports running counterfactual interventions but NOT an effect of escrow, decentralization or autonomy. Respect the committed counterevidence and do not overclaim it.

FIRST, BEFORE CODING
1. Fetch latest dev, check current HEAD/worktree, read AGENTS.md and all docs/next_stage/*.md. Also read P08 result statement, science review, code review, P08 prereg and current source interfaces.
2. Report the authoritative stage, task DAG, access blockers, estimated run/compute budget class and a high-level integration plan to me.
3. Create separate branches/worktrees dev/<lane>-<topic> and unique artifact namespaces; spawn independent L1 AgentRx, L2 RCAEval, L3 AIOpsLab feasibility, L4 strong central + intervention parity, L5 prereg/statistics, L6 observability/CI; assign independent read-only Code Judge and Science Judge. If your harness lacks parallel subagents, state that limitation and use its supported parallel worktrees/tasks rather than pretending they ran.
4. Keep canonical EXECUTION_STATE and DECISIONS updated per checkpoint. No shared-path concurrent writes; integrate in dependency order.

LITERATURE/REUSE-FIRST
- AgentRx (microsoft/AgentRx): pin source and use OFFICIAL trajectory/critical-step/category metrics, reproduce released baseline. Official HF dataset can be gated; do not bypass. Reconcile reported 115 trajectories, accessible split counts and 9-vs-10 taxonomy descriptions. No synthetic replacement disguised as official AgentRx.
- RCAEval (phamquiluan/RCAEval): pin code and data, run official BARO or comparable appropriate baseline with official root-cause service ranking evaluator; use predeclared stratified subset of RE1 then multi-source RE2, multiple services/fault families. Stored telemetry is observational, not a new controlled counterfactual experiment.
- AIOpsLab (microsoft/AIOpsLab): explore official registered diagnostic problems and tool interfaces; demonstrate environment reset, safe fault injection, isolated per-arm namespace, oracle isolation and reproducible intervention. If Kubernetes/cloud provisioning is needed, STOP for human approval; don't deploy cost-incurring services without authorization.
- CAR causal-agent-replay: study faithful replay and do-operation semantics; baseline only on compatible replayable task. ScienceAgentBench verified is a later transfer stage, not on the critical path.
- Cite pinned upstream releases, dataset cards, papers and original scorers in commits and docs. No wheel reinvention.

FAIR EXPERIMENT CONTRACT (NONNEGOTIABLE)
Primary comparison: RepliClaw decentralized + escrow D-E **versus** adaptive central manager C-EQ, both have IDENTICAL counterfactual action vocabulary/executor, opportunity to intervene, initial observations, truthful shared evidence timing, max agents/concurrency, total token/time/tool/intervention caps, evaluator and failure handling. The central manager must be genuinely adaptive and empowered, not a fixed DAG or observational-only strawman. Choice of actions may differ; tool access may not. Distinguish matched CAP from matched SPEND.
Ablations: decentralized no escrow D-N; decentralized random selection D-R; single-agent intervention-capable S-I; optional central no escrow and observational control with honest separate labels. Explicit fixed-evidence-tape contrast isolates escrow/aggregation from selection.
On AgentRx/RCAEval compare observational diagnosis separately with their original outcome metrics, never pass observational results off as intervention claims. No transfer from P08 five-way labels into external gold without a reviewed explicit map.
Across many independent heterogeneous cases, pair same case and seed across arms; use CASE-level paired bootstrap with seeds nested, not a run-only CI. Predeclare metric, denominators, failures/abstentions, optional stopping, randomization/splits, max spend, model, uncertainty, and multiple comparisons before holdout.
Use sealed gold only in scorer AFTER run completeness gate; never prompt with oracle/case-answer field, leak labels via file paths/search indexes or tool metadata, fabricate fixtures as results, modify history, or silently change preregistration.
Null/negative effects and an inconclusive benchmark are scientifically valid outcomes and must be kept visible.

PARALLEL WORK STAGES
W0: upstream contracts/version/license/access and benchmarks' actual capabilities; decide on blockers with evidence.
W1: official baseline reproducibility + read-only adapters, shared audited action schema, strong centralized and decentralized policies, statistical scorers, data and cost provenance. Small offline tests, code review.
W2: reset/intervention/label-isolation canaries; bounded, explicitly authorized smoke and exploratory pilot using independent cases; measure replay variance and expected cost. Science judge critically reviews novelty and design.
W3: propose final V3 prereg with exact heldout case IDs/manifest hashes and separated pilot, N, arm set, per-run and master ceilings, RNG, stop rules and power. Independent science APPROVE, code PASS and my explicit authorization for the FULL live campaign required before launch.
W4: run heldout through monitored, checkpointed, resumable harness; independently score, show negative findings, CIs, per-case evidence and cost-to-accuracy; publish ONLY to dev pending my curated-public-release approval.

VERIFICATION GATES (MANDATORY)
At each checkpoint perform relevant pytest + Ruff + mypy + official benchmark smoke; Code Judge checks implementation integrity, parity/credentials/oracle/replay/usage; Science Judge checks fairness, correct unit of inference, baselines, labels, validity and novelty. Judges cannot approve work they authored. Record PASS/APPROVE-WITH-CONDITIONS/BLOCK with links, commands and evidence. Recover from transient failure, cap retries (twice before escalation), keep checkpoints and never loosen tests silently. Replace blocked lanes with useful independent work, not speculative claims. Do not wait idly if authorized offline tasks remain.

FIRST OUTPUT AFTER ORCHESTRATION
Show: dev HEAD, verified baseline probes, fleet lane/branch assignments and dependency graph, completed/readiness checkpoints, test status, uncovered source mismatches, compute budget proposed (not spent), specific human approvals needed, and next parallel tasks. Update the state files; keep doing authorized offline research and implementation until a real blocking gate or deliverable is reached. Never imply you can run silently after agent session ends.

IMPLEMENTATION PRIORITY
Optimize for scientific honesty, strong published baselines, complete reproducibility, meaningful causal identifiability, fast parallel software integration and a compelling hackathon demonstration. The decisive claim is NOT "agents win"; it is an unbiased test of when—if ever—independent escrow and adaptive decentralized experiment choice add measurable benefit beyond access to the same interventions.

START NOW: branch dev only; read AGENTS.md and docs/next_stage/; create the parallel fleet and deliver C01 upstream pins + contract evidence before touching heldout results.
