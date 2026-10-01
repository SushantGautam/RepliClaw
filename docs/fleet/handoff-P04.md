# P04 Handoff — Decentralized Need Market (G4)

Branch: `p04/need-market` (worktree `.worktrees/p04`, base `b5f7bfb`)
Contract: EESS contract §4 + F04 design `docs/design/NEED_DISPATCH.md` §4–§7; ticket `docs/fleet/P04.md`.

## What was built (all new, no pre-existing code on this branch)

| File | Contents |
|---|---|
| `src/repliclaw/needmarket/needs.py` | `Need` (schema `repliclaw.need/v1`, frozen, status pattern), `CostEstimate`, `WorkerCapability`, `eligible(need, cap)` pure self-check |
| `src/repliclaw/needmarket/broker.py` | `NeedBroker`: append-only `needs.jsonl` + `events.jsonl`, O_EXCL lease files under `locks/` (the lock file *is* the lease), injectable `clock` for frozen-time tests, budget enforcement, exactly-once verified fulfilment, **no ranking API** |
| `src/repliclaw/needmarket/policy.py` | `ActionPolicy` protocol; `LocalEigPolicy` (U = gain/cost + λ·diversity − μ·crowding, fully transparent components+reason), `RandomPolicy` (seeded, deterministic), `GreedySharedPolicy` (agent-agnostic comparator) |
| `src/repliclaw/needmarket/worker.py` | `NeedWorker.cycle()`: open_needs → eligible → local rank → `choice_ranked` event (before claim) → claim → blind `execute(need)` callback → `fulfill(verified=…)`; `choice_changed` event when a new evidence snapshot changes the ranking; `run(max_cycles)` |
| `src/repliclaw/needmarket/replay.py` | `snapshot(evidence)` (canonical sha256), `replay_events`, `ranking_from_events` (P07 counterfactual-replay support) |
| `src/repliclaw/needmarket/__init__.py` | Public surface |
| `tests/test_needmarket.py` | The 8 ticket-mandated tests |

## Gate (run from `.worktrees/p04`, actual output)

```
.venv/bin/python -m pytest          → 74 passed, 8 skipped in 3.54s
.venv/bin/python -m ruff check src tests  → All checks passed!
.venv/bin/python -m mypy src       → Success: no issues found in 22 source files
```

(66 base tests from `b5f7bfb` + 8 new need-market tests = 74. Skips are the
pre-existing 8 conditional skips from the base branch.)

## The 8 tests → behavior proven

1. `test_atomic_claim_two_processes` — two **real OS subprocesses** race one
   O_EXCL claim (barrier-released): exactly one `need_claimed` event, exactly
   one winner marker, lock names the winner, no partial lock files. (F04
   carry-over 3: real processes, not threads/Locks.)
2. `test_lease_expiry_reclaim` — frozen clock: live lease blocks; after TTL
   the re-claim wins at **generation 2** (dead lock kept as generation
   tombstone — design fix during this build, see below); `need_expired`
   emitted; first verified fulfilment (superseded holder → `late_fulfilment`)
   marks done exactly once, second verified fulfilment suppressed.
3. `test_crash_recovery` — claimer SIGKILLed after durable claim (parent polls
   the event log, not the stdout); real monotonic clock on both processes;
   lease expires after 0.5 s TTL; second agent claims at generation 2 and
   fulfils; log: 2×claimed, ≥1×expired, 1×fulfilled.
4. `test_no_central_ranking` — inspecting `NeedBroker` public methods: no
   rank/assign/allocate/choose/select/order API; `claim` requires `agent_id`;
   `open_needs` preserves publication order (filter, not ranking).
5. `test_evidence_changes_choice` (T4) — snapshot A ranks I_R first (claimed);
   new evidence (I_J_judge_fix published) + `set_discriminability` → snapshot B
   (different sha) → agent claims I_J instead; `choice_changed` event fired
   with `prev_ranking != new_ranking`, `snapshot_sha`, `delta_reason`.
   Assertion is on the **observed** ranking difference, not a mock.
6. `test_policy_determinism` — all three policies: same (needs, snapshot,
   seed) → identical ranking across two instances; `GreedySharedPolicy`
   produces identical (need_id, utility) lists for two different agents
   (the anti-pattern property).
