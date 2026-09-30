# RepliClaw — Active execution state
Last updated: 2026-10-08 13:55
status: WORKING
program: ScienceClaw competition readiness (NEW; prototype remains historically complete)
branch: repl-claw-dev
HEAD: 2ccb629 (F04 merged; fleet contracts 2ba5847; test baseline a14fa67)
current_milestone: Wave A — F04 integrated; F01 awaiting science judge; F02/F03/F05 workers running
gate: G0 PASS (66 passed, ruff/mypy clean @ a14fa67); post-F04-merge: 66 passed + 8 skipped, ruff/mypy clean @ 2ccb629
current_ticket: F01 (judging), F02 (W2 running), F03 (W3 running), F05 (W5 running)
done_workers: W4 F04 @ 0ca2e61 MERGED (Code+Science PASS), W5 F05 @ 083b4aa (dual judges running)
repair_rounds: W1 F01 @ 6fad37f — Code Judge PASS; Science Judge PASS w/ 4 Majors → REMEDIATION ROUND 1 dispatched (audit includes_peer_materials fidelity, PhaseGate bypass guard, handoff benchmark-disclosure, test sentinel tightening + flag-pinning test). Re-review by BOTH judges required after repair.
running_workers: W1 F01 remediation, W2 F02 (w2/F02-execution-honesty, .worktrees/f02), W3 F03 (w3/F03-eval-fairness, .worktrees/f03), W5 F05 judges (2ed0948f code / d27584c2 science)
worker_contracts: docs/fleet/README.md + docs/fleet/F01..F05.md
integration_owner: primary VS Code orchestrator session (this session); merges F01→F02→F03→F05; F06 ticket must carry the 8 F04 carry-over items (see CP-20261008-F04.md)
latest_checkpoint: docs/checkpoints/CP-20261008-F04.md
next_action: (1) F01 science judge verdict → merge w1/F01-baseline-validity + full gate + checkpoint. (2) Await W2/W3/W5 handoffs → dual judges per ticket → merge in order F02→F03→F05. (3) Then write F06 ticket from NEED_DISPATCH.md + carry-overs, dispatch W6.
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
