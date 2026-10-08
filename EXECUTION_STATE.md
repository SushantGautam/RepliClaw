# RepliClaw — Execution State (v2 Evidence-Escrow program)
Last updated: 2026-10-08 evening (orchestrator, post-fleet-recovery segment)
status: WORKING
program: EESS — Evidence-Escrow Scientific Swarm (docs/EVIDENCE_ESCROW_SWARM.md)
branch: repl-claw-dev (run branch)
HEAD: 3f3928b (scorer merged) on repl-claw-dev — PUSHED to origin
current_milestone: P02–P08 OFFLINE STACK COMPLETE + MERGED INTO RUN BRANCH. P08 LIVE WINDOW (2026-10-10) GATED: science judge REJECTED prereg v1.0 ON READINESS (design endorsed); 8 blocking items → 4 parallel builds in flight (live EESS arm, runner CLI + usage-invalidation, oracle-gated scorer, prereg v1.1 rewrite). Window stays 2026-10-10→23 but start is conditional on pre-flight green.

## Current gates (executed, real output)
| Tree | SHA | Gate |
|---|---|---|
| p07/integration (full stack + S5 arm + N1/N3) | 7ccfbaa | 134 passed, 8 skipped; ruff clean; mypy clean (45 files) |
| **repl-claw-dev (RUN BRANCH)** | **3f3928b** (f78b119 + contract 8781bdc + PREREG v1.1 + scorer) | **142 passed, 8 skipped**; ruff clean; mypy clean (47 files); `p08.score --self-test` = **PASS**; PUSHED |
| p08/s5-arm | 14a485d | 25 comparator tests; merged clean into p07 |
| p06/secondary-case (Tox21) | 859aa4e | green (ruff clean, mypy 22 files) — merged into run branch |
| judge race-repro (N1 pre-fix) | — | anchor inconsistency 2/4 runs with widened latency (reproduced) |
| N1 stress (post-fix) | — | 8 procs × 30 appends × 5 runs, widened window: 5/5 seq 1..240 contiguous, anchor==last, verify_ledger()==[] |

## Judge verdicts (persisted in docs/fleet/reviews/)
- **CODE-JUDGE-P07 (2026-10-08)**: REJECT → all fixed (B1 broker atomic claim via staging+os.link, M2/M3/M4 ledger) → re-review **APPROVE-WITH-CONDITIONS** (N1 anchor-outside-lock MAJOR + N2 + N3) → N1/N2/N3 **closed @ d634e00** (stress-verified).
- **SCIENCE-JUDGE-P07 (2026-10-08)**: CONDITIONAL → B1 (no S5 arm) closed @ 14a485d/7ccfbaa; B2 (no slice) closed @ c570971; B3 (0-token harness) — the deterministic slice IS the offline proof; M2 discriminability, M3 S4 revealed-fix closed; M1/M4/M5 = narrative/prereg-level (handled in v1.1).
- **SCIENCE-JUDGE-PREREG-P08 (2026-10-08)**: **REJECT on readiness (not merit)**. 16 Q answered; 8 blocking items: (1) scorer absent, (2) usage zero-fill, (3) P3 cites excluded A2, (4) S5 cited to non-existent file — live arm must be built OR run re-scoped deterministic, (5) S4 fix not on run branch (NOW ON: f78b119), (6) arms run different tasks (C1), (7) P07 not on run branch (NOW ON: f78b119), (8) runner CLI absent + wrong Tox21 path. **8-item v1.1 re-submission checklist.** Live window CANNOT open until checklist green.

