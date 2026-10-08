# RepliClaw

A decentralized **blind commit / reveal replication & falsification collective**
built on [ScienceClaw](./deps/scienceclaw) primitives. Other ScienceClaw teams
submit their central claim (plus optional bundled data/artifact references) and
receive a **provenance-linked verification report** — without adopting this
codebase.

## Scientific hypothesis

> Independent, method-diverse investigators who **cannot see each other's
> conclusions until after committing** to them (blind commit → reveal →
> adjudicate) detect misleading scientific artifacts that coordination
> baselines accept — and recover autonomously (without a hard-coded workflow)
> when their evidence conflicts.

The threat model: an artifact (or a single agent) presents a *plausible but
wrong* primary analysis (e.g. a wrong statistical test, a leaky estimate, a
cherry-picked subgroup). Single-agent and fixed-DAG pipelines trust the
artifact; vote/debate baselines can abstain but cannot repair. RepliClaw's
answer is structural: (1) method-diverse lenses that read the *raw* data, not
just the published figure; (2) commitment seals that make post-hoc position
shifting detectable; (3) **plannerless follow-up needs** — the protocol itself
emits a falsification need when revealed evidence conflicts, and an
independent follow-up investigator adjudicates it.

## Why this is not a fixed DAG

- A fixed DAG (analyst → statistician → synthesizer) has a **static** shape
  decided before any evidence exists. RepliClaw's graph is **evidence-
  conditional**: the follow-up node exists only if and only if revealed
  evidence conflicts, its *kind* (falsification vs replication) is chosen by
  the nature of the conflict, and its question is generated from the actual
  disagreement — the workflow is not hard-coded.
- Blind isolation is not a DAG edge choice: in any DAG, later nodes can be
  conditioned on earlier outputs by construction; RepliClaw *enforces*
  pre-commit invisibility at the context layer (`ContextEnforcer`,
  `PhaseGate`, tamper-evident `RunStore`), so an edge cannot smuggle a peer's
  conclusion in.
- Commit/reveal with content hashes means the *timing* of belief formation is
  attested: a DAG has no equivalent of "you committed to X before seeing Y."

## Architecture

```
claim ──► [1] BLIND      3+ method-diverse investigators build context from
                         claim + bundled data ONLY (no peer conclusions)
        [2] COMMIT       each finding is sealed (canonical JSON + hash) in the
                         run store before any reveal; tampering is detectable
        [3] REVEAL       content is re-verified against the commitment hash
                         (mismatch ⇒ rejected, run continues with the rest)
        [4] EVIDENCE     revealed findings become typed Evidence (supports /
                         contradicts / replicates / fails_to_replicate /
                         neutral) in a conflict-aware graph
        [5] FOLLOW-UP    conflict ⇒ protocol EMITS a follow-up need
                         (falsification or replication); an independent
                         follow-up investigator commits + reveals for it
        [6] VERDICT      SUPPORTED / REFUTED / INCONCLUSIVE with weighted,
                         provenance-linked evidence references
```

Key modules (`src/repliclaw/`):

| module | responsibility |
|---|---|
| `models.py` | `Claim`, `InvestigatorConfig`, `Evidence`, `NeedItem`, verdict types (ScienceClaw-aligned) |
| `isolation.py` | `PhaseGate`, `ContextEnforcer` — enforced pre-commit blindness |
| `runstore.py` | sealed commitments, reveal verification, event log (tamper-evident) |
| `investigators.py` | `DeterministicInvestigator` (hermetic statistical lenses) + `LLMInvestigator` (OpenAI-compatible, usage-accounting) |
| `protocol.py` | the 6-phase `RepliClawProtocol` (RepliClaw strategy) |
| `evidence.py` | conflict detection, sufficiency, error-correlation proxy |
| `verdict.py` | weighted verdict engine incl. decisive-adjudicator recovery rule |
| `strategies.py` | the 5 coordination baselines on one shared task interface |
| `benchmark.py` | controlled known-answer harness (6 tasks, 4 seeded fault modes) |
| `verify.py` | cross-team `verify(claim, artifacts=None, config=None)` |
| `observability.py` | OTel/OpenInference span emission (no-op when no provider; the Studio OTLP seam) |
| `cli.py` | `repliclaw verify` / `benchmark` / `demo` |
| `scienceclaw_adapter.py` | reuse (not fork) of ScienceClaw Need/Artifact/Reactor primitives |

## Install & test (reproducible)

Python ≥ 3.10.

```bash
# 1. install (ScienceClaw primitives are vendored under deps/scienceclaw)
pip install -e ".[dev]"

# 2. hermetic test suite (no network; 66 tests)
python -m pytest

# 2b. static checks (both configured in pyproject.toml)
ruff check src/repliclaw/ tests/
mypy src/repliclaw/

# 3. inspectable demo outputs under artifacts/
python -m repliclaw.cli demo --out artifacts/demo --backend deterministic
# real generated outputs (requires REPLICLAW_LLM_API_KEY / CUSTOM_SIMULACHAT_KEY):
python -m repliclaw.cli demo --out artifacts/demo-llm --backend llm
```

