# RepliClaw fast-finish status (coordinator-owned)

**As of 2026-10-11 19:30 UTC (fleet mode, native subagents):** BYOK inherit fix verified — `settings.json` sets rc-fast/rc-implement/rc-review to `model: inherit`; rc-fast native canary passed and telemetry confirms it ran on the inherited `sigma2.no/Qwen3.8-27B-Thinking` (no hosted fallback). Three native subagents now running in parallel on worktrees: FF-02 independent review (rc-review, of commit 7028865), FF-03 null-model completion (rc-implement, from WIP 63b3cfe), FF-04 intervention-parity tests (rc-implement). FF-05 fake full-pilot rehearsal verified the harness end-to-end (both arms + scoring + ledger + stop rules; stop1_ssat tripped correctly on fake saturation, both arms equal). FF-05 live pilot BLOCKED on SIMULACHAT provider env.

## Primary goal
An intervention-matched multi-case D-E vs C-EQ result, no false claims of escrow/decentralization superiority.

## Known starting facts
- main `97a455947...` frozen P08; dev previously inspected at `4f54d757...`. Re-read actual `git rev-parse HEAD` at execution start.
- P08: 120 runs, one case, intervention-access effect; escrow/decentralization unproven.
- C-EQ module exists on dev; 352 passed / 8 skipped reported by prior local gate, **no new execution from this status file**.
- GitHub public main CI on 2026-10-09 failed collection: `simpleaudit` / `opentelemetry` dependencies absent from clean install; fix/re-run gate.
- RCAEval: 735 indexed cases, 42 candidate cases, 10-case BARO RE1/RE2 CPU smoke; **observational only**.
- AgentRx: 73 annotated accessible trajectories; official LLM judge baseline not yet run. **DEFER from critical path**.
- AIOpsLab: upstream interface documented; real cluster and equal intervention reset **not verified**. Fast feasibility only, no unapproved cloud deployment.
- Leakage risk: root-cause-service-derived ordinal and case ID may still reveal answers; independent hostile test required.
- Statistical concern: forced one-arm saturation with otherwise equal nominal Δ does NOT preserve true zero effect; correct null simulation and reassess stop-rule interpretation.

## Execution queue (update at real checkpoint, not every hook)
| Task | Status | Owner | Latest artifact/command | Blocker |
|---|---|---|---|---|
| FF-01 CI clean install | DONE | coordinator (direct; subagent registry was stale this session) | dev @ c0cda69; CI run 38166853788 success (3.11+3.12 install/pytest/ruff/mypy); fresh-venv repro green | none |
| FF-02 label isolation | RUNNING | rc-implement (fresh-process dispatch, worktree ff02-label-isolation) | ticket: remove decodable quota_service_order, failing-then-passing adversarial test, G2 docstring close | none |
| FF-03 judge/statistical correction | RUNNING | rc-review (fresh-process dispatch, worktree ff03-null-model) | ticket: null-model amendment doc + independent contamination canary + verdict | none |
| FF-04 actual intervention parity | RUNNING | rc-implement (fresh-process dispatch, worktree ff04-intervention-match) | ticket: action-menu/budget/environment parity + no-oracle/no-fixed-script/no-starvation tests | none |
| FF-05 exploratory multi-case pilot | WAITING | pending | none | parity + case availability |
| FF-06 prereg freeze/approvals | WAITING | pending | v3 draft | pilot + judge signoff |
| FF-07 heldout results | WAITING | pending | none | FF-06 |

## Human gate / known stop
A final heldout run requires prospectively frozen V3, independent science signoff and approved use of resources under existing G4. No new live comparative results are claimed here. Do not change this row until the approval artifact exists.