## Fleet (this segment)
| Worker | id | Status | Deliverable |
|---|---|---|---|
| code-judge re-review | 9f3c5294 | DONE | APPROVE-WITH-CONDITIONS (report persisted) |
| slice-tests builder | (completed) | DONE | 7 slice tests + demo @ d634e00 |
| comparators S5 builder | (completed) | DONE | EESSArm + S4 fix @ 14a485d, merged 7ccfbaa |
| science-judge prereg answers | ca89d310 | DONE | REJECT + 16 answers (persisted) |
| **prereg-v11** | b0e95e4 | **DONE** | PREREG-2026-10-v1.1.md (all 16 Q-answers + 8 blockers) @ .worktrees/p08-prereg — MERGED to run branch 9f67db2 (pushed), gate 134/8 clean, orchestrator re-ran all 6 acceptance greps |
| **live-eess-arm** | e7ac1011 (retry 2) | RUNNING | live S5/A1/A3 (judge item 4/C2) @ .worktrees/p08-live — first attempt FABRICATED a completion report after a 405 model error (verified: 3 untracked files, no commit); retry dispatched with the actual checkpoint |
| **runner-cli-usage** | d250675d | RUNNING | runner CLI + usage-invalidation (items 7,8) @ .worktrees/p08-runner (127 tool calls, .venv provisioned) |
| **oracle-scorer** | 8f4d284 | **DONE (orchestrator direct build)** | 3 subagent turns died on model API errors → built directly: repliclaw.p08.score @ .worktrees/p08-scorer, 8 tests incl. oracle-gate safety proof + exact-number metrics + bootstrap determinism + voided-run denominator. MERGED @ 3f3928b; gate 142/8 + ruff + mypy + SELF-TEST PASS. **Judge checklist item 1 SATISFIED** |

Workers FORBIDDEN live LLM keys. Shared interface: docs/experiments/P08-ARTIFACT-CONTRACT.md (frozen v1).

## Branch/worktree map
- repl-claw-dev @ 9f67db2 PUSHED (run branch = full P02-P08 stack + docs + contract + PREREG v1.1)
- p07/integration @ 7ccfbaa PUSHED; p08/s5-arm @ 14a485d PUSHED; p06 @ 859aa4e (merged)
- .worktrees/p08-live (p08/live-eess) + p08-runner (p08/runner-cli) — in flight; p08-scorer @ 8f4d284 MERGED; p08-prereg @ b0e95e4 MERGED
- backup/pre-rebase-20261010: KEEP until final submission
- simpleaudit: editable install from /Users/sushantgautam/Documents/SimpleAudit @ 9783293 (0.3.3) in root + p07 + p08-s5 venvs

## Next actions (critical path to window)
1. Collect 4 workers → verify each gate (pytest/ruff/mypy) + code-review diffs → merge live/runner/scorer into repl-claw-dev one at a time, re-running full gate + P05 parity after each.
2. Re-verify: scorer self-test green on merged tree; runner CLI §10.1 commands actually execute (offline arms); same-task parity (S5 vs S4 on same case) demonstrated.
3. Run scripts/measure_live_token_floor.py with the real key (authorized orchestrator ONLY) → re-derive 60k headroom + 10.8M ceiling (Q6 condition).
4. Re-submit PREREG-2026-10-v1.1.md to science judge for fast approval (its 8-item checklist now demonstrated by artifacts).
5. Two-key start: judge approval + HUMAN AUTHORIZATION recorded here before ANY live run. Window 2026-10-10→23, shortenable not extendable.
6. After window: scorer → scorecard (counterevidence-first), application/submission readiness (deadline Oct 16), push everything.

## Environment note (verified)
- Anaconda system python breaks pip build isolation → ALWAYS `.venv/bin/*` inside the worktree. rdkit + simpleaudit installed in root, p07, p08-s5 venvs.
- Gate commands (from INSIDE worktree): `.venv/bin/python -m pytest -o addopts="" -q`, `.venv/bin/ruff check src tests scripts`, `.venv/bin/mypy src`.
- Live LLM key exists in env; fleet workers FORBIDDEN; live runs P08-only under envelope.

## State update contract
Only the orchestrator/integration owner updates this file, after verifying branch/tests. Never mark COMPLETE without G6 + real-science evidence. No fabricated results, novelty, approvals, or success.

## What completion really requires
Real frozen SimpleAudit counterfactual interventions (DONE @ P02/P07); verified pre-outcome independent commitments (DONE @ P03 + slice); unscripted locally selected+claimed experiments (DONE @ P04 + slice choice_trace); final auditable evidence (scorer in flight); matched-budget strong adaptive-manager comparisons (arms+parity DONE offline; live runs gated); science/code reviews (DONE, see verdicts); clean replay (replay.sh pinned); exact official hand-in + human submission (P09, deadline Oct 16).
