# RepliClaw — Decisions Log

Material architectural decisions, evidence, and the mandatory reuse matrix.
Evidence paths are from the 2026-10-07 reconnaissance.

## D01 — RepliClaw is a new Python package; ScienceClaw is a vendored dependency
- **Decision:** Implement `repliclaw` as a standalone importable Python package in this repo. Reuse ScienceClaw's `artifacts` + `core/llm_client` + `core/skill_registry` by adding a vendored ScienceClaw checkout under `deps/scienceclaw` (git submodule) and importing it via a thin adapter layer (`repliclaw/scienceclaw_adapter/`). **No fork edits to ScienceClaw this round.**
- **Evidence:**
  - `artifacts/artifact.py`, `artifacts/needs.py`, `artifacts/reactor.py` all import cleanly with stdlib+pydantic only (`import` in 0.09s). `core.skill_registry.get_registry()` discovers 334 skills in 0.58s, no heavy deps.
  - `ArtifactStore` hardcodes `Path(os.path.expanduser("~/.scienceclaw"))` (`artifacts/artifact.py:593`) → cannot be run-local as-is. `rank_needs` also hardcodes `Path.home()/.scienceclaw/artifacts/global_index.jsonl` (`artifacts/pressure.py:199`).
- **Rationale:** Forcing run-local isolation by editing upstream would fork ScienceClaw. Instead, RepliClaw subclasses `ArtifactStore` as `RunLocalArtifactStore` overriding `_base` to a per-run directory. This is an adapter, not a fork. Reversible if upstream adds a base-dir param later.
- **Consequence for isolation:** The global artifact index is per-run (run-local base), which is *stronger* than upstream's shared `~/.scienceclaw` and is what makes the blind/commit/reveal independence testable.

## D02 — Commit/reveal = canonical-JSON SHA256 + persisted run store + event log
- **Decision:** A commitment is `sha256(canonical_json(payload))` where canonical_json = `json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",",":"))`. Commit records are persisted to a per-run, append-only, content-addressed store **before** reveal. Reveal re-hashes the revealed content and must match, else `RevealMismatchError`.
- **Reuse note:** ScienceClaw `Artifact._hash_payload` already does `sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False))`. RepliClaw adds `separators` for byte-stability and wraps it into a first-class `Commitment` type with agent identity + phase + timestamp. No custom crypto (spec forbids it).

## D03 — Pre-reveal isolation = structural (subprocess + sealed context envelope), not prompt-only
- **Decision:** Each investigator runs as a **separate OS subprocess** with a sealed `InvestigationContext` (claim + task + allowed tool list). The orchestrator enforces that an investigator's context contains **no other investigator's** conclusion/plan/result. This is enforced in code (context builder refuses to include sealed material) and independently asserted by a test. Prompt wording is secondary; the runtime gate is primary (per spec M2).
- **Evidence/risk:** A single in-process "agent" with a shared prompt is a fake-independence risk (see D05). Subprocess boundary + context-builder allowlist is the structural control.

## D04 — Plannerless follow-up reuses ScienceClaw `ArtifactReactor`/`NeedItem`/pressure
- **Decision:** Disagreement/weak-evidence emits a `NeedItem` (artifact_type `replication`/`analysis_result`, `branch=True` for competing falsification). RepliClaw drives fulfillment via ScienceClaw's `ArtifactReactor.scan_needs`/`react_to_needs` + `artifacts.pressure.score_need` (deterministic). The closed-team filters `partner_agents` + `investigation_id_filter` (reactor.py:415, 420) scope needs to the run.
- **Evidence:** `react_to_needs` (reactor.py:1178) ranks by `score_need`; `scan_needs` (reactor.py:1110) already skips self-fulfilment and respects `partner_agents`/`investigation_id_filter`. `score_need` = `2*novelty + 1*centrality + 0.5*depth + 0.2*log1p(age_min)` (pressure.py:197).
- **Caveat:** `react_to_needs` maps needs to *registered ScienceClaw skills*; RepliClaw's "analysis" skills must be registered in the SkillRegistry (or a RepliClaw skill shim) so a need for `analysis_result` is producible. Adapter detail, not a blocker.

## D05 — Verdict is evidence-weighted, not majority vote
- **Decision:** `SUPPORTED | REFUTED | INCONCLUSIVE` with a confidence/calibration field. The engine weights executable/independent evidence and *surfaces* unresolved contradictions explicitly; majority vote is one input, not the rule. Insufficient/contradictory evidence → `INCONCLUSIVE` (abstention), never forced certainty.
- **Rationale:** Spec explicitly forbids majority-only verdicts.