## Cross-team surface

```python
from repliclaw import verify

report = verify(
    "Treatment increases the event rate by 50% (published RR=1.5) versus control.",
    artifacts=[{"type": "raw_counts", "data": {
        "n": 400, "mean_treat": 6.0, "mean_ctrl": 5.0, "sd_treat": 1.0,
        "sd_ctrl": 1.0, "alpha": 0.05, "baseline_rr": 1.5,
        "events_treat": 200, "events_ctrl": 200, "tot_treat": 1000, "tot_ctrl": 1000,
    }}],
    config={"backend": "deterministic"},
)
print(report.verdict_label, report.verdict_confidence)  # e.g. REFUTED 0.256
print(report.report_path)   # provenance-linked verify_report.md
```

```bash
repliclaw verify --claim "..." --data '{"events_treat":200,...}' \
    [--backend deterministic|llm] [--artifact ...] [--json]
repliclaw benchmark --out artifacts [--backend llm]
repliclaw demo --out artifacts/demo [--backend auto|llm|deterministic]
```

`backend=llm` uses an OpenAI-compatible endpoint (`REPLICLAW_LLM_BASE_URL`,
key via `REPLICLAW_LLM_API_KEY` or `CUSTOM_SIMULACHAT_KEY`, `REPLICLAW_LLM_MODEL`).
`backend=deterministic` is fully offline and hermetic — it applies per-role
statistical lenses (effect size / two-sample t / raw-event risk-ratio with CI)
so the whole protocol is testable without network access.

## Observability (the SimpleAuditStudio seam)

Every run emits conventional **OpenTelemetry** spans (`src/repliclaw/observability.py`):
a `repliclaw.run` root (OpenInference `AGENT`) with per-investigator
`repliclaw.investigator` spans (blinded loop + emergent follow-ups) and per-phase
`repliclaw.phase.*` duration markers. Verdict label/confidence and
`llm.token_count.*` are attached to the run span. Attributes use OpenInference
semantic conventions where they exist and `repliclaw.*` namespaced keys otherwise.

The emission is **OTel API-only and a no-op when no `TracerProvider` is set**, so the
hermetic suite and benchmark never require the SDK. To send spans to
**SimpleAuditStudio** (or any OTLP backend) you only configure a provider at startup:

```python
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.trace import set_tracer_provider

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
set_tracer_provider(provider)   # RepliClaw resolves the tracer lazily per call
```

RepliClaw never imports SimpleAuditStudio (it is a Django + Hatchet + Postgres app —
see D06/D14); the OTLP exporter is the integration point.

## The five baselines (shared task interface)

All strategies receive the same `Claim` and a common investigator factory and
return a common `StrategyResult` (verdict + evidence + needs + usage):

1. `single_agent` — one investigator, one verdict.
2. `fixed_dag` — analyst → statistician → synthesizer (static graph, later
   nodes see earlier outputs — the DAG that RepliClaw is compared against).
3. `isolated_vote` — 3 isolated investigators, majority vote, **no**
   follow-up capability.
4. `open_debate` — 3 investigators see each other's outputs, one debate round,
   **no** commitment seals.
5. `repl_claw` — this protocol (blind commit/reveal + evidence-conditional
   follow-up).

## Controlled benchmark

`tests/fixtures/` holds 6 known-answer tasks: 2 clean (supported / refuted) +
4 seeded fault modes (wrong statistical test, wrong parameter magnitude,
data leakage, cherry-picked subgroup). Nothing is hard-coded: metrics are
computed from run outputs. Representative deterministic-backend results
(reproducible via `python -m repliclaw.cli benchmark --out artifacts`):

| strategy | correctness | false-accept | false-reject | inconclusive | recovery | agents/run |
|---|---|---|---|---|---|---|
| single_agent | 0.167 | 0.500 | 0.000 | 0.333 | 0.000 | 1 |
| fixed_dag | 0.167 | 0.500 | 0.000 | 0.333 | 0.000 | 3 |
| isolated_vote | 0.500 | 0.000 | 0.000 | 0.500 | 0.000 | 3 |
| open_debate | 0.500 | 0.000 | 0.000 | 0.500 | 0.000 | 3 |
| **repl_claw** | **1.000** | **0.000** | **0.000** | **0.000** | **1.000** | 4 |

Recovery = correctly overturning a verdict the naive reading would have made
(the misleading-fault tasks). Cross-strategy error-correlation proxy: 0.558
(error indicators are *not* independent across baselines; RepliClaw's errors
are the least correlated — see `artifacts/benchmark/benchmark_report.md`).

## Demo (real generated outputs)

`repliclaw demo --out artifacts/demo-llm --backend llm` produces, with live
model calls (no injected values):

