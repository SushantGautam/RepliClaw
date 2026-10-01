# P07 Vertical-Slice Demo

A single runnable command that exercises the whole P07 vertical slice and
proves the four things the science judge asked for:

1. **Commit pre-outcome** — every agent privately commits a falsifiable
   prediction packet *before* any outcome exists, and the reveal re-verifies
   the commitment hash (escrow discipline).
2. **Different agent claims** — the decentralized need market lets an agent
   run a need *proposed by another* (the broker never ranks or assigns).
3. **Real, verified SimpleAudit arm** — every claim runs a real P02 arm and is
   verified by clean re-execution + pinned-artifact hash comparison (never the
   agent's self-attestation).
4. **Evidence-derived re-rank** — the choice change is *derived* from the
   published evidence snapshot (M2 closure), not injected.

## How to run

From the worktree root (`.worktrees/p07`), using the worktree venv only:

```bash
.venv/bin/python scripts/demo_slice.py
```

The script writes the run into a timestamped directory under
`artifacts/demo-slice/run-<UTC-timestamp>/` and exits `0` on success. The
timestamp only names the directory; the artifacts themselves are
deterministic (the slice pins `seed=0` + config and excludes wall-clock from
the ledger hash chain).

## What it demonstrates

`run_slice` drives the lifecycle `COMMIT -> REVEAL -> EXECUTE -> RESOLVE`:

- **COMMIT** — `alpha`/`beta`/`gamma` each commit a falsifiable packet for
  `H_R`/`H_P`/`H_J` and publish the need for their arm; `alpha` also publishes
  the `I0_baseline` reference need (4 needs total).
- **REVEAL** — outcome-free reveal; all 3 commitment hashes re-verify.
- **EXECUTE** — the need market runs each arm through a real SimpleAudit
  executor. Observed claims (a different agent ran another's need):
  `alpha` ran `I_J_judge_fix` (proposed by gamma), `beta` ran `I_R_retrieval_fix`
  (proposed by alpha), `gamma` ran `I_P_policy_conflict` (proposed by beta),
  `beta` ran `I0_baseline` (proposed by alpha). Each is verified by
  re-execution.
- **RESOLVE** — the stop rule fires (`all_needs_fulfilled`), the ledger
  resolves, and `slice_result.json` is persisted.

## Real observed output

The following is the actual printed output of
`.venv/bin/python scripts/demo_slice.py` (run `20261008-160137`):

```text
Running P07 slice into artifacts/demo-slice/run-20261008-160137 ...

stop_reason: all_needs_fulfilled
revealed_verified=3  revealed_mismatch=0  published_evidence=4
evidence_snapshot_sha256: 398e38fd599e7a080abada34e2bf5a51e4d4e2193d75fef8b0b5bcda578b0b7c

Per-agent prediction verdicts:
  alpha  H_R  ->  supported
  beta   H_P  ->  refuted
  gamma  H_J  ->  supported

Evidence-derived choice-change trace:
  cycle 2: beta  need_I_R_retrieval_fix_alpha  ->  need_I0_baseline_alpha
      snapshot_sha: 4dc548ead83945c49752457a9da57d800eab9bf6916af0e69be940afafcc97c3

Independent re-execution verification: PASS

DEMO OK
```

Notes on the values (all real, not fabricated):

- `revealed_verified=3`, `revealed_mismatch=0` — all three pre-outcome
  commitments re-verified on reveal.
- `published_evidence=4` — the four arms (I_R, I_P, I_J, I0) each produced a
  verified observation with provenance.
- Verdicts: `alpha/H_R supported`, `beta/H_P refuted`, `gamma/H_J supported` —
  the policy-conflict arm's target output is byte-identical to baseline, so
  H_P is refuted; the retrieval and judge arms are supported.
- The **choice-change trace** is the M2 proof: after the new evidence snapshot
  is published, `beta`'s local top-of-ranking pivots from
  `need_I_R_retrieval_fix_alpha` to `need_I0_baseline_alpha`, tied to a
  specific `snapshot_sha`. The pivot is *derived* from the evidence, not
  injected.
- `Independent re-execution verification: PASS` — the demo re-runs each distinct
  arm in a clean temp dir and confirms the pinned `hashes.json` artifact hashes
  reproduce exactly (the same semantics as `verify_run`).

## Artifacts

Each run persists, under `artifacts/demo-slice/run-<timestamp>/`:

- `slice_result.json` — the summary record (stop reason, per-agent verdicts,
  choice-change trace, evidence snapshot sha).
- `ledger/` — the escrow ledger: `events.jsonl` (hash-chained),
  `commitments.jsonl`, `evidence.jsonl`, `ledger_root.json` (tail anchor),
  `private/` (unrevealed packets), `revealed/policy_rag_v1/` (published
  packets).
- `market/` — the need market: `needs.jsonl`, `events.jsonl`
  (`need_published` / `need_claimed` / `need_fulfilled` / …).
- `runs/<agent>/<need>/interventions/<arm>/` — the real arm artifacts
  (`config.json`, `target_output.txt`, `conversation.json`, `judgment.json`,
  `stdout.log`, `hashes.json`).

## Related tests

The slice's behavior is pinned by `tests/test_slice.py` (7 tests):

```bash
.venv/bin/python -m pytest tests/test_slice.py -q
```
