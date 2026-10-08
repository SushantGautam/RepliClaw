# Handoff — F04 (W4): decentralized need-dispatch architecture spike

Branch: `w4/F04-need-dispatch` · Worktree: `.worktrees/f04` · Base: `a14fa676`
Type: DESIGN (no product code touched; `src/repliclaw/` unmodified)
Final SHA: branch HEAD of `w4/F04-need-dispatch` (`git rev-parse HEAD` at
integration time; the SHA self-references its own amend, so it is read from
git, not hardcoded here).

## Files touched (this ticket only)
- `docs/design/NEED_DISPATCH.md` (new) — full design, sections 1–8
- `tests/test_need_dispatch_spec.py` (new) — 8 skipped spec tests (`reason="F06 spec"`)
- `docs/fleet/handoff-F04.md` (new) — this file

No other files changed. `git status` clean apart from these three.

## Commands run & exit codes (worktree venv)
- `.venv/bin/python -c "import repliclaw; print(repliclaw.__file__)"` → 0 →
  printed `/Users/sushantgautam/Documents/ScienceClawHackathon/.worktrees/f04/src/repliclaw/__init__.py` (venv points at this worktree ✓)
- `.venv/bin/python -m pytest -q` (baseline, before adding spec file) → 0 → `66 passed`
- `.venv/bin/python -m pytest -q` (after) → 0 → `66 passed, 8 skipped` (the 8 skips are the new F06 specs, per ticket acceptance #2)
- `.venv/bin/ruff check src/repliclaw/ tests/` → 0 → `All checks passed!`
- `.venv/bin/mypy src/repliclaw/` → 0 → `Success: no issues found`

## Key findings from the upstream code (all verified by reading)

1. **Today's dispatch is provably central.**
   - `protocol.py:302` — the need is appended (`:300`) and then consumed in the
     same call stack by `_fulfill_need` (`protocol.py:383`); nobody else ever
     sees it.
   - `protocol.py:401-404` — central role selection:
     `FALSIFIER if kind==FALSIFICATION else STATISTICIAN`.
   - `protocol.py:405-423` — orchestrator fabricates the worker identity,
     builds its context, and calls `inv.run(ctx)` in-process.
   - Isolation is context-level only (`isolation.py:92-93` gate, `:131-149`
     peer-material denial while blind, `:153-171` sealed-read refusal);
     `runstore.py:44` has a single `threading.Lock` — a process-level
     boundary does not exist (G2).
2. **The decentralized substrate already exists but is underused.**
   - `needs.py:42-76` `NeedItem` (schema incl. `branch`/`max_variants`),
     `needs.py:83-127` `NeedsSignalBroadcaster` is HTTP→Infinite (wrong
     topology for hermetic runs — deliberately NOT reused for the wire).
   - `reactor.py:1110-1176` `scan_needs` (open-need discovery with partner /
     investigation filters), `reactor.py:1178-1445` `react_to_needs`
     (rank by `score_need`, execute, save child with `_fulfilled_need` /
     `_need_index` tags at `:1400-1408`, then mark consumed).
   - **Critical gap:** `_mark_need_consumed` (`reactor.py:1089-1093`) is
     PER-AGENT (`~/.scienceclaw/artifacts/<agent>/consumed_needs.txt`,
     `:1055-1060`). Two reactors can therefore both fulfil the same need —
     there is **no atomic claim, no lease, no cross-process dedup** upstream.
     That is exactly what F06 must add (it is the only genuinely new
     coordination state).
   - `reactor.py:397` hardcodes `~/.scienceclaw` and `:399` binds an
     in-process skill executor — two more reasons not to bolt a
     multi-process loop directly onto `ArtifactReactor` without extension.
   - `pressure.py:57-115` `iter_open_needs`, `:145-193` `score_need`
     (deterministic `2·novelty + 1·centrality + 0.5·depth + 0.2·log1p(age)`,
     formula at `:190`), `:197-240` `rank_needs` — all pure, all reusable
     with a run-local index path.
   - `artifact.py:477-507` `Artifact` (content hash, lineage, `needs` field
     `:506`), `:605-627` `save` + `:629-660` `_append_global_index` — the
     index entry carries `fulfilled_need_parent_id`/`fulfilled_need_index`
     (`:643-659`), which `_coverage_count` (`pressure.py:127-133`) counts:
     publishing a fulfilment artifact automatically collapses the need's
     novelty score and satisfies `scan_needs` dedup. Reuse, no new store.
3. **What the adapter already bridges** (`scienceclaw_adapter.py`): `NeedItem`
   (`:30`), `NeedRef`/`score_need` (`:31`), run-local store
   (`:34-48`), finding→artifact (`:54`), needs→NeedItem (`:78-91`),
   `pressure_score` (`:94-110`). It imports **no reactor** — the decentralized
   half of the vendored stack is currently dead weight in the protocol. F06
   turns it on.

## Design decisions + rationale (short form; full text in the design doc)

- **D-A: Reuse the substrate for data + priority + storage; build only the
  coordination layer.** NeedItem schema, `iter_open_needs`/`score_need`/
  `rank_needs`, `Artifact`/`ArtifactStore` (via existing `RunLocalArtifactStore`),
  `ContextEnforcer`/`PhaseGate`, `Commitment`/`RunStore` — all REUSE. New:
  `NeedBroker` (file-backed atomic lease log) + `NeedWorker` (subprocess) +
  `FulfilmentProvenance`. Rationale: everything new is forced by the
  per-agent consumed-mark gap (#2) and the missing process boundary (G2).
- **D-B: The broker is an append-only JSONL event log under an O_EXCL
  lockfile, with state derived on read (no rewriting).** Crash-safe by
  construction: a dead writer leaves a stale lease/lock, both time-bounded
  (`lease_ttl` default 120 s; lock stale at 3×ttl). Key =
  `"<parent_artifact_id>:<need_index>"` — the exact key upstream already uses
  for dedup and coverage, so broker, reactor, and pressure all agree.
- **D-C: At-least-once work, exactly-once effects (verified-fulfilment dedup,
  duplicates tagged `duplicate_suppressed`, never deleted).** Stated openly
  (design §4.3/§5.3) — we do not claim distributed-lock-grade exactly-once
  for work, and we do not claim Byzantine tolerance.
- **D-D: Eligibility is self-declared and claim-based; the published need has
  NO role/agent field** — this is the direct negation of G1's "chooses a role"
  (`protocol.py:401-404` is deleted from the decentralized path).
- **D-E: Verification stays central (single orchestrator verifies reveals and
  ingests evidence).** Decentralize *execution*, keep the audit crisp.
- **D-F: Isolation = existing context seal + process boundary; threat model is
  independence/fault isolation, NOT adversarial sabotage on one host**
  (design §5.3 — worktree/venv ≠ sandbox, stated honestly).
- **D-G: Baseline strategies untouched.** Decentralization is an additive
  mode; `STRATEGY_RUNNERS` signatures and the benchmark `rows` schema are
  unchanged (fleet rule 10).

## F06 contract (exact symbols, module `src/repliclaw/need_dispatch.py`)
- `WorkerCapability` (frozen dataclass: `agent_id`, `method_family`, `model`,
  `producible_types`)
- `Lease` (frozen dataclass: `need_key`, `worker_id`, `claim_token`,
  `lease_deadline`, `expired(now)`)
- `NeedBroker` — `publish_need`, `open_needs`, `claim` (atomic; None on
  loss), `renew`, `release`, `mark_fulfilled`, `fulfilled_artifact`
  (dedup rule), `claim_history`
- `NeedWorker` — `eligible`, `scan_and_rank`, `cycle`, `run`
- `FulfilmentProvenance` (frozen dataclass: `need_key`, `claim_token`,
  `worker_agent_id`, `method_family`, `model`, `producer_process_pid`,
  `lease_deadline`, `fulfilled_at`, `parent_artifact_id`, `need_index`,
  `reveal_verified`; `to_dict()`)
- `start_worker_pool` (subprocess-per-worker, M8), `publish_followup_need`
  (orchestrator side, replaces `protocol.py:300` region), `consume_fulfilments`
  (orchestrator side, replaces `protocol.py:302-307` region)
- Fulfilment payload keeps upstream tags `_fulfilled_need` / `_need_index` /
  `_fulfillment_variant` (`reactor.py:1400-1413`) + adds
  `fulfilment_provenance` (upstream readers keep working).

Spec tests pinning all of this: `tests/test_need_dispatch_spec.py`
(SPEC-1 double-fulfil race, SPEC-1b reverse order, SPEC-2 crash/lease/re-claim,
SPEC-2b stateless restart, SPEC-3 eligibility-not-preassigned, SPEC-4
pre-reveal isolation, SPEC-5 orphaned fulfilment, SPEC-6 deterministic
ranking) — all `@pytest.mark.skip(reason="F06 spec")`.

## Reuse-vs-build one-liners (design §3)
M1 NeedItem schema — REUSE · M2 Infinite HTTP broadcaster — DO NOT REUSE
(hermetic) · M3 pressure/discovery — REUSE · M4 store/index/lineage — REUSE
(adapter) · M5 eligibility shape — REUSE pattern (not the reactor) · M6
reactor-as-engine — BUILD thin `NeedWorker` (alt: EXTEND upstream reactor
`base_dir`+`claim_hook`) · M7 atomic claim/lease — BUILD (the only new
coordination state) · M8 subprocess pool — BUILD (thin) · M9/M10 isolation +
commit/reveal — REUSE · M11 provenance block — BUILD (G6 evidence) ·
M12/M13 verdict + otel — REUSE.

## Open questions for the orchestrator (design §8)
1. **Q1** Demo worker count: recommend 3 (2 eligible + 1 decoy-ineligible) so
   eligibility-driven dispatch is *visible in the demo trace*, not just tests.
2. **Q2** In-process fallback for baselines: design default = baselines
   unchanged, decentralization opt-in mode. Needs sign-off (touching all five
   runners would muddy the baseline comparison).
3. **Q3** Multi-machine: out of scope (single host, stated limit). The
   Infinite HTTP path is the only existing cross-machine primitive; a
   networked broker would be a M7-swap only (everything is keyed on
   `need_key`).
4. **Q4** Lease TTL / follow-up timeout constants for the LLM gate (F08) —
   need measured p95 fulfilment time; defaults 120 s / 600 s until then.
5. **Q5** Where `FulfilmentProvenance` surfaces in `repliclaw verify` output
   (and whether SimpleAuditStudio's schema gains a matching field — owned
   upstream, track separately).

## Unresolved / integration notes
- Design is decision-complete; the two BUILD rows (M7 broker, M11 provenance)
  carry the `BUILD_REPLICLAW` justifications for `DECISIONS.md` — orchestrator
  to fold the matrix (design §3) into the reuse matrix when merging F06.
- If F06 prefers the EXTEND_UPSTREAM alternative for M6, the upstream change
  is `ArtifactReactor.__init__` (accept `base_dir` + optional claim hook) —
  keep it minimal; the vendored copy lives at `deps/scienceclaw/artifacts/
  reactor.py:388-434`.
- No LLM calls were made; all work offline (fleet rule 7). No pushes, no
  merges (fleet rule 6).
