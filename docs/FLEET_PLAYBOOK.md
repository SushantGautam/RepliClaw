# Parallel VS Code agent fleet — operating protocol
Active from 2026-10-08. The orchestrator must use the exact current `EXECUTION_STATE.md` as a cursor, not blindly trust old 'COMPLETE' logs.

## Native VS Code capabilities (confirmed against official docs 2026-10-08)
- Workspace custom agents: `.github/agents/*.agent.md`; Copilot project instructions: `.github/copilot-instructions.md`; cross-harness shared instructions: root `AGENTS.md`.
- Copilot/Claude/Codex harnesses have different subagent/session tools. **Discover at runtime**. Do not invent session API calls. Subagents can perform parallel read-only research/review; available nested delegation varies by harness.
- Parallel code editors need **independent sessions with New Worktree** (or explicit `git worktree add -b` + separate directory). Multiple chats in ONE session share the same files, NOT isolated commits.
- VS Code session orchestration may create independent worktree sessions where supported; otherwise give the user explicit worktree commands and task prompts, or sequentially implement independent tasks.
- Worktrees are **code isolation, not security sandboxing**. Keep API keys, cloud credentials and datasets out of worker logs/commits.
References: https://code.visualstudio.com/docs/agents/guides/delegate-two-tasks ; https://code.visualstudio.com/docs/agents/run/sessions/manage-sessions ; https://code.visualstudio.com/docs/agents/run/subagents

## Fleet lifecycle
1. **Recon** (parallel, read-only): code correctness audit, ScienceClaw API audit, benchmark validity audit, competition/submission verification. Each returns file+line references, risks, alternatives and experiment recommendations.
2. **Plan/claim**: orchestrator verifies `IMPLEMENTATION_PLAN.md` and assigns one open ticket per implementation worker. Record owner, base SHA, branch/worktree, owned paths, contract, exact tests, integration points and acceptance evidence in `EXECUTION_STATE.md`.
3. **Parallel implementation**: workers stay in their worktree and own disjoint paths. Each creates code, tests and a brief handoff note, commits on its feature branch, and runs focused checks. Never commit to `repl-claw-dev` from concurrent workers.
4. **Independent review**: two independent reviews per P0 change: (a) code/security/concurrency critic; (b) scientific/experimental validity critic. Reviewers do not edit the author's worktree. Report blockers by severity and evidence, not vibes.
5. **Integrate**: only the orchestrator/chosen integration owner merges or cherry-picks into `repl-claw-dev` one feature at a time. Resolve conflicts, rerun focused + entire test suite + static gates, then prove e2e behavior with saved artifacts.
6. **Checkpoint**: after every merged P0 ticket or successful vertical slice, update state/plan, append PROGRESS, create `docs/checkpoints/CP-*.md` snapshot with commit SHA and commands/results. Demonstrate current functionality rather than a future promise.
7. **Continue**: execute ready tickets based on dependencies and critical path; do not declare competition ready because the prototype's old AC01–AC18 passed.

## Ready-to-run first fleet
| Worker | Ticket | Owned paths (primary) | Depends on | Stop condition |
|---|---|---|---|---|
| W1 | F01 baseline validity | `src/repliclaw/strategies.py`, `tests/test_strategies.py` | none | real shared-context debate + true vote, adversarial tests |
| W2 | F02 execution honesty | `src/repliclaw/investigators.py` plus new `src/repliclaw/execution*.py`, `tests/test_execution*.py` | none | self-claim executable cannot pass; command/log/output verified |
| W3 | F03 benchmark design | `src/repliclaw/benchmark.py`, new `src/repliclaw/evaluation*.py`, new `tests/test_evaluation*.py` | none | fair budgets, proper recovery, honest intervals, frozen heldout manifest |
| W4 | F04 distributed needs SPIKE | research/design only first, `docs/design/NEED_DISPATCH.md` | none | verified upstream Reactor integration plan + adversarial integration test specification |
| W5 | F05 science feasibility | `experiments/`, `docs/design/SCIENTIFIC_CASE.md` (no modifications to core initially) | none | one runnable scientific case with tracked data/license/origin |
| R1 | skeptical code reviewer | read-only | worker patches | evidence-based security/correctness findings |
| R2 | scientific judge | read-only | worker patches + eval | detects benchmark leakage/fairness and overclaims |

**Conflict schedule:** W2 may touch investigator contracts used by W1/W3. Establish a tiny, backward-compatible interface contract first, then merge W1 → W2 → W3 as needed. W4 becomes implementation only after the F04 design review; its likely owned files `src/repliclaw/protocol.py`, `scienceclaw_adapter.py`, new dispatch modules and tests. No one except integration owner edits `README.md`, `AGENTS.md`, `TASK_SPEC.md`, `EXECUTION_STATE.md`, `IMPLEMENTATION_PLAN.md`, `DECISIONS.md` on shared branch.

## Contract for each worker
Each assigned ticket must specify:
- exact problem and rubric link; upstream/base commit;
- owned paths, forbidden paths and interface contract;
- exact tests/red tests before fix when applicable;
- reproducible demo showing feature, negative tests, and error paths;
- dependencies, explicit claim to scientific validity, risks;
- acceptance criteria with objective evidence and output locations;
- reviewer names/roles and state handoff.
Worker must output: branch, commit SHA, paths touched, commands and exit codes, measured observed behavior, blockers, assumptions, unresolved issues, handoff instructions.

## Scheduling / fleet bounds
At most ~3 independent editing workers plus read-only reviewers at once unless integrations and compute budget justify more. Never launch many workers against one expensive LLM service simultaneously without quota/rate-limit protection. Give each worker separate output/run directories and seeds. Pause integration when another editor owns shared state. Have one state writer. Reserve one lane for integration and one for independent review; this prevents 'parallel work' from multiplying merge failures.

## Continuation algorithm
On resume: read state → inspect `git status`, HEAD SHA, branches and running sessions → reconcile recorded workers with actual commits/results → identify smallest unblocked ticket → dispatch or implement → test → review → integrate → checkpoint → repeat. Use existing sessions instead of spawning duplicates. If tool/harness lacks session orchestration, operate sequentially and truthfully log why; don't pretend sessions were launched.

## Safety / authority
Agents may run local code/tests and update assigned feature worktrees, but must not overwrite unrelated user work, delete datasets, expose secrets, alter production services or spend unbounded API credits. Any external irreversible action needs user's explicit authorization. No generated claims of 'judge approved' without a review record referencing the diff and evidence. A failed experiment stays recorded as failed.