7. `test_open_needs_excludes_leased_fulfilled` (carry-over 1) — live-leased
   and fulfilled needs are gone from `open_needs` for any agent, including
   the proposer.
8. `test_budget_enforced` — `BudgetExhausted` when cost > remaining; spend
   accumulates across fulfilled claims (100 spent → 0 remaining); a second
   agent with its own budget is unaffected.

## Design decisions made during build (deviations from first draft)

- **`expire_due` does NOT unlink dead locks.** First draft unlinked on expiry
  and every re-claim regressed to generation 1 (test 2 caught it). Final: the
  dead lock file is a *generation tombstone*; `claim()` takes the
  FileExistsError path, computes `generation + 1`, and only the O_EXCL winner
  unlinks and recreates. This keeps generation monotonic and crash-safe
  (a process killed between expiry and re-claim leaves a parseable tombstone).
  `expire_due` is idempotent (one `need_expired` per need+generation).
- **`events()` public** (was `read_events`) — workers and tests read the log;
  `record(kind, **payload)` is the public append path for worker-side events
  (`choice_ranked`, `choice_changed`, `abstained`) so the broker still owns
  the file but never interprets scientific content.
- **Worker abstain events** (`abstained`) are recorded with a `reason`
  (no open needs / no eligible need / claim lost / budget) — T4 traceability.
- **Fulfilment semantics kept exactly per F04 §4.3/§4.5**: unverified →
  event only + lease release; verified with no live holder-matching lease →
  `late_fulfilment` flag, still marks done; duplicate verified →
  `fulfilment_duplicate_suppressed`.

## F04 checkpoint carry-over mapping (CP-20261008-F04, "must-fix items from both judges")

1. open_needs closure (live-leased / fulfilled / cancelled / own-proposed)
   — **test 7**.
2. Eligibility reads the capability field named by the contract. Under the
   frozen v2 contract (EESS_CONTRACTS §4, schema `repliclaw.need/v1`) the
   field is `Need.required_capability` (the F06-era `NeedItem.preferred_skills`
   was renamed in the v2 freeze); `eligible()` reads exactly that field and
   nothing nonexistent.
3. real-subprocess atomicity (≥2 child processes) — **tests 1 & 3** (two
   `Popen` children race one O_EXCL claim; SIGKILL crash matrix).
5. pin to a frozen clock — injectable `clock` on `NeedBroker`, `FrozenClock`
   in tests; **tests 2, 5, 6, 8**.
8. verified-fulfilment disambiguation (the VERIFIED one wins; duplicate
   verified is suppressed) — **tests 2 & 3** + broker docstring
   (`late_fulfilment` / `fulfilment_duplicate_suppressed` flags).

## What is NOT proven (honest scope)

- **Scientific quality of the utility function.** `LocalEigPolicy` is a
  transparent, deterministic mechanism; whether local EIG ranking *beats* the
  comparators at matched budget is P05/P08's job with real runs.
- **No SimpleAudit wiring here.** `NeedWorker.execute` is a blind callback by
  design (ticket P04); P07 injects the P02 executor.
- **No multi-need, multi-worker end-to-end swarm run** — that is P07's
  vertical slice.
- **No live/network/LLM behavior** — all deterministic, offline, file-based.
- Budget model is token-estimate based (cost_estimate from the need
  proposer); real token metering of execution is P08's harness concern.
- Concurrency guarantee is per-claim O_EXCL atomicity, not a global
  transaction: two different needs claimed concurrently is fine; two claims
  of the *same* need have exactly one winner (test 1).

## Attack list (for reviewers)

- Lease files are per-need; a process crash mid-`_write_lock` (renew) can
  leave a stale-but-parseable file — bounded by TTL expiry.
- `open_needs` is O(needs × events) (event scan for fulfilled/cancelled);
  fine for competition scale, would need indexing at 10⁴+ needs.
- `_spend_tokens` re-reads needs.jsonl per event — same scaling caveat.
- `choice_changed` compares *full ranking* vectors; a utility tie-break
  flip without any evidence change (same snapshot sha) cannot fire because
  rankings are pure functions of (inputs, snapshot, seed).
- The broker never validates that `execute`'s artifact actually exists —
  `verified` is the executor's attestation (P02's verifier is the real
  verifier at P07).
