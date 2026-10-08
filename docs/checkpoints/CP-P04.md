# Checkpoint CP-P04 — Decentralized Need Market (G4)

Status: DONE — committed `1b48ac2` on `p04/need-market` (worktree `.worktrees/p04`, base `b5f7bfb`). No merge (P07 integration gate owns merging).

## What was delivered
- `src/repliclaw/needmarket/` — needs.py, broker.py, policy.py, worker.py, replay.py, __init__.py
- `tests/test_needmarket.py` — 8 ticket-mandated tests (all green)
- `docs/fleet/handoff-P04.md` — commands/outputs/design decisions/NOT-PROVEN/attack list

## Gates (actual output, run from .worktrees/p04)
```
pytest:  74 passed, 8 skipped in 3.54s   (66 base + 8 new)
ruff:    All checks passed!
mypy:    Success: no issues found in 22 source files
```

## Evidence highlights (what the tests actually proved)
- Two **real OS subprocesses** raced one O_EXCL claim: exactly one `need_claimed` event, one winner, no partial lock files.
- SIGKILL crash matrix: parent observed the durable claim event, killed the claimer, lease expired after real 0.5 s TTL, second agent claimed at generation 2 and fulfilled; log had 2×claimed / ≥1×expired / 1×fulfilled.
- Frozen-clock expiry: re-claim wins at generation 2 via dead-lock tombstone (design fix during build — first draft's expire-unlink collapsed generation to 1; caught by test 2).
- T4: observed ranking flip on new evidence snapshot (I_R → I_J) with `choice_changed` event carrying prev/new ranking + snapshot sha + delta_reason.
- `NeedBroker` public surface contains no ranking/assignment API (asserted by inspection); claim requires agent_id.
- Budget enforcement: BudgetExhausted above remaining; spend accumulates per agent.
- All three policies deterministic under pinned (seed, snapshot); GreedyShared identical across agents.

## F04 carry-over closure (CP-20261008-F04)
1 → test 7 (open_needs closure); 2 → `eligible` reads `Need.required_capability` (v2-frozen field name; documented in handoff); 3 → tests 1 & 3 (real subprocesses); 5 → injectable clock + FrozenClock; 8 → verified-fulfilment disambiguation + duplicate suppression.

## NOT proven (scope honesty)
- Scientific superiority of local EIG ranking vs comparators (P05/P08).
- SimpleAudit wiring (blind `execute` callback by design; P07 injects P02 executor).
- Multi-worker end-to-end swarm run (P07 vertical slice).
- Real token metering (cost estimates are proposer-declared; P08 harness).

## Next
P07 integration: merge p02+p03+p04 branches, run merged gate, dual judges, then wire the vertical slice (escrow → need market → P02 executor → comparators at matched budget).
