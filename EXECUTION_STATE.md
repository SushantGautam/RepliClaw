# RepliClaw — Active execution state
Last updated: 2026-10-08 13:55
status: WORKING
program: ScienceClaw competition readiness (NEW; prototype remains historically complete)
branch: repl-claw-dev
base_SHA: 2ba5847 (fleet contracts committed; test baseline a14fa67)
current_milestone: Wave A parallel fleet F01–F05 running in isolated worktrees
gate: G0 PASS (66 passed, ruff clean, mypy clean — logs/G0-baseline-20261008.txt, @ a14fa67)
current_ticket: F01+F02+F03+F04+F05 (parallel)
running_workers: W1 F01 (w1/F01-baseline-validity, .worktrees/f01), W2 F02 (w2/F02-execution-honesty, .worktrees/f02), W3 F03 (w3/F03-eval-fairness, .worktrees/f03), W4 F04 design-only (w4/F04-need-dispatch, .worktrees/f04), W5 F05 (w5/F05-science-feasibility, .worktrees/f05)
worker_contracts: docs/fleet/README.md + docs/fleet/F01..F05.md
integration_owner: primary VS Code orchestrator session (this session); merges F01→F02→F03→F05, F04 design feeds DECISIONS.md/F06
latest_checkpoint: docs/checkpoints/CP-20261008-G0.md
next_action: Await worker handoffs; per P0 ticket run Code Judge + Science Judge reviews; fix blockers; merge one at a time with full gate; checkpoint each merge.
blockers: none verified
source_of_truth: docs/COMPETITION_STRATEGY.md, IMPLEMENTATION_PLAN.md, docs/QUALITY_GATES.md

## Baseline honesty
Old EXECUTION_STATE.md stated COMPLETE for 18 prototype criteria, reported 66 passing tests, and saved deterministic + live demos. This NEW program is NOT complete. Prior reports are historical evidence and have not been independently rerun in this planning update.
Scientific gap: deterministic 6/6 on toy fixtures; the live-model misleading case is a tie across 5 strategies. No causal proof of distributed collective advantage, no documented independent cross-team use.
Engineering gap: direct central follow-up, context-only blindness, erroneous debate peer serialization, model-self-certified execution, non-budget-matched comparator suite.

## Environment note (verified 2026-10-08)
- Anaconda system python 3.11 breaks pip build isolation (`_distutils_hack` assertion). ALWAYS use a venv: main tree `.venv/` (install `pip install -e ".[dev,otel]"`), each worktree `.worktrees/fNN/.venv/` (install with `-e` from INSIDE the worktree so `repliclaw` resolves to that worktree's src).
- Live LLM API key exists in env but fleet workers are FORBIDDEN to use it (quota + fairness); live runs are F08-only with explicit budgets.

## State update contract
Only the orchestrator/integration owner updates this file, after verifying underlying branch/tests. Record current ticket, owner/worktree, HEAD, gate status, command outputs, latest checkpoint, blockers and next action. Never mark COMPLETE without docs/QUALITY_GATES.md G6 and real-science evidence. Never infer running sessions just because a work plan exists.
