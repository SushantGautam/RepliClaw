Agent is idle (waiting for messages). agent_id: 9f3c5294-4c8d-41ff-8d2c-1b7dc8bc8ad1, agent_type: RepliClaw Code Judge, status: idle, description: Code judge: p07 integration, elapsed: 1136s, total_turns: 1

[Turn 0]


I have everything I need. All findings reproduced, gates run, no authored code modified.

---

# Adversarial Review — `p07/integration`

## Verdict: **REJECT**

One **BLOCKER** (the broker's expired-lease re-claim can award the same need to two concurrent agents — a direct breach of the core O_EXCL "exactly one winner" guarantee the entire design rests on), plus **3 MAJOR** integrity gaps. The counterfactual and determinism story is genuinely sound.

## Actual gate output (run by me, not quoted)

From worktree root, `.venv/bin/python`:

```
$ .venv/bin/python -m pytest tests/test_counterfactual.py tests/test_escrow.py \
    tests/test_needmarket.py tests/test_execution.py tests/test_need_dispatch_spec.py
27 passed, 8 skipped in 4.58s          # the 8 skips are all test_need_dispatch_spec.py (F06, unimplemented)

$ .venv/bin/python -m ruff check src tests
All checks passed!

$ .venv/bin/python -m mypy src
Success: no issues found in 36 source files
```

**On the "expect 93 passed" note:** at the integration SHA under review (68a27c7) the full suite is **93 passed, 8 skipped** — matching your expectation. My initial full-suite run showed **112 passed** only because P05/comparators (251dead) merged onto the branch *mid-review*, adding `tests/test_comparators.py` (19 tests). 112 − 19 = 93. `git diff --name-only 68a27c7 251dead` confirms P05 touched none of the three reviewed packages, so that drift does not affect this verdict. (Scoped ruff/mypy above are clean for the reviewed files.)

---

## Findings

### 1. BLOCKER — `broker.py` expired-tombstone re-claim is not atomic → double-claim
**File:** `src/repliclaw/needmarket/broker.py:315–339` (claim); tombstone design at `:244–248`; the false guarantee at `:12–13`.

**Evidence.** The docstring asserts:
> `os.O_CREAT | os.O_EXCL` is the atomic cross-process claim primitive — **the OS guarantees exactly one winner.** (broker.py:12–13)

`claim()` only satisfies this on the *first-ever* claim (no lock exists yet, single O_EXCL). On an **expired** lock it does:

```python
# broker.py:333–339  — "Only the process that can unlink the dead lock first may
# recreate it; the second O_EXCL fails and it loses."
try:
    lock.unlink()
except FileNotFoundError:
    return None
try:
    fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
except FileExistsError:
    return None
```

The comment's reasoning is wrong: after `A` unlinks the tombstone and *before* `A` re-opens with O_EXCL, process `B` (which already passed the `FileExistsError` branch on the *same* expired lock) can also `unlink()` (now hitting the file A just… or the original), reach `FileNotFoundError`, or — in the interleaving that actually matters — both read the expired lock, both attempt `unlink()`, one succeeds and one gets `FileNotFoundError` **only if B unlinks after A's recreate**. The ordering that produces two winners is: A unlinks → A opens O_EXCL (wins) → but B had already grabbed the "I'm the winner" control flow and its own `unlink` returns the file A created? No — the real window is tighter and I reproduced it empirically rather than argue it.

**Reproduction (6 concurrent processes racing one expired lock, TTL swept 0.4/0.15/0.05 s):** **7 misfires** — 2 or 3 processes each returned a non-`None` `Lease` and each emitted its own `need_claimed` event. Two agents simultaneously believe they won the same need → double-fulfilment, double budget-spend, violated exactly-once. The `unlink()`→`O_EXCL` pair is two separate syscalls with a window between them; it is **not** a single CAS primitive, so it cannot enforce exclusivity. The `FileNotFoundError → return None` guard only saves the case where the loser's unlink finds *nothing*; it does not cover the case where the loser's O_EXCL finds the file *the winner just created*, because in the failing interleavings both reach O_EXCL against an empty path.

**Required fix:** make re-claim on an expired tombstone a single atomic operation. Cleanest: never delete the lock file — write the *new* lease to a per-generation sidecar (`locks/<need_id>.gen<N+1>`) with O_EXCL, then atomically `os.replace` it over `locks/<need_id>.lock` after verifying the on-disk file still holds the *expired* generation+token you read (a compare-and-swap on the file's contents). Alternatively keep the tombstone file in place and use `link()` of a pre-created per-generation source file onto the lock name: `link(2)` fails if the destination already exists, which is a true atomic existence-check + claim. Either way the winner is decided by **one** kernel atomic call, never by `unlink` + `O_EXCL`. Add a stress test that races N processes on an *expired* lock and asserts exactly one non-`None` result and exactly one `need_claimed` event.

---

### 2. MAJOR — `load_private_packet()` has no phase or ownership gate → cross-agent pre-reveal leak
**File:** `src/repliclaw/escrow/ledger.py:237` (`load_private_packet`).

**Evidence.** The escrow's entire privacy model is that a prediction is *committed* (only a hash projection is public) and the full packet bytes are sealed until `REVEAL`. But `load_private_packet(packet_id)` reads `private/<agent_id>/<packet_id>.json` directly with **no** check that the caller's `PhaseGate` is in `REVEAL+`, and **no** check that the requesting `agent_id` owns the packet. I reproduced: agent B, while the case is still in `COMMIT`, reads agent A's sealed private statement/predicted-outcome bytes. This defeats the counterfactual-honesty guarantee the escrow exists to provide — a peer can learn another agent's unrevealed hypothesis before reveal. Note `commit()`/`reveal()` both go through `self.gate.assert_can(...)`, but this accessor bypasses the gate entirely.

**Required fix:** `load_private_packet(agent_id, packet_id)` must (a) assert the gate is `REVEAL` or later for that `case_id`, and (b) verify the packet's owner == `agent_id` (except a privileged reconciler role if one is intended). Remove the unowned single-arg form from the public `__init__.py` export.

---

### 3. MAJOR — `verify_ledger()` forward-only chain never verifies the trailing event
**File:** `src/repliclaw/escrow/ledger.py:366–401` (verification loop), chain built at `:159–184`.

**Evidence.** Each event stores `prev_event_sha256` = sha256 of the *previous* event's body (excluding `ts` and the `prev` field). `verify_ledger` walks forward and checks `ev.prev_event_sha256 == prev_sha`. The **last** event in the file is therefore only ever the *prev* of a nonexistent event-1 — its own body hash is **never** checked against anything, so its `payload` can be rewritten and the whole ledger still verifies clean. I reproduced: tamper the trailing commitment event's `case_id` → `verify_ledger` returns **0** violations.

**Required fix:** anchor the chain. Options: (a) append a terminal **root/Merkle sentinel** event whose `payload` records the sha256 of the previous event's full body, so the final real event becomes a `prev` to someone; or (b) persist `head_event_sha256` in a separate `ledger_root` file (written/rotated explicitly, out-of-band from the chain) and have `verify_ledger` check the final event's body against it. Document that "verified" now means the *entire* chain including the tail.

---

### 4. MAJOR — escrow `_append_event` has no advisory lock; the "concurrent writers" docstring claim is only half-true, and the test proves only the half it holds
**File:** `src/repliclaw/escrow/ledger.py:15–17` (docstring), `:149–184` (`_last_event`/`_next_seq`/`_append_event`); test at `tests/test_escrow.py:176–235` (Part B).

**Evidence.** The module docstring says:
> Appends use O_APPEND + a single `write()` of a complete line … so **concurrent writers from different processes interleave without corrupting lines.** (ledger.py:15–17)

Line-*integrity* is real (O_APPEND, single sub-PIPE_BUF write). But `_next_seq()`/`_last_event()` do a **read-then-compute-then-append** with **no** lock (grep confirms zero `fcntl`/`flock` anywhere in escrow/needmarket). Under 4 concurrent writer processes (my repro, 20 commits each = 80 events): all 80 lines are well-formed, but **seq is not monotonic** and `verify_ledger` reports **77 violations** (77 hash-chain breaks from duplicate/overwritten `prev` links). So the ledger silently produces an *invalid* hash chain under the exact concurrent-writer condition the docstring advertises as safe — it fails loudly (verifiable) but not safely (the invariant "seq strictly monotonic, a crashed writer must not rewrite history" in the same docstring is violated).

`tests/test_escrow.py:176–235` Part B is the test that should catch this, and it **does not**: after the concurrent run it asserts only `set(ev) >= {seq,ts,...}`, `len(commitments) == 10`, and "no two lines byte-identical" — i.e. it asserts *line* integrity and *count*, never that `seq == range(1,N+1)` or that `verify_ledger(conc_root) == []` after the concurrent phase. So the test passes while the chain is corrupted. This is the "test asserts something the implementation satisfies only by coincidence" gap: the guarantee being tested (append-only line integrity) is weaker than the guarantee being advertised (valid monotonic hash chain under concurrent writers).

**Required fix:** two independent items. (a) Either serialize escrow appends with an advisory lock (`fcntl.flock` on a `.lock` sidecar) around the read-compute-append in `_append_event`, or (b) *downgrade* the docstring claim to "concurrent appends preserve per-line integrity only; a valid hash chain requires a single writer per case" and state the single-writer precondition the way the phase machine already does. (b) Strengthen Part B to assert `seq == list(range(1,len(seqs)+1))` **and** `verify_ledger(conc_root) == []` *after* the concurrent phase — the assertion the current design actually fails.

---

### 5. MINOR — three divergent `canonical_json` definitions
**Files:** `src/repliclaw/canonical.py:17` (`ensure_ascii=False`) vs `src/repliclaw/counterfactual/case.py:39` and `src/repliclaw/escrow/packet.py` (`commitment_hash`/`project_commitment`, default `ensure_ascii=True` via plain `json.dumps(sort_keys=True, separators=(",",":"))`).

**Evidence.** Two different byte-canonicalizations coexist. For the current ASCII-only fixtures they agree, so nothing fails today — but any non-ASCII hypothesis statement or policy text would hash *differently* between `canonical.canonical_json` and the packet/case-local copies, producing silent cross-package hash mismatches (e.g. a commitment hash computed by one path not matching one computed by the other). **Fix:** route all three through a single `repliclaw.canonical.canonical_json` and pin `ensure_ascii=False` (or True) deliberately; add a shared-vector test.

---

### 6. NOTE (not a defect; document it) — integrity primitives are test-only, not wired to production
`execution.py`'s `verify_execution`/`run_python_execution`, `escrow.ledger.verify_ledger`, and `counterfactual.executor.replay/run_case/run_canonical` have **no non-test call sites** in `src/`. Every honesty check is currently exercised only by tests, not by any execution path. This is expected pre-P07 wiring, but it means none of findings #1/#3/#4 would be *caught in production* today — only by an explicit verifier call. Flag for the P07 wiring task.

### 7. NOTE — gate-count drift (explained, not a defect)
Full suite 112 vs expected 93 is the in-flight P05/comparators merge (19 tests). See gate section. Also, an empty `src/repliclaw/slice/` dir (with a transient `orchestrate.py` referencing `NeedWorker`) appeared mid-review from a concurrent P05/P06 builder, then vanished — I scoped this review to the three committed packages, which P05 did not touch.

---

## Suspicious paths I examined and cleared (with reason)

- **Oracle leak (counterfactual):** `experiments/policy_rag/oracle/oracle.json` is sealed; grep over `src/repliclaw/counterfactual/{case,executor,frozen_backend}.py` shows **no** `oracle.json` reference; only `tests/test_counterfactual.py` reads it. `frozen_backend.py` is pure/deterministic and never imports the oracle. Sound.
- **5 arms genuinely distinct:** `interventions.json` — I0 (no override), I_R (retrieval only), I_P (`policy_conflict` only), I_J (`judge_reference_days` only), I_C (retrieval **and** judge, 2-factor). These are distinct factor vectors. **I_P is intentionally a null control** — `frozen_backend` never reads the `policy_conflict` field, so I_P's `target_output`/judgment bytes are byte-identical to I0 (only `config.json` differs). That is the documented no-effect control, and the oracle + test assert exactly that byte-identity. Sound *by design*, but worth noting the arm's "distinction" is in the config, not the output.
- **Byte-identical replay determinism:** `ARM_FILES = (config.json, target_output.txt, conversation.json, stdout.log, judgment.json)` carry **no** wall-clock; `started_at`/`finished_at` live only in the manifest, which `replay()` does not byte-compare. SimpleAudit offline mode emits 0 tokens and no timestamps in the persisted files; `replay()` is a two-pass check (stored files vs pins; re-exec in a clean temp dir vs pins). No set-ordering or dict-ordering leak in the compared bytes (canonical JSON, sorted keys). Sound.
- **No import cycles:** imported `repliclaw.{canonical,counterfactual,escrow,needmarket,execution}` cleanly; dependency graph is a DAG (models/isolation/etc. at the bottom, the three packages only depend downward).
- **No central ranking (needmarket):** `open_needs` (broker.py:252–268) is a pure filter over `needs()` insertion order — no `sort`/`rank`/`heapq`/scoring. `needs()` (broker.py:154) is file order. The broker genuinely enforces lease/dedup/budget only; ranking is delegated to `policy.py` (per-agent). The property holds.

## Read-only compliance
No authored file was modified. All repro scripts were written to `/tmp` and executed read-only against the worktree. I did not approve myself; the verdict above reflects the reproduced defects, foremost the broker double-claim (finding #1), which must be fixed before this integration can be approved.