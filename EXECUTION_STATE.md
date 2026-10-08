# RepliClaw — Execution State (v2 Evidence-Escrow program, post-migration)
Last updated: 2026-10-08 15:20 (new orchestrator session, post-PR#1-merge)
status: WORKING
program: EESS — Evidence-Escrow Scientific Swarm (docs/EVIDENCE_ESCROW_SWARM.md)
branch: repl-claw-dev
HEAD: post-merge of origin/strategy/evidence-escrow-swarm-20261008 (see merge commit)
current_milestone: P00 SAFE_MIGRATION (inventory DONE) → G0 re-verified → P02 first causal intervention NEXT
gate: G0 RE-VERIFIED @ main tree post-merge: **66 passed, 8 skipped** (pytest), ruff clean (src tests), mypy clean (16 files) — logs/G0-postmerge-20261008.txt
pre_pivot_checkpoint: docs/checkpoints/CP-PRE-PIVOT-20261008-fleet.md (authoritative inventory)
running_worker_state: NO live external workers observed (old fleet paused/cancelled at pivot; sessions unavailable to inspect → UNKNOWN per contract)
application_deadline: October 16, 2026 early; final hand-in format UNKNOWN until event

## Salvaged WIP inventory (all work preserved, worktrees clean)
| Worktree | Branch @ HEAD | State | Salvage map (old→new) |
|---|---|---|---|
| main | repl-claw-dev | G0 green; F04 design merged @ 2ccb629 | F00→P00, F04→P04 foundation |
| .worktrees/f01 | w1/F01-baseline-validity @ c4c95c8 | R1 landed; R2 re-review never ran | → P05 (open_debate/isolated_vote comparators = mandatory S2/S4) |
| .worktrees/f02 | w2/F02-execution-honesty @ 2afa7df | execution.py + runner/verifier; 2 red tests (self-attest, swapped-record), 1 mypy arity error | → P02 (machine-executed evidence/provenance for SimpleAudit adapter) |
| .worktrees/f03 | w3/F03-eval-fairness @ 32b6330 | 9 held-out fixtures + manifest + 10 RED eval-API tests; eval.py not started | → P05/P08 (denominators, paired metrics, held-out eval) |
| .worktrees/f05 | w5/F05-science-feasibility @ ef3584b | Tox21 AR-agonist case complete (McNemar p=0.009, claim_freeze.json); R2 pending | → P06 secondary case (held-out controlled case, offline) |

## Environment note (verified 2026-10-08)
- Anaconda system python 3.11 breaks pip build isolation. ALWAYS use a venv: main tree `.venv/`; each worktree `.worktrees/fNN/.venv/` (install `-e ".[dev,otel]"` from INSIDE the worktree).
- Live LLM API key exists in env but fleet workers are FORBIDDEN to use it (quota + fairness); live runs are P08-only with explicit budgets.
- Gate commands: `.venv/bin/python -m pytest` / `ruff check src tests` / `mypy src` (root-level ruff/mypy scan .venv — wrong targets, do not use).

## State update contract
Only the orchestrator/integration owner updates this file, after verifying underlying branch/tests. Record current ticket, owner/worktree, HEAD, gate status, command outputs, latest checkpoint, blockers and next action. Never mark COMPLETE without docs/QUALITY_GATES.md G6 and real-science evidence. Never infer running sessions just because a work plan exists.

## What completion really requires
Do not call COMPLETE until: real frozen SimpleAudit counterfactual interventions; verified pre-outcome independent commitments; unscripted locally selected and claimed subsequent experiment; final auditable evidence; correctly resource-matched strong adaptive manager comparisons; science/code reviews and clean replay; exact official hand-in verified; actual application submitted by human. Honest negative experiments acceptable, fabricated positive claims not.

## Next actions (P02 first)
1. Salvage f02 `execution.py` into main tree as the execution-honesty foundation (T3: machine-created run ID, hashes, logs, verifiable record).
2. Build P02: policy-RAG AI-failure case (retrieval omission) + frozen SimpleAudit-style counterfactual runner: 1-factor interventions (document presence / snippet order / instruction conflict / judge rubric), machine-produced hashes/configs/seeds/traces, clean replay, deterministic backend.
3. Red tests first; dual judges; checkpoint CP-P02.
4. Then P03 (escrow ledger) and P04 (need market via f04 design) in parallel worktrees.
