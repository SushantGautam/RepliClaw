# RepliClaw — Execution State (v2 Evidence-Escrow program, post-migration)
Last updated: 2026-10-10 (orchestrator session, post-P02)
status: WORKING
program: EESS — Evidence-Escrow Scientific Swarm (docs/EVIDENCE_ESCROW_SWARM.md)
branch: repl-claw-dev
HEAD: post-merge of origin/strategy/evidence-escrow-swarm-20261008 (see merge commit)
current_milestone: P02 COMPLETE (committed 3f452b2, gates green) → P03 escrow + P04 need-market NOW (built directly in .worktrees/p03, .worktrees/p04 — builder agents confirmed non-functional in this environment after 2 fresh-dispatch attempts each)
gate: P02 gates @ .worktrees/p02: pytest 62 passed/8 skipped, ruff clean, mypy clean (21 files) — docs/checkpoints/CP-P02.md; G0 post-merge main tree still 66 passed/8 skipped — logs/G0-postmerge-20261008.txt
pre_pivot_checkpoint: docs/checkpoints/CP-PRE-PIVOT-20261008-fleet.md (authoritative inventory)
running_worker_state: NO live external workers observed (old fleet paused/cancelled at pivot; sessions unavailable to inspect → UNKNOWN per contract)
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
| .worktrees/p03 | p03/evidence-escrow (new) | bootstrap only, build in progress (direct) | escrow ledger |
| .worktrees/p04 | p04/need-market (new) | bootstrap only, build in progress (direct) | need market |

## Environment note (verified 2026-10-08)
- Anaconda system python 3.11 breaks pip build isolation. ALWAYS use a venv: main tree `.venv/`; each worktree `.worktrees/fNN/.venv/` (install `-e ".[dev,otel]"` from INSIDE the worktree).
- Live LLM API key exists in env but fleet workers are FORBIDDEN to use it (quota + fairness); live runs are P08-only with explicit budgets.
- Gate commands: `.venv/bin/python -m pytest` / `ruff check src tests` / `mypy src` (root-level ruff/mypy scan .venv — wrong targets, do not use).

## State update contract
Only the orchestrator/integration owner updates this file, after verifying underlying branch/tests. Record current ticket, owner/worktree, HEAD, gate status, command outputs, latest checkpoint, blockers and next action. Never mark COMPLETE without docs/QUALITY_GATES.md G6 and real-science evidence. Never infer running sessions just because a work plan exists.

## What completion really requires
Do not call COMPLETE until: real frozen SimpleAudit counterfactual interventions; verified pre-outcome independent commitments; unscripted locally selected and claimed subsequent experiment; final auditable evidence; correctly resource-matched strong adaptive manager comparisons; science/code reviews and clean replay; exact official hand-in verified; actual application submitted by human. Honest negative experiments acceptable, fabricated positive claims not.

## Next actions
1. P03 (evidence escrow ledger) directly in .worktrees/p03 (branch p03/evidence-escrow, bootstrap .venv created): pre-outcome commitments, sealed reveal, tamper-evidence; red tests first per docs/fleet/P03.md.
2. P04 (need market) directly in .worktrees/p04 (branch p04/need-market, bootstrap .venv created): O_EXCL atomic claim, lease expiry, only-verified-fulfilment; f04 carry-overs 1/2/3/5/8 binding per docs/fleet/P04.md.
3. Integrate P02+P03+P04 into one branch + run G0-equivalent merged gate; dual judges (code + science) per ticket.
4. Then P05 comparators (salvage f01+f03), P06 (f05 Tox21 secondary case), P07 vertical slice, P08 live runs (prereg + science-judge approval FIRST), P09 application.
