# RepliClaw — autonomous fleet instructions (DEVELOPMENT BRANCH ONLY)

Read this document first. These instructions govern research and coding agents operating on **dev**. This file is an internal development instruction, not public-release documentation. Public `main` is the curated, public-facing research release; **never write, push, cherry-pick, merge, open an auto-merge PR to, or rewrite `main` without explicit human public-release approval.** Do not assume a public GitHub dev branch is private: NEVER commit keys, raw secrets, hidden benchmark labels or restricted data.

## Mission
Deliver Stage 2: literature-standard external evaluation and genuinely intervention-matched decentralized vs adaptive-central research. The next result must answer whether coordination/escrow adds value **after every compared strategy has equal counterfactual diagnostic capabilities**, and must distinguish external observational benchmark performance from controlled interactive causal experiments.

Canonical instructions and editable tracker:
- `docs/next_stage/LITERATURE_AND_BENCHMARK_DECISION.md`
- `docs/next_stage/EXPERIMENT_PROTOCOL_V3_DRAFT.md` (PROPOSED, not approved)
- `docs/next_stage/FLEET_EXECUTION_PLAN.md`
- `docs/next_stage/EXECUTION_STATE.md`
- `docs/next_stage/DECISIONS.md`
- `docs/next_stage/SEED_PROMPT.md`

## Required start of every agent session
1. Confirm `git remote -v`, current branch and clean worktree; `git fetch`; branch from current `dev`, not `main`; use **one git worktree/branch per worker**. Check live HEAD before committing.
2. Read original `docs/experiments/P1_RESULT_STATEMENT_20261009.md`, `docs/reviews/SCIENCE-JUDGE-CAMPAIGN-RESULTS-20261009.md`, and `docs/reviews/CODE-JUDGE-CAMPAIGN-EVIDENCE-20261009.md`. P08: S5/A1/A3 1.00, S4 .20, S3 .05, S0 .15 on **one** case; counterfactual execution not decentralization is supported. Preserve negative evidence.
3. Read V3 proposed protocol and state ledger. Before coding, output task ID, owned paths, interface contract, acceptance criteria, expected tests and cost class.
4. Discover and reuse official upstream benchmark implementations; pin versions. No bespoke substitute benchmark without explicit science sign-off.
5. If live models or external data require credentials, ask only for provider aliases/secret names. NEVER paste tokens, URLs containing tokens, .env, signed URL query strings or benchmark answer keys in commit/log/chat.

## Parallel agents and ownership
Orchestrator issues independent lanes (ownership in FLEET_EXECUTION_PLAN); science judge and code judge are distinct read-only roles with authority to BLOCK. Prefer high independent parallelism but constrain services with shared state (scorer, fixtures, source index, agent-run namespaces). Every worker uses a branch named `dev/<lane>-<short-scope>`, separate worktree and distinct output path. Workers make no changes outside owned paths without an integration ticket; conflict/rebase process is orchestrator-owned. No coordinator that secretly selects scientific investigations inside the assessed decentralized swarm.

## Stage gates
- **G0** source/version/license/access + benchmark contract audit
- **G1** unmodified official baseline and scoring reproducibility
- **G2** same tools/executor, intervention caps, independent environment reset, leakage and replay canary
- **G3** bounded pilot and two independent judge reviews
- **G4** frozen preregistration + Science Judge sign-off + explicit human authorization for full experiment/model/maximum cost
- **G5** sealed heldout run and evaluator-only scoring
- **G6** independent statistical/integrity review with negative/uncertain findings
- **G7** public release approval; only then curate a `main` push

No human approval => continue **offline documentation, fixtures, infrastructure, read-only baseline work** but **STOP at any paid/live-campaign or cloud-deployment barrier**. Do not turn a user's general request to "spin the fleet" into permission for unknown spending. Do not claim empirical results before evidence exists.

## Orchestrator responsibilities
- Maintain dependency DAG, worktree/branch registry, a single authoritative STATE and decision log, resource queue and test report; prefer 4–8 agents if capacity exists, with no hard-coded claim that parallelism is free.
- Pull completed work into `dev` with explicit integration checkpoints. Parallelize research, adapters and protocol reviews; serialize shared scorer contracts, manifest schema and integration commits.
- Require proof (command, hash, path, independent review) per completed task. A green narrative without machine-verifiable artifact is NOT DONE.
- Reassign blocked tasks, retry transient failures within limits, quarantine flaky tests; never silently loosen acceptance criteria.
- Use git checkpoints after each meaningful stage; retain original/scored artifacts, logs, reproducibility data and negative outcomes.
- Update `EXECUTION_STATE.md` and `DECISIONS.md` on every checkpoint, with completed/blocked/next, actual branch HEAD, and URLs. Note in state when human authorization is needed.

## Code Judge (independent, cannot self-approve)
Check Ruff/mypy/pytest/CI + integration smoke, exact upstream pin, truthful dataset counts, no secret leaks, scorer/label schema parity, Oracle isolation, action parity, baseline uncrippled, reset/seed provenance, stable resume + idempotency, per-call usage, no benchmark-specific answer hard-coding. Reject broken code or unverifiable claims.

## Science Judge (independent, cannot self-approve)
Attack estimand, intervention identifiability, variance unit, independence, label leakage, cherry-picking, underpowered comparison, optional stopping, prompt/task parity, benchmark/version mismatch, metric definitions, post-hoc amendments and strength of the adaptive central manager. Require an intervention-matched central comparator, strong published baselines and case-level uncertainty. Record verdict PASS / APPROVE-WITH-CONDITIONS / BLOCK with corrective evidence.

## Reuse, reproducibility and safety
- Reuse AgentRx, RCAEval and AIOpsLab evaluation code where licensed. CAR may be a method baseline when replay is compatible; ScienceAgentBench verified is later optional. Pin original SHA and do not redistribute restricted original data.
- AgentRx HF `microsoft/AgentRx` requires access approval; no bypass. Distinguish source-paper counts from accessible dataset counts and taxonomy versions.
- **Stored traces are observational**; they are not genuine counterfactual experiments. AIOpsLab fault injection does not by itself prove arbitrary reversible replay: verify reset semantics.
- Use case-level paired bootstrap, with seeds nested in cases; P08 run-level CI cannot establish generalization.
- Keep GIT state on `dev` until a human decides what public artifact goes to `main`; public release must contain counterevidence and honest limitations.
