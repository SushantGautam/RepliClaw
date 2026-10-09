# Stage 2 — Parallel research fleet implementation plan

Status: DRAFT task graph, 2026-10-09; agent instructions apply only on `dev`.

## North-star acceptance
1. A published, independently checkable benchmark is evaluated with its official scorer and a strong released baseline.
2. A pre-registered **intervention-matched central manager vs RepliClaw** controlled comparison spans independent cases; BOTH can use identical actual counterfactual tools.
3. Causal vs observational claims are separated; zero/negative effects accepted; reproducibility artifacts are inspectable.
4. A user can reproduce a small representative example and test without access to a private GPU.
5. Existing P08 120-run artifacts/result statement stay frozen.

## Fleet lanes, exact owners, dependencies and deliverables

| Lane | Owner paths (preferred) | Dependencies | Outputs / exit evidence |
|---|---|---|---|
| L0 Orchestrator/Integrator | docs/next_stage/EXECUTION_STATE.md, DECISIONS.md; merge/integration | every lane | DAG, worktree map, checkpoint release notes, gate decisions, no premature main push |
| L1 AgentRx feasibility + comparator | src/repliclaw/benchmarks/agentrx/**, tests/benchmarks/test_agentrx*, docs/next_stage/adapters/agentrx* | G0 licensing/access, canonical interface | official repo pin, dataset manifest/split/count, strong official baseline reproduction, correct critical-step/category scoring, access blocker if gated |
| L2 RCAEval baseline + adapter | src/repliclaw/benchmarks/rcaeval/**, tests/benchmarks/test_rcaeval*, docs/next_stage/adapters/rcaeval* | G0 source, official scorer | RE1/RE2 index, stratification, original baseline (BARO etc) metric reproduction, read-only telemetry ingestion, root-service TopK, no gold leakage |
| L3 AIOpsLab feasibility + controlled interventions | src/repliclaw/benchmarks/aiopslab/**, tests/benchmarks/test_aiopslab*, docs/next_stage/adapters/aiopslab* | G0; isolated cluster approval for deployments | documented registered problem, reproducible reset/fault injection, action API + context, executor receipts, isolation parity canaries. Environment unavailable => BLOCK not fake pass |
| L4 Intervention parity, central-manager design | src/repliclaw/experiments/v3/**, tests/experiments/test_v3*, docs/next_stage/design/** | signed interfaces from L1–L3, G2 | C-EQ truly adaptive and can call SAME interventions as D-E, no pre-coded answers, plus D-N/D-R/S-I; deterministic offline contract tests |
| L5 Methods/prereg/scoring | docs/next_stage/science/**; scorer files by exclusive lease; statistical tests | result schema from L1–L4 | evaluator-only oracle, native official metrics, nested-seed paired case bootstrap + CIs, counts/ITT failure cases, draft prereg frozen BEFORE final runs |
| L6 Observability/performance/reproducibility | src/repliclaw/benchmarks/common/**, scripts/benchmarks/**, tests/benchmarks/test_common*, docs/next_stage/ops/** | canonical JSON contracts | provenance, budgets, tool counts, entropy/forecast, run resume, reset timing, multi-run isolation, benchmark hashes; no secrets |
| J-SCI Independent Science Judge | docs/next_stage/reviews/SCIENCE_* | every gate | adversarial review, explicit sign-off/BLOCK; may not alter own evidence |
| J-CODE Independent Code Judge | docs/next_stage/reviews/CODE_* | every gate | CI, leak, repro, API/metric schema canary and intervention-parity verification; may not alter own evidence |

Path additions require integrator approval; no two agents edit same file concurrently. Use local worktrees or parallel VS Code agent sessions if genuinely supported; **don't invent agent spawning commands for an unknown client**.

## Phase dependency graph and gates

**Wave 0 (parallel, no live LLM, day-1):** L1/L2/L3 upstream contracts/access, L5 protocol and metric audit, L6 schema/provenance. L0 assigns scope and integrates initial findings. G0 requires source pins and permissions.

**Wave 1 (parallel, no claim of research success):** L1/L2 reproduce official baselines, L3 proves safe reset/action parity or blocks, L4 implements central/D-N/D-R interfaces against frozen action contract, L6 tests traces. G1/G2 Science and Code Judge evidence.

**Wave 2 (bounded smoke/pilot ONLY after legitimate local authorization):** deterministic fixture + official single-case smoke; bounded pilots of heterogeneous independent cases; rerun true official baseline. L5 performs blind score audit and variance/power proposal; independent J-SCI/J-CODE act before confirmation. Pilot results may not be used as confirmatory holdout.

**Wave 3 (human key required):** freeze v3 prereg, selected cases/splits and exact accessible dataset counts, N, seeds, models, budgets, maximum spend and stop rules. G4 sign-off includes human authorization for this exact final campaign. Launch no full campaign before this.

**Wave 4:** heldout run, results, negative findings, within-domain and cross-domain generalization, replay fidelity, compute costs, review. G6 report independently verified. Public release gate G7: curated evidence-only `main` updates after human approval.

## Measurable checkpoints: do not mark DONE without paths

- C00 DEV-READY: dev branch, this AGENTS.md, full source decision, state and seed prompt.
- C01 UPSTREAM-PINS: Git SHA, license, official dataset indices and verified run command per source; gated resources flagged.
- C02 OFFICIAL-BASELINES: official evaluator reproduces baseline on representative cases; tests show exact label mapping.
- C03 PARITY: central vs decentralized share tool interface SHA, reset state, observation timing, same max tests + compute envelope. Baseline is adaptive, not fixed.
- C04 ISOLATION: model sees no oracle labels, gold files, hidden seeds, evaluator paths; smoke tests and independent audit.
- C05 PILOT: at least two domain/fault families, genuine failures and abstentions, within-budget models; reported as exploratory.
- C06 FREEZE: signed prereg, independent science/code reviews, full spend/endpoint authorization.
- C07 HELDOUT: case-weighted paired outcomes and stable CI, raw predictions, complete logs, executed commands and version pins.
- C08 RELEASE: public-friendly research statement that opens with counterevidence, methodological caveats and resource limits.

## Agent feedback / continuous integration
After each wave: worker commits to isolated `dev/<lane>-...`, runs `pytest`, `ruff`, `mypy` as applicable, writes a short DONE/BLOCKED note with hashes. Code Judge reproduces tests, Science Judge reviews estimand. Orchestrator integrates approved commits into **dev** and updates state, then schedules next dependency-ready work. Repair loops may retry twice without loosening a gate; after persistent failure mark BLOCKED, propose alternative, record human decision needed. Keep a 10.8M token P08 spending ceiling historical only; stage-2 budget is **NOT YET AUTHORIZED or set**.

## Collaboration / speed
Prefer many read-only research probes simultaneously; serialize expensive LLM runs, shared cluster/fault injection, dataset downloads, scoring snapshot modifications and integration branch updates. Use Qwen/vLLM endpoint only if connection is provided by user's environment and authorized for this scope; do not hardcode hostname/key. Reuse local offline tests for fastest fail feedback and host official evaluations as designed.

## Required output format at each checkpoint
Checkpoint ID / timestamp UTC / dev HEAD / upstream SHAs / owners completed / artifact paths / tests and gate verdict / actual cost so far / unresolved risks / next dependency-ready tasks / human approvals needed. Update EXECUTION_STATE.md rather than announcing a percentage without evidence.
