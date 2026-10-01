# P03 handoff — evidence-escrow ledger (G3)

Branch `p03/evidence-escrow`, base b5f7bfb. All new files under the owned
paths only; nothing existing was modified.

## What this delivers (ticket P03.md)

The G3 evidence-escrow mechanism: independent agents **privately commit to
falsifiable prediction packets before any peer's unpublished content or
intervention outcome is visible**; after a phase boundary, reveals are
verified against commitment hashes and published. Mismatched reveals are
integrity events — never silently repaired, never published.

## Files (all new)

| Path | Role |
|------|------|
| `src/repliclaw/escrow/packet.py` | `PredictionPacket` (schema `repliclaw.prediction_packet/v1`), `canonical_bytes` (sort_keys, compact, UTF-8 — reuses `repliclaw.canonical`), `commitment_hash`, `PacketCommitment` public projection + byte-level no-leak assertion in `project_commitment`. |
| `src/repliclaw/escrow/phase.py` | `Phase` (COMMIT→REVEAL→EXECUTE→RESOLVE), `PhaseGate` (per-run, monotonic, one step), `PhaseViolation`, `PHASE_ACTIONS` allow-list. |
| `src/repliclaw/escrow/ledger.py` | `EscrowLedger` (commitments.jsonl / events.jsonl / evidence.jsonl + `private/<agent>/` + `revealed/<case>/`), `EvidenceObservation` (contract §3, requires `run_id` + `provenance.config_sha256`), `verify_ledger` (disk-level tamper detection: line parseability, seq monotonicity, hash chain, commitment↔event cross-check, reveal hash re-verification). |
| `src/repliclaw/escrow/__init__.py` | Public surface. |
| `tests/test_escrow.py` | The 7 red-first tests from the ticket. |

## How each ticket requirement maps

1. **`test_two_agents_independent_precommit`** — both agents commit in
   COMMIT; the union of `commitments.jsonl` + `events.jsonl` bytes (all a
   peer can legitimately see) contains **none** of the four private
   statement fields, checked at byte level. Private full packets live only
   under `private/<agent_id>/`, referenced by no public content.
2. **`test_reveal_verifies_and_preserves`** — verified reveal publishes
   bytes == committed packet's canonical bytes; commitment hash unchanged;
   a post-hoc "amended" packet with the same `packet_id` raises
   `DuplicateCommitment` on re-commit and produces `reveal_mismatch` (never
   published) on reveal.
3. **`test_tampered_reveal_mismatch`** — one-char mutation →
   `reveal_mismatch` event, nothing published, ledger still usable (agent B
   reveals fine after).
4. **`test_phase_violations`** — reveal before boundary, evidence in COMMIT,
   commit after REVEAL, and terminal-RESOLVE advance all raise
   `PhaseViolation`.
5. **`test_events_monotonic_and_append_only`** — Part A: strict seq
   monotonicity + `verify_ledger` clean on a single-writer history. Part B:
   two real concurrent `python` processes append to the same root; every
   line parses, no duplicate/partial lines, all 10 commitments present.
6. **`test_snapshot_deterministic`** — identical action sequence in two
   fresh roots → identical `snapshot_sha256`; an extra
   publish-evidence step → different hash.
7. **`test_verify_ledger_catches_tampering`** — hand-editing a hash field
   on line 1 → chain-break violation; swapping lines 1↔2 → seq violation.

## Key design decisions

- **Hash chain excludes `ts` and the `prev` field itself.** A chain that
  hashes wall-clock timestamps would (a) leak time into the chain and
  (b) make identical action sequences produce different chains — breaking
  snapshot determinism. Excluding `prev` from the hashed content also
  avoids the circularity where forging event i would require knowing
  event i+1.
- **Snapshot is wall-clock-free by construction**: events minus
  `ts`/`phase`, commitments minus `committed_at`, published packet file
  hashes. Content-addressed and deterministic for identical action
  sequences (this is what P04's counterfactual replay consumes).
- **Concurrency model**: appends are single `write()` of a complete line
  under `O_APPEND` — atomic for lines ≤ PIPE_BUF on POSIX, so concurrent
  writers never corrupt lines. We deliberately do **not** promise a
  globally unique `seq` under concurrent writers (that needs a lock or a
  sequencer service); the ticket's bar is line-integrity, and
  `verify_ledger` flags seq anomalies for a given history.
- **Duplicate detection spans commit+reveal**: a packet id that was
  committed or already revealed can never be re-committed, so no
  post-hoc amendment under the same id.

## What this does NOT guarantee (per PRIOR_ART_NOVELTY_GATE "no
cryptographic-guarantees" prohibition)

- **No wall-clock ordering guarantee** — `committed_at` is an audit stamp,
  not an ordering primitive; the *phase gate* orders actions.
- **No process isolation** — a malicious process with filesystem access to
  the ledger root can still rewrite files; `verify_ledger` *detects* that
  (chain/seq/cross-checks), it does not prevent it.
- **No epistemic independence** — escrow prevents reading peer packets
  before reveal via the ledger's public surface; it cannot stop two agents
  from colluding out-of-band or sharing a model.
- **Not a blockchain** — a single-file ledger with a hash chain, by design
  (cheap, inspectable, auditable).

## Commands (run in `.worktrees/p03`)

```
.venv/bin/python -m pytest            # 69 passed, 8 skipped (base skips)
.venv/bin/python -m ruff check src tests   # clean
.venv/bin/python -m mypy src           # clean (20 files)
```

## Attack list for judges

- Try to read a peer's packet before reveal through any public file or API.
- Mutate a private packet on disk after commit, then reveal → mismatch must
  fire (private file is the source of truth the agent reveals from).
- Reorder/tamper `events.jsonl` → `verify_ledger` must report it.
- Race more than two writers and check `verify_ledger` flags the seq gaps.
- Replay a snapshot across machines and confirm `snapshot_sha256` matches.