## D06 — SimpleAuditStudio is an OTLP integration target, not a core dependency
- **Decision:** RepliClaw emits OpenTelemetry spans (OpenInference semantic conventions where applicable, `repliclaw.*` namespaced attributes otherwise) via an in-memory / optional OTLP exporter. It does **not** import SimpleAuditStudio as a library.
- **Implementation (D14):** the emission lives in `src/repliclaw/observability.py` (OTel *API*-only). It emits a `repliclaw.run` root span (OpenInference `AGENT`) with per-investigator `repliclaw.investigator` spans (blinded loop + emergent follow-ups) and per-phase `repliclaw.phase.*` duration spans; verdict label/confidence and LLM token counts are attached as span attributes. The tracer is resolved lazily per call and the whole layer is a safe no-op when no TracerProvider is set, so the hermetic suite and benchmark never require the SDK.
- **Evidence:** `SimpleAuditStudio/pyproject.toml` depends on `hatchet-sdk==1.41.0`, `postgres` extra; it is a Django app (`manage.py`, `apps.py`, `migrations/`). `audits/agentic/schema_v2.py` referenced in TASK_SPEC does **not** exist in the current checkout. Importing it requires the full Django+Hatchet+Postgres stack → would make RepliClaw core non-hermetic.
- **Rationale:** AC16/AC13 need a CLI/Python `verify` that works in a clean shell. RepliClaw must be standalone; Studio is where a team can ingest the OTLP trace later. Reversible: add a Studio export adapter later.

## D07 — Tests are hermetic (offline deterministic); live-LLM is the demo/benchmark path
- **Decision:** The automated test suite (AC14/AC15) uses a deterministic offline `ProcessInvestigator` (no LLM) so it runs in a clean env. Live-LLM runs (via the verified `simulachat.sushant.pp.ua` OpenAI-compatible endpoint) are the demo (AC16) and benchmark (AC10–AC12) path, producing **real** generated outputs. No metric value is hand-typed (AC18): every number in reports comes from the run store / API `usage` fields.
- **Evidence:** endpoint verified 2026-10-07: `POST /api/v1/chat/completions`, model `default` (base Qwen3.8-27B), correct t-test answer, `usage {prompt:71, completion:66}`, <1s.

## D08 — Dependency minimalism
- **Decision:** New third-party deps limited to `openai` (LLM client), `pydantic`, `networkx` (evidence graph), and `opentelemetry-sdk` (optional, no-op fallback). All present in the current env. No new heavy scientific libs for the core; benchmark fixtures use plain numpy/statistics.
- **Rationale:** AC01 must be reproducible from a clean env; fewer deps = smaller blast radius.

## D09 — A surviving independent conflict is ADJUDICATED only by a decisive, executable, directional follow-up (AC12 recovery)
- **Decision:** When independent evidence conflicts and survives follow-up, the verdict defaults to `INCONCLUSIVE` (conflict surfaced). It is decided as `SUPPORTED`/`REFUTED` ONLY if an independent follow-up produced a *decisive* lean: `executable=True`, `quality != suspicious`, directional relation, and confidence ≥ 0.6; the strongest such follow-up adjudicates. A weak, non-executable, or suspicious follow-up cannot break the tie.
- **Rationale:** The follow-up is the protocol's deadlock-breaker, but it must not become a fake-independence backdoor (it sees revealed material). Requiring an *executable, directional* lean means the tie is broken by a fresh computation on raw data, not opinion — this is what makes misleading-evidence recovery (AC12) sound. Verified: clean→0.98, clean-refuted→0.534, misleading-recovered→0.256 (well-ordered confidence).
- **Rule in code:** `verdict._decisive_adjudicator` + conflict branch of `compute_verdict`; protocol passes `followup_evidence` (evidence whose `notes` contain "fulfills need").

