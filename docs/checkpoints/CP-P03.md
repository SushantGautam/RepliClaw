# CP-P03 — Evidence escrow ledger (2026-10-10)

**Status: P03 implementation complete, gates green, committed — awaiting merge.**

- Branch `p03/evidence-escrow` @ `ba71a4d` (base b5f7bfb).
- Gate @ `.worktrees/p03`: pytest **69 passed, 8 skipped**; ruff clean; mypy clean (20 files).
- 7 red-first tests green (test_escrow.py): byte-level pre-reveal isolation,
  reveal verify/preserve + no post-hoc amendment, tamper → mismatch (ledger
  stays usable), phase violations, append-only events under two concurrent
  processes (line integrity), deterministic content-addressed snapshots,
  verify_ledger catches hash-edit + reorder tampering.
- Design: hash chain excludes wall-clock `ts` (snapshot determinism);
  O_APPEND single-write line atomicity (no lock; seq-global-uniqueness under
  concurrency is NOT promised — documented); no blockchain, no cryptographic
  prevention (detection only) per novelty-gate prohibition.
- Escrow does NOT guarantee: wall-clock ordering, process isolation,
  epistemic independence (documented in handoff-P03).
- Next: P04 need market (`.worktrees/p04`, direct build); then integrate
  P02+P03+P04 once, merged gate, dual judges, CP at merge.
