# RepliClaw — Execution State (v2 Evidence-Escrow program, post-migration)
Last updated: 2026-10-10 (orchestrator session, post-P04)
status: WORKING
program: EESS — Evidence-Escrow Scientific Swarm (docs/EVIDENCE_ESCROW_SWARM.md)
branch: repl-claw-dev
HEAD: 50dd599 (state) on repl-claw-dev
current_milestone: P02+P03+P04 ALL COMPLETE (committed, gates green) → P05 comparators + P06 secondary case running as background builder agents in .worktrees/p05, .worktrees/p06
gate: P02 @ 3f452b2: 62 passed/8 skipped, ruff+mypy clean; P03 @ ba71a4d: 69 passed/8 skipped, ruff+mypy clean; P04 @ 1b48ac2: 74 passed/8 skipped, ruff clean, mypy clean (22 files) — docs/checkpoints/CP-P02.md, CP-P03.md, CP-P04.md
pre_pivot_checkpoint: docs/checkpoints/CP-PRE-PIVOT-20261008-fleet.md (authoritative inventory)
running_worker_state: 3 background agents live — p05-comparators (1047a496, RepliClaw Builder, non-thinking model), p06-secondary-case (d7624f80, RepliClaw Builder), novelty-research (0bb3b985, research agent)
application_deadline: October 16, 2026 early; final hand-in format UNKNOWN until event

## Salvaged WIP inventory (all work preserved, worktrees clean)
| Worktree | Branch @ HEAD | State | Salvage map (old→new) |
|---|---|---|---|
| main | repl-claw-dev | G0 green; F04 design merged @ 2ccb629 | F00→P00, F04→P04 foundation |
| .worktrees/f01 | w1/F01-baseline-validity @ c4c95c8 | R1 landed; R2 re-review never ran | → P05 (open_debate/isolated_vote comparators = mandatory S2/S4) |
| .worktrees/f02 | w2/F02-execution-honesty @ 2afa7df | execution.py + runner/verifier; 2 red tests (self-attest, swapped-record), 1 mypy arity error | → P02 DONE (execution.py ported; 6/6 green) |
| .worktrees/f03 | w3/F03-eval-fairness @ 32b6330 | 9 held-out fixtures + manifest + 10 RED eval-API tests; eval.py not started | → P05/P08 (denominators, paired metrics, held-out eval) |
| .worktrees/f05 | w5/F05-science-feasibility @ ef3584b | Tox21 AR-agonist case complete (McNemar p=0.009, claim_freeze.json); R2 pending | → P06 secondary case (held-out controlled case, offline) |
| .worktrees/p02 | p02/simpleaudit-counterfactual @ 3f452b2 | counterfactual/ package + execution.py + policy_rag_v1 canonical run (replay.sh pinned); 12 new tests green | DONE — merge at P07 integration gate |
| .worktrees/p03 | p03/evidence-escrow @ ba71a4d | escrow/ package (packet+phase+ledger+verify); 7 red-first tests green; 69 passed/8skipped, ruff+mypy clean | DONE — merge at P07 integration gate |
| .worktrees/p04 | p04/need-market @ 1b48ac2 | needmarket/ package (needs/broker/policy/worker/replay); 8 red-first tests incl. real-subprocess race + SIGKILL crash; 74 passed/8skipped, ruff+mypy clean | DONE — merge at P07 integration gate |
| .worktrees/p05 | p05/comparators (bg builder agent 1047a496) | build in progress | matched-budget comparators |
| .worktrees/p06 | p06/secondary-case (bg builder agent d7624f80) | build in progress | Tox21 secondary case (salvage f05) |

## Environment note (verified 2026-10-08)
- Anaconda system python 3.11 breaks pip build isolation. ALWAYS use a venv: main tree `.venv/`; each worktree `.worktrees/fNN/.venv/` (install `-e ".[dev,otel]"` from INSIDE the worktree).
- Live LLM API key exists in env but fleet workers are FORBIDDEN to use it (quota + fairness); live runs are P08-only with explicit budgets.
- Gate commands: `.venv/bin/python -m pytest` / `ruff check src tests` / `mypy src` (root-level ruff/mypy scan .venv — wrong targets, do not use).

## State update contract
Only the orchestrator/integration owner updates this file, after verifying underlying branch/tests. Record current ticket, owner/worktree, HEAD, gate status, command outputs, latest checkpoint, blockers and next action. Never mark COMPLETE without docs/QUALITY_GATES.md G6 and real-science evidence. Never infer running sessions just because a work plan exists.

## What completion really requires
Do not call COMPLETE until: real frozen SimpleAudit counterfactual interventions; verified pre-outcome independent commitments; unscripted locally selected and claimed subsequent experiment; final auditable evidence; correctly resource-matched strong adaptive manager comparisons; science/code reviews and clean replay; exact official hand-in verified; actual application submitted by human. Honest negative experiments acceptable, fabricated positive claims not.

## Next actions
1. Await P05 (comparators) and P06 (secondary case) background builders → verify their gates, dual-judge review, integrate.
2. Integrate P02+P03+P04 into one branch + run G0-equivalent merged gate; dual judges (code + science) per ticket.
3. P07 vertical slice (wire P02 executor into P04 worker `execute` callback; P03 escrow around predictions; P05 comparators at matched budget).
4. P08 live runs (preregistration + science-judge approval FIRST), P09 application/submission readiness (deadline Oct 16).
5. Push local commits to origin when safe (main is 17+ ahead).