## D10 — LLM investigators need data + explicit per-role methods in the prompt (AC16/AC18)
- **Decision:** `InvestigationContext.to_prompt_block` serializes `claim.data` (shared bundled input, safe pre-reveal); `LLMInvestigator` appends a role-specific quantitative method (analyst: Cohen's d; statistician: two-sample t vs alpha; falsifier: raw-event RR + log-normal 95% CI vs baseline_rr) mirroring the deterministic lenses. `LLMConfig.max_tokens` default raised 1024→4096 and `chat_json` retries once with a "terse JSON" prompt on parse failure.
- **Rationale:** Two live-run failures (kept as evidence in PROGRESS.md): (a) prompt omitted `claim.data` → all roles honestly abstained ("no bundled data"); (b) 1024-token budget truncated verbose model JSON → `ValueError`. Also: `LLMClient` double-wrapping was guarded (`TypeError`), and the protocol hard-fails when ALL investigators fail — a zero-evidence run must not masquerade as INCONCLUSIVE.
- **Verified:** live repl_claw on misleading fixture → REFUTED 0.98, 3 clean calls, 2847 real tokens, 0 errors (2026-10-07).

## D11 — Demo/eval narrative is derived from run outputs, never fixed (AC18)
- **Decision:** `demo.py`'s "Interpretation" section, the Case-2 heading, and the "commitments before reveal" table are all generated from the run's own results (verdict labels, need count + fulfillment via `notes = "fulfills need ..."`, `committed` events before the `revealing` phase). A need is only described as "fulfilled" when actual follow-up evidence exists.
- **Rationale:** Independent code review flagged that a static interpretation paragraph contradicted the live run (which had no conflict → no follow-up) and that `needs.jsonl` is written at emission, not fulfillment. Every reported number in artifacts must trace to computed run data.
- **Verified:** deterministic demo (conflict → 1 fulfilled follow-up → REFUTED 0.256) and LLM demo (3-way agreement → 0 needs → REFUTED 0.98) both render narratives consistent with their own tables.

## D12 — Fixtures must be internally consistent in *direction*, not just magnitude
- **Decision:** In all "treatment increases" fixtures, `mean_treat > mean_ctrl` (was reversed: 5.0/6.0). Affected: clean_supported, misleading_wrong_test, wrong_param_magnitude, data_leakage + `SUPPORTED_DATA` in tests + README example.
- **Rationale:** A live direction-aware model correctly read the reversed means as contradicting "treatment increases" — the *model was right and the fixture was wrong*. Deterministic lenses are magnitude-based (|t|, |d|, raw RR), so the flip is a strict consistency improvement: verified zero regression (60 tests, demo 0.980/0.256, benchmark table byte-identical).
- **Rule:** before shipping a fixture, check claim direction vs every bundled metric's direction; keep `events_*`/`baseline_rr` as the falsifier's raw-data anchor.

## D13 — AC15 strengthened: lint (ruff) + type-check (mypy) are part of the verification gate, not just compileall
- **Decision:** Add `[tool.ruff]` (line-length 120; select E,F,W,I001,B006,B008) and `[tool.mypy]` (`mypy_path = "src:deps/scienceclaw"`, overrides for un-stubbed vendored `artifacts.*`/`networkx`/`openai`/`pydantic`) to `pyproject.toml`; require `ruff check` (0 errors) and `mypy src/repliclaw/` (no issues) in addition to the 61-test suite. `dev` extras now ship `ruff` + `mypy`.
- **Evidence:** First pass found 26 ruff + 10 mypy findings — all genuine (dead vars, unused imports, `F821` from a missing module-level `LLMConfig` import, a real `List[str]`→`List[Dict[str,Any]]` annotation bug on `Verdict.unresolved_conflicts`, a `None`-guard, an int/dict annotation). After fixes: `ruff check` = 0, `mypy` = no issues in 15 files, **62 tests green**. Proven behavior-preserving: benchmark CSV regenerated from current code is **byte-identical (cols 1–14)** to a clean `acaefbb` run — the committed artifact had gone **stale** (`n_needs=4` from M8-era code; current code yields `n_needs=1`), so the canonical `artifacts/benchmark/` was regenerated. The staleness root-caused a real **harness reproducibility bug** (separate fix): `RunStore.append_need` is append-mode, so re-running into a dirty `_work/` inflated `n_needs`; `run_benchmark` now wipes each per-run dir first, guarded by `test_benchmark_is_deterministic_across_reruns`.
- **Rule:** a "static check" that only runs `compileall` is not sufficient evidence for AC15; the gate is compileall + ruff + mypy + full suite, and committed benchmark artifacts must be regenerated from current code before any completion claim.

## D14 — OTel emission is API-only, no-op by default, never imports the SDK
- **Decision:** `src/repliclaw/observability.py` uses only `opentelemetry-api` (never `opentelemetry-sdk` / `openinference-instrumentation`), resolves the tracer **lazily per call** (not at import), and treats a missing/broken provider as a silent no-op. Span shape: `repliclaw.run` (OpenInference `AGENT` root) → `repliclaw.phase.{blind,committed,revealing,evidence,followup,verdict}` (non-current duration markers, explicitly ended) and `repliclaw.investigator` (one per blinded investigator and per emergent follow-up). Verdict label/confidence + `llm.token_count.*` land on the run span. OpenInference attribute names come from `openinference.semconv` when installed, else exact literal fallbacks — same values either way.
- **Evidence:** the installed env has a broken SDK (`opentelemetry-sdk 1.39.1` vs `opentelemetry-api 1.45.0` → `ImportError: cannot import name '_ExtendedAttributes'`), so tests cannot use `InMemorySpanExporter`; `tests/test_observability.py` instead injects an SDK-free tracer via `obs.set_test_tracer()` (the seam also exists so a real deployment can route emission without touching the global provider). 4 tests prove a real run emits the root/investigator/phase tree with correct parenting, an `inv-followup-*` span on the conflict path, and genuine OpenInference constants. Gate: **66 tests**, ruff 0, mypy clean.
- **Rationale:** keeps the hermetic suite (AC15) and benchmark (AC10–AC12) dependency-free; makes D06's "RepliClaw emits OpenTelemetry spans" literally true; a Studio OTLP ingest later only needs `TracerProvider` configuration, no code change.

---

## Reuse Matrix (mandatory gate)

| Capability | Disposition | Notes / Why |
|---|---|---|
| Agent creation/config | `BUILD_REPLICLAW` (thin) | ScienceClaw agents bind to Infinite registration; RepliClaw needs run-scoped, tool-isolated investigator identities. ~100-line `Investigator` profile dataclass. |
| Scientific agent execution | `REUSE_AS_IS` (ScienceClaw `core.llm_client`) | `LLMClient.call` already multi-backend incl. OpenAI-compatible; RepliClaw points it at the verified endpoint. |
| Durable task execution | `BUILD_REPLICLAW` (subprocess) | Subprocess-per-investigator gives the structural isolation D03 requires; Hatchet is Studio-side and too heavy for hermetic core. |
| Artifact storage/provenance | `REUSE_AS_IS` + adapter (ScienceClaw `Artifact`/`ArtifactStore`) | Content-hashed, lineage DAG. Adapter = `RunLocalArtifactStore` overriding hardcoded `~/.scienceclaw` base. |
| Needs / plannerless follow-up | `REUSE_AS_IS` (ScienceClaw `NeedItem`/`ArtifactReactor`/`pressure`) | `react_to_needs` + `score_need` already plannerless + deterministic; closed-team filters scope to run. |
| Commit/reveal (sealed artifact) | `BUILD_REPLICLAW` | ScienceClaw has no commit/reveal or sealed-visibility state. Thin `Commitment` + `RunStore` built on top of `Artifact` hashing. |
| Independence metadata | `BUILD_REPLICLAW` | No generic independence/provenance assertion upstream. Add `IndependenceRecord` + audit of what each investigator could see per phase. |
| Trace transport/instrumentation | `ADOPT_LIBRARY` (OTel + OpenInference) | In-memory exporter + `repliclaw.*` attributes; OTLP export optional. |
| Trajectory normalization | `ADOPT_LIBRARY` (OpenInference conventions) | Emit standard agent/tool spans; reuse, don't fork. |
| Scenario/dataset versioning | `BUILD_REPLICLAW` (fixture manifest) | Controlled benchmark needs known-answer fixtures + seeded-fault metadata; a JSON manifest suffices. |
| Judges/evaluators | `BUILD_REPLICLAW` (evidence-weighted verdict) | Verdict engine is the experiment's core claim; Studio judges are for trace audit, not scientific verdict. |
| Baseline experiment scheduling | `BUILD_REPLICLAW` (strategy runners) | Five coordination regimes on one task interface; no upstream scheduler matches. |
| Progress/live UI | `REUSE_AS_IS` (out of scope) | Non-goal until core ACs; Studio UI is the future surface. |
| Metrics + comparison viz | `BUILD_REPLICLAW` (CSV/JSON/MD summary) | Machine-readable + concise summary; Studio comparison view is a later integration. |
| Cross-team API/CLI | `BUILD_REPLICLAW` (`repliclaw verify`) | Thin CLI + `verify()` Python function producing a provenance-linked report. |
| Distributed need-dispatch (F04→F06) | `BUILD_REPLICLAW` (broker + leases) + `REUSE_AS_IS` (NeedItem/pressure/store) | F04 design (docs/design/NEED_DISPATCH.md, merged 2026-10-08): cross-process atomic claim/lease does not exist upstream (single process-wide lock today; `_mark_need_consumed` is per-agent, no cross-process dedup); `NeedWorker`/subprocess pool + `FulfilmentProvenance` are new. Infinite HTTP broadcaster is NOT reused (vendor-specific). Central in-process `_fulfill_need` dispatch (protocol.py) stays as the in-process baseline for comparison. Must-fix carry-overs recorded in docs/checkpoints/CP-20261008-F04.md. |
