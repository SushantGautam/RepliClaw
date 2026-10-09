# F04 — Decentralized need-dispatch architecture (design)

Origin: dev-branch ticket F04 (archived) · Branch: `w4/F04-need-dispatch`
Status: **design complete, decision-complete** · Implementation: **F06**
All `file:line` citations below were read and verified in this worktree at
base `a14fa676`. Upstream = `deps/scienceclaw/`, RepliClaw = `src/repliclaw/`.

Competition context: `docs/COMPETITION_STRATEGY.md:27` (G1 — "Not sufficiently
decentralized: `protocol.py::_fulfill_need` chooses a role and invokes a
follow-up directly; the NeedItem/Reactor adapter does not establish a truly
independent claim/dispatch loop") and `:32` (G6 — "different agent IDs are not
proof of independent methods, evidence, models, tools, or errors").
"Decentralized agency" is scored at 20%.

---

## 1. Current-state analysis — why today's dispatch is central

### 1.1 The central-dispatch code path (verified)

The follow-up loop in `RepliClawProtocol._run_phases`:

1. **Need creation** — `src/repliclaw/protocol.py:281` (`if conflicts or
   agreement["unresolved"] or agreement["label"] == "conflict":`), a single
   `FollowUpNeed` is constructed at `protocol.py:282-293` with a role-agnostic
   `need_id`; priority is scored at `protocol.py:294-298` via
   `sc.pressure_score` (the upstream `score_need`), and the need is appended to
   the run-local store at `protocol.py:300` (`self.store.append_need(need)`,
   `src/repliclaw/runstore.py:266`).
2. **Immediate synchronous fulfilment** — `protocol.py:302`:
   `followup_ev = self._fulfill_need(claim, need, evidence, revealed, errors)`.
   No other component ever observes the need. It is consumed in the same
   process, in the same thread, in the same call stack, microseconds after it
   is appended. There is no pool, no other process, no claim.
3. **Central role selection** — inside `_fulfill_need`
   (`protocol.py:383`), the orchestrator *chooses* the fulfilment identity:
   - `protocol.py:401-404`: `followup_role = InvestigatorRole.FALSIFIER if
     need.kind == NeedKind.FALSIFICATION else InvestigatorRole.STATISTICIAN` —
     a deterministic central mapping of need-kind → role.
   - `protocol.py:405-410`: the orchestrator fabricates the worker identity
     `InvestigatorConfig(agent_id=f"inv-followup-{need.need_id[-6:]}",
     role=followup_role, ...)`.
   - `protocol.py:411-419`: the orchestrator builds the worker's context via
     `self.enforcer.build_context(...)`.
   - `protocol.py:422-423`: `inv = self.followup_factory(cfg); finding =
     inv.run(ctx)` — direct in-process invocation of the chosen role.
4. **Central commit/reveal** — `protocol.py:431-446` (orchestrator computes
   `commit_payload`, constructs `Commitment`, calls `self.store.commit(c)` and
   `self.store.verify_reveal(...)`), then `protocol.py:447-458` central
   evidence construction and `store.append_evidence`.

### 1.2 Why agent-ID diversity ≠ independence (G6)

- All investigators — including the follow-up — are constructed by one
  process via one factory (`protocol.py:111`:
  `self.followup_factory = followup_factory or investigator_factory`), run
  sequentially in the same Python process (`protocol.py:189-190` for the blind
  phase; `protocol.py:422-423` for follow-up), share the same `RunStore`,
  event log, and memory. Nothing about `agent_id`/`role` creates a boundary.
- The follow-up is *structurally pre-assigned*: the role is a pure function of
  `need.kind` chosen by the orchestrator (`protocol.py:401-404`), never
  *claimed* by an independent agent that decided it could help.
- Isolation today is **context-level, single-process**:
  `src/repliclaw/isolation.py:92-93` (`PhaseGate.is_blind` = phases
  `blind|committed`), `isolation.py:131-149` (`peer_materials` returns `{}`
  while blind), `isolation.py:153-171` (`read_sealed_commitment` raises
  `IsolationViolation` on pre-reveal content reads, `isolation.py:25`). The
  enforcement point is one in-process API. A process-level boundary (separate
  address space, no shared memory, separate worktree) does not exist — this is
  gap G2 (`docs/COMPETITION_STRATEGY.md:28`), which F04's target design moves
  from "context gating only" to "context gating + process boundary" while
  staying honest about what that buys (Section 5).
- The ScienceClaw bridge (`src/repliclaw/scienceclaw_adapter.py`) proves
  *reuse is wired* but is not a dispatch loop: it imports `NeedItem`
  (`:30`), `NeedRef`/`score_need` (`:31`), provides run-local storage
  (`RunLocalArtifactStore`, `:34`), `artifact_from_finding` (`:54`),
  `needs_to_need_items` (`:78`), `pressure_score` (`:94`). Notably it imports
  **no reactor, no claim mechanism** — the decentralized half of the vendored
  stack is currently unused by the protocol.

**Conclusion.** Today's "decentralized" story is: N investigators with
different IDs/roles in one process, plus a central dispatcher that
hand-picks who fulfils the need. The vendored substrate for a genuinely
decentralized claim/fulfil loop already exists in `deps/scienceclaw` (Section
1.3); F06 must make RepliClaw's follow-up phase run through it.

### 1.3 Upstream building blocks (verified, with line numbers)

**`deps/scienceclaw/artifacts/needs.py`**
- `NeedItem` (pydantic) at `needs.py:42-76`: `artifact_type` (literal union of
  concrete types incl. `"analysis_result"`, `needs.py:19`), `query` (min 5),
  `rationale` (min 20), `branch: bool` (competing fulfillments),
  `max_variants` (1..6), `preferred_skills`, `param_variants`.
- `NeedsSignal` at `needs.py:79-80` (≤2 needs).
- `NeedsSignalBroadcaster` at `needs.py:83-127`: best-effort **HTTP**
  broadcaster to the Infinite platform (`needs.py:101-127`). **Reuse verdict:
  NO for the wire** — it is network-bound (`InfiniteClient`), and it is the
  wrong topology for a hermetic run (Section 3). We reuse the *data model*
  (`NeedItem`) and the *pattern* (needs embedded in artifact metadata), not
  the HTTP client.

**`deps/scienceclaw/artifacts/reactor.py`**
- `ArtifactReactor.__init__` (`reactor.py:388-434`): takes `agent_name`,
  `agent_profile` (dict), `artifact_store`. Knobs read from profile:
  `preferred_tools` (`:404-409`), `partner_agents` closed team
  (`:413-414`), `investigation_id_filter` (`:419-423`),
  `needs_fulfillment_budget` (`:426-427`), `needs_max_variants_default`
  (`:429-430`). Hardcodes `self._base = Path.home() / ".scienceclaw" /
  "artifacts"` (`:397`) and per-agent `consumed.txt` (`:398`).
- `register_peer` (`reactor.py:583-587`): registers a *sibling reactor*
  (in-process) to receive mutation-cascade outputs. **In-process only** — no
  cross-process semantics (Section 5).
- `scan_needs` (`reactor.py:1110-1176`): scans `global_index.jsonl` for peer
  needs this agent can fulfil. Filters: non-empty needs; `producer_agent !=
  self.agent_name` ("no self-fulfilment", `:1144-1146`); partner-team filter
  (`:1157-1159`); investigation filter (`:1160-1161`); skip keys in
  `consumed_needs` (`:1163-1171`); producibility via
  `_artifact_type_to_skills` (`:1172-1176`).
- `react_to_needs` (`reactor.py:1178-1445`): rank candidates by
  `score_need` (`:1239-1253`), pick skills producing the need's
  `artifact_type` (`:1284-1292`), execute variants (`:1379-1413`), save child
  artifact with `payload["_fulfilled_need"]` + `payload["_need_index"]`
  (`:1400-1408`), then `store.create_and_save` (`:1415-1420`) and
  `self._mark_need_consumed(artifact_id, need_index, variant_id=...)`
  (`:1421`). `strict_need_variants` can raise if a variant fails
  (`:1432-1436`).
- **Consumed-need dedup is per-agent**: `_mark_need_consumed`
  (`reactor.py:1089-1093`) appends `artifact_id:need_index:variant_id` to
  `~/.scienceclaw/artifacts/<agent>/consumed_needs.txt`
  (`reactor.py:1055-1060`). There is **no shared/atomic claim record**: two
  different reactors (different `agent_name` → different
  `consumed_needs.txt`) independently scan the same index and both conclude
  the need is unfulfilled. `scan_needs` therefore answers "have *I* fulfilled
  this before", not "is anyone doing this now". **This is the exact gap F06
  closes with a shared broker + lease.**
- Cross-machine variant exists but is out of scope: `_fetch_remote_needs`
  (`reactor.py:461-504`), `_merge_remote_needs` (`reactor.py:506-555`),
  `_patch_remote_need_fulfilled` (`reactor.py:557-581`) — all HTTP via
  Infinite.
- Execution is **in-process skill invocation**: `react_to_needs` calls
  `self._executor.execute_skill(...)` (`reactor.py:1393-1399`), where
  `_executor = get_executor()` (`:399`). No subprocess boundary.

**`deps/scienceclaw/artifacts/pressure.py`**
- `NeedRef` frozen dataclass (`pressure.py:46-55`): `(parent_artifact_id,
  need_index, producer_agent, investigation_id, artifact_type, query,
  rationale, parent_timestamp)`.
- `iter_open_needs` (`pressure.py:57-115`): reads `global_index.jsonl`
  (default `~/.scienceclaw/artifacts/global_index.jsonl`, `:67-68`), with
  `exclude_agent` (`:83-84`), `investigation_id` (`:85-86`),
  `partner_agents` (`:87-88`) filters — an *open-needs iterator* that
  F04's worker loop reuses directly with a run-local index path.
- `score_need` (`pressure.py:145-193`): deterministic
  `2.0* novelty + 1.0* centrality + 0.5* depth + 0.2* log1p(age_min)`
  (`:190`). Novelty falls as coverage grows — `_coverage_count`
  (`:118-142`) counts existing `fulfilled_need_parent_id`/
  `fulfilled_need_index` index entries. Already used by RepliClaw via
  `sc.pressure_score` (`scienceclaw_adapter.py:94-110`) and by the reactor
  (`reactor.py:1239-1253`).
- `rank_needs` (`pressure.py:197-240`): deterministic sort, precomputed
  centrality.

**`deps/scienceclaw/artifacts/artifact.py`**
- `Artifact` (`artifact.py:477-507`): immutable, `content_hash` = sha256 of
  canonical JSON (`:509-512`), `parent_artifact_ids` lineage DAG
  (`:504`), `needs: List[dict]` carried on the artifact
  (`:506`) — i.e. the native *broadcast* channel is "needs embedded in an
  indexed artifact", not a separate topic.
- `ArtifactStore.save` (`artifact.py:605-627`): append to per-agent
  `store.jsonl` + `_append_global_index` (`:629-660`). Index entries carry
  only discovery fields — including the needs list and, for fulfillments,
  `fulfilled_need_parent_id` / `fulfilled_need_index` /
  `fulfillment_variant` (`:643-659`).
- `_append_global_index` shows the **coverage signal** the pressure scorer
  consumes: a fulfilment artifact's index entry *is* the record that
  `_coverage_count` counts (`pressure.py:127-133`).
- `ArtifactStore` hardcodes `~/.scienceclaw` (`artifact.py:592-599`);
  RepliClaw's `RunLocalArtifactStore` (`scienceclaw_adapter.py:34-48`) bypasses
  `__init__` and re-roots both the per-agent store and the global index under
  the run dir — the same trick F06's broker must apply to everything.

---

## 2. Target architecture — the decentralized need-dispatch loop

### 2.1 Design principles

1. **Reuse the substrate, don't reinvent it.** `NeedItem` (schema),
   `NeedRef`/`iter_open_needs`/`score_need`/`rank_needs` (priority),
   `Artifact`/`ArtifactStore` (broadcast + lineage + coverage), and the
   `ArtifactReactor` *shape* (scan → eligibility → fulfil → mark consumed)
   all stay. F06 adds only the missing coordination layer.
2. **The broker is the single shared state**; workers are stateless
   executors that only *read* shared state and *write* their own outputs.
   No worker ever mutates another worker's data.
3. **Eligibility is claimed, not assigned.** No need carries a role or an
   agent. A worker fulfils a need iff it self-declares eligibility
   (its capability set covers the need's `artifact_type` + method family).
   The orchestrator never picks.
4. **Process = isolation unit.** Each worker is a separate OS process
   (subprocess), with its own `RunLocalArtifactStore`-scoped view and its own
   `consumed_needs`-equivalent. Blind-phase commitments stay sealed by the
   existing `ContextEnforcer`/`PhaseGate`; the process boundary adds a
   second, physical layer.
5. **At-least-one, effectively-once fulfilment.** Crash semantics: a need can
   be re-fulfilled after a crash (at-least-once), but the consumer (reactor /
   evidence graph) dedupes by `(parent, need_index)` and keeps the first
   *verified* fulfilment, so the verdict sees one (at-least-one →
   effectively-once after dedup). Exactly-once for *effects* (evidence rows)
   is the goal; exactly-once for *work* is impossible without distributed
   locks and is explicitly not promised.

### 2.2 The loop (per need)

```
                        ┌─────────────────────────────────────────────┐
                        │  Orchestrator process (existing protocol)   │
                        │  1. detect conflict/insufficient evidence   │
                        │  2. emit FollowUpNeed → NeedItem            │
                        │  3. publish to shared index via NeedBroker  │
                        └──────────────────┬──────────────────────────┘
                                           │ append (atomic, run-local JSONL)
                                           ▼
                        ┌─────────────────────────────────────────────┐
                        │  Shared need index  (run-local file)        │
                        │  global_index.jsonl + needs_broker.jsonl    │
                        │  (lease, ttl, claim_token per open need)    │
                        └──────────────────┬──────────────────────────┘
                                           │ each worker polls
              ┌────────────────────────────┼────────────────────────────┐
              ▼                            ▼                            ▼
   ┌────────────────────┐      ┌────────────────────┐      ┌────────────────────┐
   │ Worker process A   │      │ Worker process B   │      │ Worker process C   │
   │ NeedWorker.run()   │      │ NeedWorker.run()   │      │ NeedWorker.run()   │
   │ 1. iter_open_needs │      │ 1. iter_open_needs │      │ 1. iter_open_needs │
   │ 2. score_need rank │      │ 2. score_need rank │      │ 2. score_need rank │
   │ 3. eligibility()   │      │ 3. eligibility()   │      │ 3. eligibility()   │
   │ 4. broker.claim()  │      │ 4. broker.claim()  │      │ 4. broker.claim()  │
   │ 5. execute (blind) │      │    → lease lost    │      │    → lease won     │
   │ 6. commit+reveal   │      │    (skip)          │      │ 5. execute         │
   │ 7. fulfilment arti │      └────────────────────┘      │ 6. commit+reveal   │
   └─────────┬──────────┘                                  │ 7. publish        │
             │ publish fulfilment Artifact                  └─────────┬──────────┘
             ▼                                                        ▼
   ┌──────────────────────────────────────────────────────────────────────────┐
   │ Shared index receives fulfilment entry (fulfilled_need_parent_id, ...)   │
   └──────────────────────────────────┬───────────────────────────────────────┘
                                      ▼
                        ┌─────────────────────────────────────────────┐
                        │ Orchestrator: reactor/consumer pass          │
                        │  - scan_needs → now empty for this need      │
                        │  - _coverage_count ≥ 1 → pressure novelty    │
                        │    collapses; need marked fulfilled          │
                        │  - first verified fulfilment becomes         │
                        │    Evidence (notes="fulfills need …")        │
                        │  - verdict re-scored                         │
                        └─────────────────────────────────────────────┘
```

Step-by-step contract:

1. **Emit** — orchestrator (inside the existing follow-up phase,
   `protocol.py:281-300` region) converts the `FollowUpNeed` to a native
   `NeedItem` (schema already proven by `sc.needs_to_need_items`,
   `scienceclaw_adapter.py:78-91`) and publishes it. The orchestrator's role
   in the decentralization claim ends here: it *announces* the need, it does
   not *dispatch* it.
2. **Index** — the need lives in the shared index (run-local
   `global_index.jsonl`, exactly where `iter_open_needs` and
   `ArtifactReactor.scan_needs` already look: `pressure.py:67-68`,
   `reactor.py:1125-1133`). Nothing new for readers.
3. **Discover** — each worker process calls `iter_open_needs`
   (`pressure.py:57-115`) with the run-local index path,
   `exclude_agent=<self>`, `investigation_id=<claim>`.
4. **Prioritize** — `score_need`/`rank_needs` (`pressure.py:145-193`,
   `:197-240`) deterministically order the queue. Same score for all workers
   (pure function of index contents) → no tie-break arbitration needed to
   *rank*, only to *claim*.
5. **Eligibility** — the worker checks, from its *own* capability declaration
   (roles/methods/tools it can run), whether it can produce the need's
   `artifact_type`. This mirrors the upstream producibility check
   (`reactor.py:1095-1108`, `_artifact_type_to_skills`) but is *self*-declared
   and **not** a pre-assignment: any eligible worker may proceed.
6. **Claim** — `NeedBroker.claim(need_key, worker_id, lease_ttl)` performs an
   atomic, compare-and-swap on the shared `needs_broker.jsonl`: a need is
   claimable iff it has no live lease; claiming writes
   `{need_key, worker_id, claim_token, lease_deadline}`. File-level atomicity
   via `os.O_CREAT|os.O_EXCL` claim-locks + single-writer append (Section 4).
   Losers see the existing live lease and skip.
7. **Execute** — the winning worker runs the investigation **blind**
   (same `ContextEnforcer.build_context` path, `isolation.py:107-129`), in its
   own process, writing to its own per-agent store. It does not read other
   workers' outputs until reveal.
8. **Commit + reveal** — the worker commits its finding
   (`commit_payload`, `models.py:24-40`), seals it, then reveals and
   self-verifies — or, more decentralizes, publishes the commitment to the
   shared index and the orchestrator verifies reveal against the commitment
   hash (`RunStore.verify_reveal`, `runstore.py:180`). F06 default: worker
   publishes commitment record; orchestrator verifies (single verifier keeps
   the tamper-evidence honest; verification is central, fulfilment is not).
9. **Publish fulfilment** — the worker saves an `Artifact` with
   `needs=[]` and payload tags `_fulfilled_need`/`_need_index`
   (upstream convention, `reactor.py:1400-1408`) plus a
   `FulfilmentProvenance` block (Section 6.3) into the run-local store.
   `ArtifactStore.save` (`artifact.py:605-627`) appends the index entry with
   `fulfilled_need_parent_id`/`fulfilled_need_index`
   (`artifact.py:643-659`) — the exact fields `_coverage_count`
   (`pressure.py:127-133`) and `scan_needs` consume, so the *existing*
   dedup/pressure machinery now sees the fulfilment automatically.
10. **Consume** — the orchestrator (or a designated consumer worker) runs a
    `scan_needs` pass (`reactor.py:1110-1176`) to confirm the need is no
    longer open for any eligible peer, marks the `FollowUpNeed`
    `status="fulfilled"` (`models.py:207`), ingests the fulfilment artifact as
    `Evidence` (replacing the old inline `evidence.append(followup_ev)` at
    `protocol.py:303-305`), re-runs `detect_conflicts`, and proceeds to
    verdict. If two fulfilment artifacts exist (crash + re-claim race,
    Section 4), the consumer keeps the one with the *earliest verified
    reveal* and records the other as `duplicate_suppressed` (never silently
    dropped — auditability).

### 2.3 What changes in `protocol.py` (F06 scope, described not implemented)

- The body of `_fulfill_need` (`protocol.py:383-458`) becomes a thin
  *orchestrator-side consumer*: publish-need → wait-for-fulfilment (with
  timeout + optional single in-process fallback for the `single_agent`
  strategy) → verify → ingest. The central role-mapping at
  `protocol.py:401-404` is deleted from the decentralization path; the
  `single_agent` baseline may keep a direct call (it is a *baseline*, not the
  decentralized regime — that's the point of the comparison).
- `RepliClawProtocol.__init__` gains optional `need_broker` / `worker_pool`
  parameters (additive, defaulting to None ⇒ current behaviour for all five
  existing strategies, so `STRATEGY_RUNNERS` signatures and the benchmark
  `rows` schema are untouched).
- A new `decentralized` mode (or strategy flag on `repl_claw_blind_commit_
  reveal`) starts the worker pool; the five baseline strategies keep
  working unchanged.

---

## 3. Reuse-vs-build matrix

Verdicts below use the convention: `REUSE_AS_IS` / `REUSE_ADAPTER` /
`EXTEND_UPSTREAM` (we own SimpleAudit + may extend ScienceClaw) /
`BUILD_REPLICLAW` (with justification).

| # | Mechanism | Verdict | Evidence / justification |
|---|-----------|---------|--------------------------|
| M1 | Need schema + "needs embedded in artifact" broadcast | **REUSE_AS_IS** — `NeedItem` (`needs.py:42-76`) published as `Artifact.needs` (`artifact.py:506`); adapter already bridges (`scienceclaw_adapter.py:78-91`) | Native schema carries exactly what a replication/falsification need needs (`artifact_type`, `query`, `rationale`, `branch`, `max_variants`). No new need type. |
| M2 | Cross-run / cross-machine need wire | **DO NOT REUSE** — `NeedsSignalBroadcaster` is HTTP→Infinite (`needs.py:83-127`) | A hermetic run must not depend on a remote platform; local shared index (M4) is the broadcast medium. Decision recorded so F06 doesn't "fix" the broadcaster. |
| M3 | Need priority / open-need discovery | **REUSE_AS_IS** — `iter_open_needs` (`pressure.py:57-115`), `score_need` (`:145-193`), `rank_needs` (`:197-240`), already wrapped (`scienceclaw_adapter.py:94-110`) | Deterministic, LLM-free, stable under the same index → all workers rank identically. |
| M4 | Shared index / storage / lineage / content-hash / coverage | **REUSE_ADAPTER** — `ArtifactStore` + `Artifact` (`artifact.py:477-660`) via `RunLocalArtifactStore` (`scienceclaw_adapter.py:34-48`) | Run-local re-rooting is proven; coverage fields (`artifact.py:643-659`) are what pressure/dedup consume. No new store format. |
| M5 | Eligibility / producibility check *shape* | **REUSE_AS_IS (pattern)** — `_artifact_type_to_skills` + `scan_needs` filters (`reactor.py:1095-1108`, `:1110-1176`) | We copy the *shape* (type-produceability + partner + investigation filters) but implement it against the worker's self-declared capability, because `scan_needs` is bound to a reactor's skill registry (`reactor.py:397` hardcoded base, `:399` executor) — see M6. |
| M6 | `ArtifactReactor` as the fulfilment engine | **EXTEND_UPSTREAM (optional) / else BUILD a thin `NeedWorker`** | The reactor is right in spirit (scan → rank → fulfil → mark consumed, `reactor.py:1178-1445`) but three things block direct reuse for a *decentralized multi-process* loop: (a) `~/.scienceclaw` base hardcoded at `reactor.py:397` (would leak between runs and require a monkeypatched instance); (b) in-process skill executor `get_executor()` (`:399`) — no process boundary, no crash isolation; (c) **no atomic claim** — `_mark_need_consumed` is per-agent (`reactor.py:1089-1093`) so two reactors can both fulfil (M7). Cleanest path: **BUILD_REPLICLAW** a thin `NeedWorker` that reuses `iter_open_needs`/`score_need`/`Artifact` and borrows the reactor's fulfilment *sequence*, while adding the broker claim. *Alternative (if F06 judges it cheaper):* `EXTEND_UPSTREAM` `ArtifactReactor.__init__` to accept a `base_dir` + `claim_hook` (we own the upstream; the constructor already takes a store, so a `base_dir` param is a small, broadly useful generalisation). **Decision: default = BUILD_REPLICLAW thin worker** (small, hermetic, zero upstream churn under time pressure); the upstream extension is the documented alternative if review prefers. |
| M7 | Atomic claim / lease / re-claim / crash recovery | **BUILD_REPLICLAW** — no upstream primitive exists | `BUILD_REPLICLAW` justification: nothing in `deps/scienceclaw` (or SimpleAudit) offers a file-based, cross-process, atomic claim with TTL. `ArtifactReactor`'s consumed-mark is per-agent and post-hoc (`reactor.py:1089-1093`, file `consumed_needs.txt`); `global_index.jsonl` has no claim state; the Infinite HTTP path (`reactor.py:461-581`) is the wrong topology for hermetic runs. SimpleAudit's Hatchet is a durable *audit* executor (Studio-side) — wrong boundary for a hermetic scientific core (durable task execution = BUILD_REPLICLAW subprocess). A ~150-line file-lease broker is the smallest architecture that satisfies Section 4. |
| M8 | Worker process isolation | **BUILD_REPLICLAW (thin)** — subprocess per worker | Subprocess-per-investigator; Hatchet too heavy for a hermetic core. `subprocess.Popen` + JSON-over-stdout/exit-code; no framework. |
| M9 | Blind-phase visibility gating | **REUSE_AS_IS** — `ContextEnforcer`/`PhaseGate` (`isolation.py:73-195`) | Already code-enforced with a read log (`isolation.py:107-129` builds context, `:131-149` denies peer material while blind, `:153-171` raises on sealed reads). Workers inherit it by construction: a worker's context is built by the *same* enforcer, so the seal is as strong as today plus a process boundary. |
| M10 | Commit/reveal tamper-evidence | **REUSE_AS_IS** — `Commitment` + `RunStore.commit/verify_reveal` (`models.py:101-117`, `runstore.py:121-230`) | Content-hash sealing already exists and is tested (`tests/test_commit_reveal.py`). The decentralization loop reuses the same commitment record; only *who* produces it changes. |
| M11 | Fulfilment provenance (who/what/when/how for audit) | **BUILD_REPLICLAW (dataclass)** | `BUILD_REPLICLAW` justification: upstream `Artifact.payload["_fulfilled_need"]` (`reactor.py:1400-1408`) records *what* need was fulfilled but not *which independent process, lease token, model, or capability set* produced it — exactly the G6 evidence the judges need ("not proof of independent methods, evidence, models, tools"). A small `FulfilmentProvenance` pydantic block appended to the payload is additive and feeds `verify()`/Studio. |
| M12 | Verdict / evidence ingestion | **REUSE_AS_IS** — `detect_conflicts`/`compute_verdict` (`protocol.py:348-378`, `verdict.py`) | No change; the decentralization loop feeds the *same* evidence list. |
| M13 | OTel trace of the dispatch loop | **REUSE_AS_IS (pattern)** — `obs.run_span`/`investigator_span` (`protocol.py:141-161`, `:187-188`) | Broker/claim/execute/verify steps get the same span style; Studio ingest unchanged. |

**One-liners** (for the handoff): M1 reuse `NeedItem`; M2 skip the HTTP
broadcaster (hermetic); M3 reuse pressure; M4 reuse adapter store; M5 reuse the
eligibility *pattern* not the reactor; M6 **build** thin `NeedWorker`
(alternative: extend upstream reactor base/claim hook); M7 **build** file-lease
broker (the only genuinely new coordination state); M8 **build** subprocess
pool; M9–M10 reuse isolation + commit/reveal; M11 **build** provenance
block; M12–M13 reuse verdict + otel patterns.

---

## 4. Worker ownership, leases & retries (the only new state)

### 4.1 Data structures

**`needs_broker.jsonl`** (run-local, one JSON line per *event*; the broker is
an append-only event log — never rewritten, so concurrent appends are safe on
POSIX with O_APPEND writes < PIPE_BUF… in practice we serialize with a
lockfile, below):

```jsonc
// event kinds
{"t":"need_opened","need_key":"<artifact_id>:<need_index>","published_at":"..."}
{"t":"claimed","need_key":"...","worker_id":"w-2","claim_token":"c-<uuid>","lease_deadline":"..."}
{"t":"lease_renewed","need_key":"...","claim_token":"c-<uuid>","lease_deadline":"..."}
{"t":"lease_released","need_key":"...","claim_token":"c-<uuid>","reason":"fulfilled|failed|abandoned"}
{"t":"need_fulfilled","need_key":"...","artifact_id":"...","claim_token":"c-<uuid>","worker_id":"w-2"}
```

Derived state (recomputed by scanning the log on each read — cheap, index is
small): a need is **claimable** iff no `claimed` event for it has an
unexpired `lease_deadline` and no later `need_fulfilled` event exists. The
holding worker is the worker of the latest non-superseded `claimed` event.

`need_key` = `f"{parent_artifact_id}:{need_index}"` — the exact key upstream
already uses for dedup (`reactor.py:1089-1093` consumed-needs format) and for
`_coverage_count` (`pressure.py:127-133`), so broker state, reactor dedup, and
pressure coverage all agree on one key.

### 4.2 Atomic claim (cross-process)

Single-mechanism, no daemons, no DB:

1. **Exclusive lock** on `<run_dir>/.need_broker.lock` via `open(..., O_CREAT|O_EXCL)`
   in a retry loop (lockfile + mtime staleness detection: a lock older than
   `3×lease_ttl` is considered dead and unlinked — a crashed holder cannot
   wedge the pool forever).
2. Under the lock: re-read the log tail (other writers may have appended
   since the worker's scan), recompute claimability, and if still claimable,
   **append one `claimed` event** with `claim_token = uuid4()` and
   `lease_deadline = now + lease_ttl` (default `lease_ttl = 120 s`,
   configurable).
3. Release lock, execute.

Two workers racing the same need both pass step 1; the OS guarantees exactly
one wins the O_EXCL. The loser either sees the live lease and skips, or
(appending later) sees a `claim_token` it does not own. Because *all* state
writes go through the lock, the log is a total order — no split-brain.

### 4.3 Lease lifecycle, expiry, re-claim

- **Renewal** — long investigations append `lease_renewed` (same token) every
  `lease_ttl/2`. A worker that cannot renew (died) simply stops.
- **Expiry** — any worker (or the orchestrator's timeout path) treats a need
  with `now > lease_deadline` as **claimable again**. The stale `claimed`
  event is *not* rewritten; expiry is derived from timestamps. The stale
  holder's partial outputs (if any) are invisible until it published a
  fulfilment artifact — and a fulfilment without a valid, non-expired lease at
  publish time is treated as **orphaned** (Section 4.5).
- **Re-claim** — after expiry, another eligible worker claims with a *new*
  `claim_token`. The broker logs record the full chain
  (claimed w-2 → expired → claimed w-5) — the audit trail is the log itself.
- **Double-fulfil guard** — `need_fulfilled` events are deduped at *ingest*:
  the consumer accepts the first `need_fulfilled` with a verified reveal and
  the earliest `lease_deadline`-valid claim; later ones are recorded as
  `duplicate_suppressed` (still in the log, still visible to `verify()`) and
  their artifacts stay in the store for inspection. This is *at-least-once
  work, effectively-once effects*: we never delete, we never claim a
  distributed lock on the write path.

### 4.4 Idempotency & crash/restart matrix

| Crash point | State after restart | Recovery |
|---|---|---|
| Worker dies after `claimed`, before execution | need has a live lease | lease expires (≤ `lease_ttl`); another worker (or the same one restarted, which *rescans* — stateless) re-claims with a new token; no partial artifact exists (execution writes nothing until publish) |
| Worker dies after execution, before publish | same as above; plus scratch files in worker's own dir | scratch dir is worker-private and GC'd on next scan; need re-claimed; work redone (accepted cost — see 4.6) |
| Worker dies between `ArtifactStore.save` and `need_fulfilled` append | fulfilment artifact in store + index, need still claimable | another worker may re-claim and re-fulfil → consumer dedup (4.3) keeps the first verified; orphaned fulfilment from the dead holder is tagged `duplicate_suppressed`. Alternatively the restarting worker finds its own artifact (by content hash + need_key) and only appends the missing `need_fulfilled` event — **idempotent republish**, allowed because the event log tolerates duplicates and the consumer dedupes |
| Worker dies after `need_fulfilled` | need fulfilled | nothing to recover; orchestrator timeout resolves on the next `scan_needs` (need no longer open) |
| Orchestrator dies mid-run | all broker state in files | protocol is resumable from `RunStore` (existing); workers are disposable — restart pool, rescan, leases enforce safety |
| Lockfile holder dies holding the lock | `.need_broker.lock` stale | mtime staleness rule (4.2) unlinks after `3×lease_ttl`; no permanent wedge |

**Exactly-once fulfilment** is therefore: *work* may repeat (at-least-once),
*effects* (evidence rows, verdict inputs) are exactly-once via verified-
fulfilment dedup, *audit* is total (every claim/fulfilment event persisted).
This is stated honestly in the design so external reviewers are not surprised.

### 4.5 Orphaned fulfilments (publish without a live lease)

If a worker's lease expired but it still ran to completion and published
(the TTL was too short, or the clock jumped), the consumer must decide.
Rule: a `need_fulfilled` event whose `claim_token` no longer matches the
broker's live holder at append time is still **accepted** if its reveal
verifies, but flagged `late_fulfilment` in the provenance; the *claim
winner* among accepted fulfilments (earliest valid append under lock order)
supersedes. This keeps liveness (we never lose a good, verified result
because of a clock/TTL misconfiguration) at the cost of a possible
duplicate, which the dedup already absorbs. **No silent data loss, no
unverified data accepted.**

### 4.6 Cost & budget

- Redo-on-expiry is bounded by `lease_ttl` × (workers per need) and in
  practice is near-zero (worker dies ⇒ rare in the benchmark regime).
- The orchestrator's follow-up phase gains a **bounded wait**
  (`followup_timeout_s`, default `5×lease_ttl`) with a deterministic
  fallback: if no fulfilment arrives, the need is marked
  `status="dropped"` (`models.py:207`) and the verdict proceeds on existing
  evidence — matching today's `need_unfulfilled` branch
  (`protocol.py:306-307`). No strategy can hang.

---

## 5. Isolation model — what it is, and honest limits

### 5.1 What "separate worker process" concretely means here

- One OS process per worker (`subprocess.Popen`, M8), distinct
  `agent_id`, distinct per-agent store under the run dir (upstream layout
  `artifact.py:592-599`, run-local re-root `scienceclaw_adapter.py:34-48`),
  distinct `consumed_needs`-equivalent file (upstream
  `reactor.py:1055-1060`).
- **No shared memory.** Cross-worker communication is file-mediated only:
  the shared index (read), the broker log (read + locked append), and
  parent/child pipe/exit-code for lifecycle. A worker's Python heap cannot be
  observed or mutated by a peer — `register_peer`-style in-process cascade
  (`reactor.py:583-587`) is *not* used for the decentralization path.
- **Blind-phase seal (two layers).** Layer 1 (existing, logical): the worker's
  context comes from `ContextEnforcer.build_context` (`isolation.py:107-129`)
  and `to_prompt_block(revealed=False)` (`investigators.py:218`) — peer
  conclusions are not in the payload at all. Layer 2 (new, physical): before
  reveal, the *file* that would contain a peer's revealed conclusion is not
  written by anyone (reveal is a single orchestrator step at
  `protocol.py:246-261`), and even post-reveal each worker process only
  re-reads what its phase gate allows. Sealed commitments are readable pre-
  reveal as metadata-only via `read_sealed_commitment`
  (`isolation.py:153-185`); content reads raise
  `IsolationViolation` (`isolation.py:160-171`).
- **Independent method** (G6): each worker declares a *method family*
  (e.g. effect-size re-derivation vs bootstrap vs raw-event falsifier) and a
  `model` string (`InvestigatorConfig.model`, `models.py:87`); the
  `FulfilmentProvenance` block (M11) records both, so independence is
  *evidence in the artifact*, not an ID.

### 5.2 What it protects

| Threat | Mitigated? | By |
|---|---|---|
| Worker A reads worker B's *unrevealed* conclusion | **Yes** | no such file exists pre-reveal (5.1) + context enforcer |
| Worker A reads worker B's *scratch*/in-progress work | **Yes** | per-agent dirs; other agent's dir is not in A's context; (best-effort at OS level — see limits) |
| Worker A crashes and wedges the pool | **Yes** | lease expiry + stale-lock rule (4.2, 4.3) |
| Double fulfilment corrupting the verdict | **Yes** | verified-fulfilment dedup (4.3) |
| Tampered reveal | **Yes** | content-hash commit/reveal (`models.py:24-40`, `runstore.py:180`) |
| Orchestrator bias (choosing the winner) | **Yes** | eligibility + atomic claim; orchestrator never selects (2.2 step 5-6) |

### 5.3 Honest limits (stated in the public release, not hidden)

1. **Worktree/venv ≠ sandbox.** A "separate process" on the same machine
   shares the filesystem, OS user, and the local venv. A *malicious* worker
   that deliberately reads `<run_dir>/artifacts/<peer>/store.jsonl` (it can
   see the path) is not stopped by this design — only by OS permissions.
   Our threat model is *independence and fault isolation* (independent
   methods, crash-proofness, no coordination leak), **not** adversarial
   sabotage. We say so.
2. **Single host.** The broker is file-based; multi-machine would need the
   existing Infinite HTTP path or a networked lock — explicitly out of scope
   for the live experiment window (Section 8).
3. **At-least-once work.** A crash between execution and publish redoes work
   (4.4). Effects are exactly-once; work is not.
4. **Clocks.** Lease expiry trusts the host wall clock; an NTP jump can
   expire a live lease (handled by 4.5, with a `late_fulfilment` flag).
5. **Verification is still central.** One orchestrator verifies reveals and
   ingests evidence. That is deliberate: decentralizing *execution* is the
   claim; a single tamper-evident verifier keeps the audit crisp. We do not
   claim a Byzantine-fault-tolerant consensus.
6. **Model independence is declared, not certified.** Provenance records the
   `model` string; whether two workers truly had different error
   distributions is a property of the benchmark (F05/G5), not of this
   mechanism.

---

## 6. F06 implementation contract (exact new symbols)

F06 implements *exactly* this surface in `src/repliclaw/` (new module
`need_dispatch.py` + additive changes only; no existing signature changes):

### 6.1 `src/repliclaw/need_dispatch.py`

```python
@dataclass(frozen=True)
class WorkerCapability:
    """Self-declared eligibility — the ONLY thing a worker publishes about
    itself before claiming. No need is ever pre-assigned to it."""
    agent_id: str                 # unique per worker process
    method_family: str            # e.g. "effect-size", "bootstrap", "falsifier-raw"
    model: str                    # model identifier string (G6 evidence)
    producible_types: frozenset[str]   # artifact_types this worker can produce

@dataclass(frozen=True)
class Lease:
    need_key: str                 # f"{parent_artifact_id}:{need_index}" (upstream key)
    worker_id: str
    claim_token: str              # uuid4 hex
    lease_deadline: str           # ISO-8601 UTC
    def expired(self, now: str) -> bool: ...

class NeedBroker:
    """File-backed, cross-process need coordination. Append-only log."""
    def __init__(self, run_dir: str | Path, lease_ttl_s: float = 120.0): ...
    def publish_need(self, parent_artifact_id: str, need_index: int,
                     need: dict) -> str: ...           # returns need_key
    def open_needs(self, exclude_agent: str,
                   investigation_id: str) -> list[tuple[dict, int, NeedRef]]: ...
        # thin wrapper over pressure.iter_open_needs(run-local index)
    def claim(self, need_key: str, worker_id: str) -> Optional[Lease]:
        """Atomic. Returns the lease if this worker won; None if a live lease
        exists (another worker owns it) or the need is already fulfilled."""
    def renew(self, lease: Lease) -> bool: ...
    def release(self, lease: Lease, reason: str) -> None: ...
    def mark_fulfilled(self, need_key: str, artifact_id: str,
                       lease: Lease) -> None: ...
    def fulfilled_artifact(self, need_key: str) -> Optional[str]:
        """First verified fulfilment id, or None. Dedup rule in §4.3."""
    def claim_history(self, need_key: str) -> list[dict]: ...  # audit

class NeedWorker:
    """One worker process's loop. Reuses iter_open_needs/score_need/Artifact;
    borrows the reactor's fulfilment sequence; adds the broker claim."""
    def __init__(self, capability: WorkerCapability, broker: NeedBroker,
                 investigator_factory, store: RunLocalArtifactStore,
                 enforcer: ContextEnforcer, tick_s: float = 0.05,
                 max_cycles: int = 50): ...
    def eligible(self, need: dict) -> bool:
        """need["artifact_type"] in capability.producible_types AND
        (need preferred_methods ⊇ method_family) — self-check, not
        pre-assignment (mirrors reactor.py:1095-1108 producibility)."""
    def scan_and_rank(self) -> list[tuple[NeedRef, float]]:
        """pressure.iter_open_needs + score_need/rank_needs (deterministic)."""
    def cycle(self) -> Optional[Artifact]:
        """One poll: scan → rank → first eligible → broker.claim → execute
        (blind) → commit/reveal → publish fulfilment Artifact with
        FulfilmentProvenance → broker.mark_fulfilled. Returns the artifact or
        None (nothing eligible / lost the claim)."""
    def run(self) -> list[Artifact]:
        """Poll until no open eligible needs remain (or max_cycles)."""

@dataclass(frozen=True)
class FulfilmentProvenance:
    """M11 — G6 evidence attached to every fulfilment artifact payload."""
    need_key: str
    claim_token: str
    worker_agent_id: str
    method_family: str
    model: str
    producer_process_pid: int
    lease_deadline: str
    fulfilled_at: str
    parent_artifact_id: str
    need_index: int
    reveal_verified: bool
    def to_dict(self) -> dict: ...

def start_worker_pool(run_dir, workers: list[WorkerCapability],
                      worker_factory) -> list[subprocess.Popen]: ...
    """M8 — one subprocess per capability; JSON-over-stdout protocol;
    each child rebuilds its own broker/enforcer from run_dir (stateless)."""

def publish_followup_need(store, run_local_store, claim, need: FollowUpNeed,
                          broker: NeedBroker) -> str: ...
    """Orchestrator side: FollowUpNeed → NeedItem → Artifact(needs=[...]) →
    broker.publish_need. Returns need_key. (Replaces protocol.py:300 region.)"""

def consume_fulfilments(broker, run_store, run_local_store, claim,
                        timeout_s: float) -> list[Evidence]:
    """Orchestrator side: wait for verified fulfilments (bounded), build
    Evidence rows (notes='fulfills need …'), mark FollowUpNeed fulfilled /
    dropped. (Replaces protocol.py:302-307 region.)"""
```

### 6.2 Data flow (F06 wiring)

1. `publish_followup_need` (orchestrator) → shared `global_index.jsonl`
   (via `RunLocalArtifactStore.save`) + `needs_broker.jsonl` (`need_opened`).
2. `NeedWorker.cycle` in each child → `open_needs` → `eligible` → `claim`
   (O_EXCL lock, §4.2) → execute blind → `Commitment` → `Artifact` with
   `_fulfilled_need` + `FulfilmentProvenance` → `mark_fulfilled`.
3. `consume_fulfilments` (orchestrator) → `fulfilled_artifact` → verify reveal
   → `Evidence` → `FollowUpNeed.status="fulfilled"` → verdict.
4. `claim_history` → event log (`runstore.event("need_claim", ...)`) →
   Studio/`verify()` provenance report.

### 6.3 Payload tags (compat with upstream readers)

The fulfilment payload keeps upstream keys `_fulfilled_need` /
`_need_index` / `_fulfillment_variant` (`reactor.py:1400-1413`) **and** adds
`"fulfilment_provenance": provenance.to_dict()`, so a stock
`ArtifactReactor.scan_needs` / `_coverage_count` still treats it as a
fulfilment (coverage counts it, `pressure.py:127-133`) while RepliClaw's
`verify()` can extract the G6 block.

---

## 7. Adversarial test SPEC (implemented in F06)

The suite `tests/test_need_dispatch_spec.py` pins these scenarios as
`pytest.mark.skip(reason="F06 spec")` — **red by design, green-skipped
today**. Each is written to fail if F06 implements the mechanism *centrally*
(i.e. the tests are the decentralization oracle).

### SPEC-1 — Two eligible workers → exactly one fulfils (no double)

- **Setup:** run-local index with one open need (`analysis_result`, query
  recompute-from-raw); two `NeedBroker`-sharing `NeedWorker`s
  (different `capability.agent_id`, both `producible_types` include
  `analysis_result`) run interleaved cycles *in the same test* (deterministic
  proxy for two processes: shared broker file, two worker objects, one
  thread each).
- **Action:** let both race the same `need_key` (worker A `claim`, then
  worker B `claim` in the same millisecond window — and the reverse order in
  a parametrized case).
- **Assertions:**
  - exactly one `Lease` is non-None per race; the loser gets `None`;
  - broker log contains exactly one `claimed` with a live deadline at the
    moment both attempted;
  - after both finish: exactly one fulfilment artifact exists for the
    `need_key`, `fulfilled_artifact()` returns it, the need is no longer in
    `open_needs` for any peer, and `FollowUpNeed.status == "fulfilled"`.
- **Why it proves decentralization:** a central dispatcher would fulfil
  without a `claim` event at all — the log assertions would fail.

### SPEC-2 — Crash after claim → lease expiry → re-fulfil by another

- **Setup:** worker A claims `need_key`, then "dies" (test kills A's cycle
  mid-execution; no publish). Broker log shows a live lease owned by A.
- **Action:** advance fake clock past `lease_deadline`; worker B (fresh,
  stateless — rebuilt from `run_dir`) scans and claims.
- **Assertions:**
  - while lease live: B's `claim` → `None` (no steal);
  - after expiry: B's `claim` → valid new `claim_token` (≠ A's);
  - broker log shows `claimed(A) … claimed(B)` chain;
  - B fulfils; exactly one accepted fulfilment; `claim_history` length ≥ 2;
  - restart-A scenario: A rebuilt from disk finds its *unpublished* partial
    state = none (scratch is private), and would only re-claim if the lease
    had expired — no double fulfilment in any interleaving (parametrize 4
    interleavings).
- **Why it proves decentralization:** crash recovery must come from the
  shared lease state, not from the orchestrator noticing a dead thread.

### SPEC-3 — Eligibility-driven, NOT role-preassigned

- **Setup:** a falsification-kind need (today's central code would force
  `FALSIFIER`, `protocol.py:401-404`). Workers: (i) a falsifier-capable
  worker, (ii) a statistician-capable worker that *also* produces
  `analysis_result` with `method_family="bootstrap"`, (iii) an analyst
  worker that produces a *different* `artifact_type` (not eligible).
- **Action:** run the pool.
- **Assertions:**
  - the fulfilment's `FulfilmentProvenance.method_family` is one of
    {"falsifier-raw","bootstrap"} — i.e. produced by whichever worker won
    the claim, not by a need-kind→role map; parametrize so that in at least
    one run the **statistician** (not the falsifier) fulfils the falsification
    need;
  - no code path receives the need with a role attached: assert the published
    `NeedItem` has no `role`/`agent_id` field and `NeedWorker.eligible`
    depends only on `capability`;
  - the non-eligible worker never appears in `claim_history` for the need.
- **Why it proves decentralization:** directly negates G1's "chooses a role".

### SPEC-4 — Pre-reveal: no worker sees another worker's conclusion

- **Setup:** two workers both hold in-flight blind findings (fixtures with
  distinguishable conclusions "support…" vs "refut…"). Their commitments are
  in the store, phase `committed`, **not revealed**.
- **Action:** each worker (in its own "process" object with its own store
  view) attempts, through the *legitimate API only*, to read the other's
  state: `enforcer.peer_materials`, `read_sealed_commitment(revealed=True)`,
  and a raw scan of the other's per-agent store dir.
- **Assertions:**
  - `peer_materials` → `{}` (gate is blind/committed);
  - `read_sealed_commitment(revealed=True)` → `IsolationViolation`
    (`isolation.py:160-171`);
  - the worker's `InvestigationContext.to_prompt_block(revealed=False)`
    contains neither peer's conclusion string (substring check on both
    fixtures);
  - the raw-scan probe is *permitted by the OS* (honest limit, §5.3.1) but
    the test asserts it is **not part of the worker's code path** — i.e.
    `NeedWorker.cycle` never references a foreign store path (source-level
    assertion via the worker's context build log, `isolation.py:119-127`
    `context_built` events show `includes_peer_materials=False`).
- **Why it proves decentralization:** the seal must hold *between processes*,
  not just inside one Python object.

### SPEC-5 — Crash before publish (orphaned fulfilment) → no double effect

- **Setup:** worker A publishes a fulfilment `Artifact` to the store but dies
  before `mark_fulfilled` (simulate: save artifact, then kill). Lease still
  live, then expires. Worker B re-claims and re-fulfils (different payload).
- **Assertions:**
  - two fulfilment artifacts exist in the store (honest: no deletion);
  - `fulfilled_artifact()` returns exactly one; the other is
    `duplicate_suppressed` in `claim_history`/events;
  - `consume_fulfilments` yields exactly **one** `Evidence` row;
  - verdict computed on the single row; rerunning the consumer is idempotent
    (second call → same single Evidence, no append).
- **Why it proves decentralization:** the at-least-once/exactly-once-effects
  contract (§4.3) is the property that makes crash decentralization safe.

### SPEC-6 (bonus, cheap) — Deterministic priority: all workers rank identically

- Same index snapshot → `NeedWorker.scan_and_rank()` in two workers returns
  identical `(need_key, score)` order (pure `score_need`,
  `pressure.py:145-193`), so no worker can be "starved" or "favored" by the
  scheduler; the only nondeterminism is the claim race itself.

These six scenarios are the acceptance tests for F06's decentralization claim
and map 1:1 to the scoring: SPEC-1/2/5 = fault-tolerant decentralized
fulfilment, SPEC-3 = "not pre-assigned" (G1), SPEC-4 = independent
processes (G2/G6), SPEC-6 = fairness/determinism.

---

## 8. Risks & open questions

**Risks (mitigations in design)**
1. *File-lock contention under many workers* — mitigated by O_EXCL lockfile
   with bounded retry + backoff; lock is held only for an append
   (microseconds). **Residual:** if the judge demands >10 concurrent
   workers on slow FS, revisit with `fcntl.flock` (advisory, still
   cross-process) — a 1-line swap inside `NeedBroker._with_lock`.
2. *TTL too short for a long LLM fulfilment* → orphan churn. Mitigation:
   renewal every `ttl/2`; default `ttl=120 s` covers the deterministic
   fixtures easily; LLM runs (F08 gate) set `ttl` from observed p95.
3. *Clock jump* (NTP) expiring live leases → `late_fulfilment` path (§4.5)
   absorbs it; monitor via `claim_history` audit.
4. *Scope creep into strategy semantics* — the five `STRATEGY_RUNNERS`
   signatures and benchmark `rows` schema must not change;
   decentralization is an additive mode. F06 must not touch
   `strategies.py` public signatures.
5. *Upstream drift* — if F06 takes the EXTEND_UPSTREAM alternative (M6), the
   change to `ArtifactReactor.__init__` (base_dir + claim hook) must be
   minimal and tested against upstream behavior; default choice avoids this
   risk entirely.

**Open questions (genuinely undecidable at design time)**
1. **Q1 — Worker count in the demo.** Design supports N≥1; the
   "decentralized agency" result likely wants N≥2 *eligible* workers visible
   in the trace. Recommendation: 3 workers (2 eligible + 1 decoy-ineligible)
   so SPEC-3's shape is *visible in the demo*, not only in tests. Orchestrator
   to confirm for the demo script.
2. **Q2 — In-process fallback.** Should `single_agent`/`fixed_dag` keep the
   old direct `_fulfill_need` path (recommended: yes — they are baselines and
   changing them muddies the comparison), or should *all* strategies route
   through the broker with 1 worker (purer story, but touches every runner)?
   Default in this design: **baselines unchanged, decentralized mode
   opt-in**. Needs orchestrator sign-off.
3. **Q3 — Multi-machine.** The Infinite HTTP path (`reactor.py:461-581`) is
   the only existing cross-machine primitive. For the live experiment window:
   **no** (single host, stated limit §5.3.2). If the evaluation rubric rewards
   cross-machine, that is a post-experiment item; design already keys
   everything on `need_key` so a networked broker would be a M7 swap only.
4. **Q4 — Lease TTL / timeout constants** for the LLM gate (F08): needs a
   measured p95 fulfilment time to set `lease_ttl_s` and `followup_timeout_s`
   sensibly. Until then: `120 s` / `600 s`.
5. **Q5 — Provenance in the `verify()` report.** Where in the
   `repliclaw verify` output should `FulfilmentProvenance` surface (top-level
   `provenance` block vs per-evidence)? F06 to propose during implementation;
   Studio schema (SimpleAuditStudio) may need a matching field — that's an
   owned-upstream change, track separately.
</file_text>
