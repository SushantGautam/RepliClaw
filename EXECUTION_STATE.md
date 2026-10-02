# RepliClaw — Execution State (v2 Evidence-Escrow program)
Last updated: 2026-10-08 21:00 (orchestrator, post-live-arm-reconciliation segment)
status: WORKING
program: EESS — Evidence-Escrow Scientific Swarm (docs/EVIDENCE_ESCROW_SWARM.md)
branch: repl-claw-dev (run branch)
HEAD: d4c6f6b on repl-claw-dev (live arm merged @ d0cb054 + arms.py cleanup d3beaeb + prereg v1.1 erratum d4c6f6b)
current_milestone: P08 LIVE WINDOW (2026-10-10→23) PRE-FLIGHT. Live-S5 arm BUILT + MERGED + tested (judge checklist items 1 scorer + 2 live-arm now DONE; token-floor measurement in flight). Runner CLI + same-task + usage-invalidation still in flight (e7ac1011). D-10 hyperparameter-pin is a newly-open pre-flight requirement.

## Current gates (executed, real output)
| Tree | SHA | Gate |
|---|---|---|
| **repl-claw-dev (RUN BRANCH)** | **d3beaeb** (f78b119 + contract + PREREG v1.1 + scorer 3f3928b + live-arm merge d0cb054 + arms.py cleanup d3beaeb; erratum d4c6f6b) | **149 passed, 8 skipped**; ruff clean; mypy clean (54 files); `p08.score --self-test` PASS; 5 parity tests pass |
| p08/live-eess (live S5/A1/A3 arms) | 9022138 (1806cd2 + 2 integration commits) | **141 passed, 8 skipped**; ruff clean; mypy clean (53 files); tree clean; MERGED into run branch |
| p07/integration (full stack + S5 arm + N1/N3) | 7ccfbaa | 134 passed, 8 skipped; ruff clean; mypy clean (45 files) |
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
| **live-eess-arm** | d250675d | **DEAD → work RECONCILED by orchestrator** | live S5/A1/A3 (judge item 4/C2) @ .worktrees/p08-live @ 9022138 (3 commits over f78b119). Worker handoff committed 1806cd2, then flushed a final divergent batch at 20:32 and exited. Orchestrator reconciled: kept its 642-line orchestrator (judge-item-7 usage hardening intact) + escrow/accounting/budget_calls/fake; restored contract arm.py (work_dir/run-01, prereg keys, 22-key final_verdict) from 1806cd2; deleted deviant arms.py + comparators/arm_registry.py; restored my 7-test contract suite. Gate @ 9022138: **141 passed, 8 skipped; mypy clean (53 files); ruff clean; tree clean**. NOTE: its escrow-seam security tests (PhaseViolation gating, owner-only reveal, foreign-file guard) were lost in the final flush and are worth re-adding in a future pass (low priority). |
| **runner-cli-usage** | e7ac1011-6231 | RUNNING (7500s, 357 tool calls, 0 completed turns) | runner CLI + usage-invalidation (items 7,8) @ .worktrees/p08-runner (tree still clean @ f78b119 — work in flight, not committed yet). Do NOT duplicate. |
| **oracle-scorer** | 8f4d284 | **DONE (orchestrator direct build)** | 3 subagent turns died on model API errors → built directly: repliclaw.p08.score @ .worktrees/p08-scorer, 8 tests incl. oracle-gate safety proof + exact-number metrics + bootstrap determinism + voided-run denominator. MERGED @ 3f3928b; gate 142/8 + ruff + mypy + SELF-TEST PASS. **Judge checklist item 1 SATISFIED** |
| **code-judge-live-eess** | 466e3ae5 | RUNNING (read-only) | Independent Code Judge on p08/live-eess @ 9022138 (escrow seam, budget integrity, A3 determinism, offline parity, test adequacy). Report → docs/fleet/reviews/CODE-JUDGE-P08-LIVE.md. |
| **token-floor-measure** | 1670f65f | RUNNING | `scripts/measure_live_token_floor.py` + real-key live S5 floor run @ .worktrees/p08-tokenfloor (p08/token-floor). **AUTHORIZED the live key** (judge item 2/F). Artifact artifacts/p08/live_token_floor/floor.json. |

Workers FORBIDDEN live LLM keys EXCEPT token-floor-measure (single authorized measurement, <25k tokens). Shared interface: docs/experiments/P08-ARTIFACT-CONTRACT.md (frozen v1).

## Branch/worktree map
- **repl-claw-dev @ d4c6f6b PUSHED** (run branch = full P02-P08 stack + docs + contract + PREREG v1.1 + scorer + live arm; 149 passed/8 skipped, ruff+mypy clean)
- p07/integration @ 7ccfbaa PUSHED; p08/s5-arm @ 14a485d PUSHED; p06 @ 859aa4e (merged)
- p08/live-eess @ 9022138 MERGED (d0cb054); p08/scorer @ 8f4d284 MERGED (3f3928b); p08-prereg @ b0e95e4 MERGED
- .worktrees/p08-runner (p08/runner-cli @ f78b119, worker in flight) + .worktrees/p08-tokenfloor (p08/token-floor, live-key measurement in flight)
- backup/pre-rebase-20261010: KEEP until final submission
- simpleaudit: editable install from /Users/sushantgautam/Documents/SimpleAudit @ 9783293 (0.3.3) in root + p07 + p08-s5 venvs

## Next actions (critical path to window)
1. Collect token-floor (1670f65f) → verify measured floor.json + gate → merge p08/token-floor into repl-claw-dev → fill PREREG §5.1 with measured floor + re-derived budget/ceiling, commit before two-key start.
2. Collect code-judge-live-eess (466e3ae5) → fix any BLOCKER/MAJOR findings on p08/live-eess → re-merge + re-gate.
3. runner-cli-usage (e7ac1011-6231): collect → verify §10.1 CLI commands execute offline + same-task (case_loader) + usage-invalidation + D-10 hyperparameter pin (λ=μ=0.5, max_cycles=6, TTL=120s wired + pre-flight assertion) → full gate → merge.
4. Re-submit PREREG-2026-10-v1.1.md (erratum d4c6f6b) to science judge ca89d310 for approval.
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
