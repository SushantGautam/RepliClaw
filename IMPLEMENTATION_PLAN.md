# RepliClaw — Active ScienceClaw competition implementation plan
Updated: 2026-10-08 (Wave A dispatched). **This replaces the old M0–M10 TODO list as current program; prior prototype remains preserved and is not competition COMPLETE.**
Authoritative rubric and goals: docs/COMPETITION_STRATEGY.md. Fleet: docs/FLEET_PLAYBOOK.md. Gates: docs/QUALITY_GATES.md. Status cursor: EXECUTION_STATE.md. Worker contracts: docs/fleet/F01..F05.md.

## Tickets and dependencies
| Ticket | Priority | Stage | Status | Owner | Depends | Acceptance (do not mark DONE without observed evidence) |
|---|---|---|---|---|---|---|
| F00 baseline | P0 | G0 | DONE (2026-10-08, logs/G0-baseline-20261008.txt) | integrator | none | rerun pytest/ruff/mypy from HEAD, capture git status, benchmark provenance |
| F01 valid comparators | P0 | G1–G5 | IN_PROGRESS (worktree .worktrees/f01, w1/F01-baseline-validity) | W1 | F00 | debate receives peer contexts; vote truly counts votes; regression tests |
| F02 verified executions | P0 | G1–G5 | IN_PROGRESS (worktree .worktrees/f02, w2/F02-execution-honesty) | W2 | F00 | executed commands, logs, hashes, actual result; model self-attestation rejected |
| F03 evaluation fairness | P0 | G1–G5 | IN_PROGRESS (worktree .worktrees/f03, w3/F03-eval-fairness) | W3 | F00 | seeded heldout runs, no label leakage, paired budget parity, actual recovery transition, CIs |
| F04 decentralized dispatch spike | P0 | G1 | IN_PROGRESS design-only (worktree .worktrees/f04, w4/F04-need-dispatch) | W4 | F00 | design/contract: ScienceClaw NeedItem/Reactor, worker ownership, leases, retries, isolation |
| F05 real-science case | P0 | G1–G4 | IN_PROGRESS (worktree .worktrees/f05, w5/F05-science-feasibility) | W5 | F00 | runnable external scientific case, dataset provenance and saved outputs |
| F06 distributed execution | P0 | G1–G5 | NOT_STARTED | integrator/feature worker | F04,F02 | needs independently claimed and fulfilled across separate worker processes; failure recovery |
| F07 blind integrity | P0 | G1–G5 | NOT_STARTED | integrator/feature worker | F01,F06 | per-investigator commit-before-peer visibility, adversarial test and provenance proof |
| F08 real live science eval | P0 | G3–G5 | NOT_STARTED | experiment lead | F01,F02,F03,F05,F06,F07 | matched comparator+ablations, science-judge approved results, negative results intact |
| F09 cross-team trial | P1 | G3–G5 | NOT_STARTED | integration lead | F06,F08 | actual independent team invokes verify, saved report and feedback |
| F10 demo + submission | P0 | G6 | NOT_STARTED | integrator | F08,F09* | reproducible hero science result, README accuracy, demo trace, official requirements checked |

*F09 is bonus-target; no invented usage if no external team available.

## Parallel wave and integration order
Wave A: F01, F02, F03 editing in isolated worktrees; F04 and F05 read-only/spike or separate owned paths; two independent reviews. Integrate F01/F02/F03 sequentially after gates. Freeze cross-module interfaces before simultaneous editing. Wave B: F06 (dispatch) + scientific experiment preparations + F07 adversarial isolation. Wave C: F08 repeated live experiments and F09 cross-team integration. Wave D: F10 clean-install/checkpoint and hand-in.

## Core pass/fail rules
Do NOT treat a green 66-test prototype as competition success. Require G0–G6 and reviewer reports for P0 tickets. After EACH integrated deliverable: update state, append progress and write docs/checkpoints/CP-<id>.md with HEAD SHA, exact tests, observed results, confidence limits and next actions. Every changed metric must derive from run artifacts, never from a desired score.

## Risks and limits
- LLM provider quota/reliability: cap calls/cost; offline deterministic suite must remain functional.
- Agent mode support varies by VS Code extension/harness. Detect support, otherwise work sequentially and present exact worktree instructions.
- Real science data access/licenses require audit and reproducibility manifest.
- No verified published final submission form or video length as of 2026-10-08.
- No external irreversible action without human consent.