- `demo_transcript.md` — the full trace: visible commitments **before**
  reveal (sealed hashes from the event log), revealed evidence, the
  disagreement, the autonomously emitted follow-up need, and the final
  provenance-linked verdict;
- `demo_summary.md` / `.json` — verdicts for a genuine supported claim and a
  misleading artifact, plus the baseline comparison table;
- full per-run directories: `events.jsonl`, `commitments/*.json` (with
  `seal_hash`, `reveal_verified`), `evidence.jsonl`, `needs.jsonl`,
  `verdict.json`, `verify_report.md`.

If the model underperforms on a case, the transcript shows that — the demo
never edits results.

## Repository layout

```
src/repliclaw/        the library (see module table above)
tests/                66 hermetic tests (isolation, commit/reveal integrity,
                      contradiction → follow-up, verdict provenance,
                      strategies, benchmark, CLI/verify, OTel spans)
tests/fixtures/       known-answer benchmark tasks
artifacts/            demo + benchmark outputs (reproducible)
deps/scienceclaw/     vendored ScienceClaw primitives (reused, not forked)
docs/agent/           archived full autonomy policy
TASK_SPEC.md          acceptance contract (AC01–AC18)
DECISIONS.md / PROGRESS.md / EXECUTION_STATE.md / IMPLEMENTATION_PLAN.md
                      living engineering state
```

## Acceptance-criteria evidence map

| AC | evidence |
|---|---|
| AC01 | this README; `pip install -e ".[dev]"` + `python -m pytest` (66 tests, hermetic) |
| AC02 | `repliclaw verify` CLI + `verify()` Python API (src/repliclaw/cli.py, verify.py) |
| AC03 | 3+ investigators with `ContextEnforcer`/`PhaseGate`; tests/test_isolation.py |
| AC04 | sealed `Commitment` records pre-reveal; mismatch ⇒ REJECTED + re-seal; tests/test_commit_reveal.py |
| AC05 | reveal verified vs commitment hash; `Evidence` carries commitment/evidence refs; tests/test_commit_reveal.py |
| AC06 | `detect_conflicts` + agreement event; test_verdict.py, protocol events |
| AC07 | conflict ⇒ emitted follow-up need, fulfilled by independent investigator (no hardcoded workflow); demo transcript phase 5 |
| AC08 | `compute_verdict` ⇒ SUPPORTED/REFUTED/INCONCLUSIVE with evidence refs; tests/test_verdict.py |
| AC09 | `STRATEGY_RUNNERS` — all 5 baselines; tests/test_strategies.py |
| AC10 | 6 known-answer fixtures, 4 seeded fault modes; tests/test_benchmark.py |
| AC11 | `benchmark.py` metrics: correctness/FA/FR/inconclusive, error-correlation proxy, recovery, diversity, tokens, latency; artifacts/benchmark/ |
| AC12 | misleading_wrong_test end-to-end: conflict → follow-up falsification → REFUTED recovery; artifacts/demo/case_misleading/ |
| AC13 | this README §Cross-team surface + §Observability; tests/test_cli_and_verify.py; tests/test_observability.py (OTel/OpenInference span emission) |
| AC14 | 66-test suite incl. isolation, commit/reveal integrity, contradiction/follow-up, verdict provenance, benchmark re-run determinism, OTel span emission |
| AC15 | `python -m pytest` (66 passed); `ruff check` (0 errors); `mypy src/repliclaw/` (no issues); `[tool.ruff]`+`[tool.mypy]` in pyproject.toml |
| AC16 | `repliclaw demo` → artifacts/demo*/ (deterministic, committed) + artifacts/demo-llm (live) |
| AC17 | this README (hypothesis, architecture, baselines, reproduction, not-a-fixed-DAG) |
| AC18 | all reported numbers computed by the harness at run time; demo shows real model outputs with per-call usage accounting |


## Active ScienceClaw 2026 competition program (October 8, 2026)
**Important:** This README documents the existing prototype and its archived six-fixture benchmark, NOT a proven competition-winning scientific result. The real live-LLM misleading-case comparison in `artifacts/demo-llm/` shows all five strategies succeed; no RepliClaw advantage has yet been demonstrated. The new competition program is **WORKING**.

- [Competition strategy / rubric](docs/COMPETITION_STRATEGY.md)
- [Active implementation tickets F00–F10](IMPLEMENTATION_PLAN.md)
- [VS Code parallel-agent fleet](docs/FLEET_PLAYBOOK.md)
- [Quality gates and independent judges](docs/QUALITY_GATES.md)
- [Current execution state](EXECUTION_STATE.md)
- [Checkpoint history](docs/checkpoints/CP-20261008-PLAN.md)
- [Agent seed prompt](SEED_PROMPT.md)
- [Submission checklist](docs/SUBMISSION_CHECKLIST.md)

The immediate next step is G0 (reproduce current tests and scientific evidence), then staged fleet work in isolated worktree sessions. Existing runnable CLI/tests remain unchanged by the planning update.
