# RepliClaw fast-finish status (coordinator-owned)

**As of 2026-10-11, instructions committed, NOT evidence of fleet startup.**

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
| FF-01 CI clean install | QUEUED | rc-fast | none | remote CI failure |
| FF-02 label isolation | QUEUED | rc-implement | none | oracle exposure |
| FF-03 judge/statistical correction | QUEUED | rc-review | none | dependent on specific artifact |
| FF-04 actual intervention parity | WAITING | pending | existing ceq.py | P0 gates |
| FF-05 exploratory multi-case pilot | WAITING | pending | none | parity + case availability |
| FF-06 prereg freeze/approvals | WAITING | pending | v3 draft | pilot + judge signoff |
| FF-07 heldout results | WAITING | pending | none | FF-06 |

## Human gate / known stop
A final heldout run requires prospectively frozen V3, independent science signoff and approved use of resources under existing G4. No new live comparative results are claimed here. Do not change this row until the approval artifact exists.
