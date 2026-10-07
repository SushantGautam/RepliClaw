# RepliClaw — Reuse-First Architecture Strategy

## Principle
RepliClaw is an experiment and protocol built from existing systems, not a new generic agent platform.

Before implementing any subsystem, answer:
1. Does ScienceClaw already provide this execution/provenance primitive?
2. Does SimpleAuditStudio/SimpleAudit already provide this experiment/audit primitive?
3. Does an established open standard or library provide this instrumentation/evaluation primitive?
4. Can a small adapter/extension solve the gap cleanly?

Only build a new subsystem when the answer is demonstrably no. Record that decision in `DECISIONS.md`.

## Preferred system boundaries

### ScienceClaw: decentralized scientific execution substrate
Reuse upstream ScienceClaw for:
- scientific agents and heterogeneous skill/tool access;
- immutable/content-hashed artifacts and artifact lineage DAG;
- `NeedItem` / unmet-needs broadcasts;
- `ArtifactReactor` plannerless follow-up;
- mutation/conflict handling where useful;
- persistent investigation state;
- Infinite publication/provenance where useful.

RepliClaw additions should be thin protocol extensions around:
- blind-phase visibility/isolation;
- commit/reveal semantics;
- scientific relation metadata needed for replication/falsification;
- explicit independence/provenance assertions;
- hooks that emit evaluation evidence to Studio.

Do not fork/reimplement generic scientific orchestration unless upstream APIs cannot support the required isolation or follow-up behavior.

### SimpleAuditStudio: experiment, evaluation, and control plane
Treat `SimulaMet/SimpleAuditStudio` as a first-class dependency and preferred place for evaluation features. We own it and may make upstream changes when the abstraction is broadly useful.

Current Studio capabilities that should be reused rather than rebuilt:
- versioned scenarios and scenario sets;
- versioned judges and criteria;
- frozen target/auditor/judge/agent config snapshots for reproducibility;
- Agent configuration and Open WebUI-backed KB/tool/MCP resource management;
- durable Hatchet audit execution and retries;
- experiment grouping, repetitions, monitors, comparisons, run events and SSE progress;
- OTLP ingestion and persistence;
- provider-neutral agent trajectory normalization;
- deterministic agentic checks for tools, retrieval, permissions, sequence/order, handoffs, errors, state and budgets;
- robust argument matchers;
- semantic agentic judge dimensions;
- agentic verdict policy including `INCONCLUSIVE` for missing evidence;
- trace-aware result UI and agentic pass/status metrics.

Relevant current areas to inspect before writing code:
- `docs/architecture.md`
- `audits/agentic/schema_v2.py`
- `audits/agentic/`
- `infra/engine.py`
- `infra/worker.py`
- `audits/services.py`
- `model_registry/models.py`
- `model_registry/otlp_views.py`
- `infra/ui.py`
- `templates/partials/result_rep_panel.html`
- `docs/chat.md`
- agent/resource models and Open WebUI adapters under `integrations/openwebui/`

## Recommended RepliClaw/Studio integration

Use Studio to model a RepliClaw evaluation as a reproducible experiment rather than creating a second benchmark database/UI.

Suggested mapping:

| RepliClaw concept | Existing Studio primitive | Likely extension |
|---|---|---|
| Scientific task/claim | Scenario + revision | Add scientific claim/reference truth/failure-injection metadata if needed |
| Coordination architecture | Agent / target config + run metadata | Add `coordination_strategy` / protocol version to frozen snapshot |
| Baseline comparison | Experiment containing multiple AuditRuns | Generate one run per strategy under matched budgets |
| Repetition | existing `n_repetitions` | Reuse directly |
| Agent execution evidence | OTLP spans / normalized trajectory | Add ScienceClaw/OpenInference normalization only where missing |
| Scientific artifacts | trace span attributes + external artifact refs | Store references, not duplicate large payloads |
| Blind/commit/reveal checks | agentic deterministic checks | Add custom check categories / schema fields |
| Final scientific verdict | agentic evaluation + semantic judge | Add evidence-aware scientific verdict evaluator rather than separate judge platform |
| Metrics | run/result aggregation | Add RepliClaw metrics/experiment comparison views/export |
| Live progress | AuditEvent + SSE | Reuse directly |
| Cross-team verification | API/CLI invoking Studio audit | Thin endpoint/client, not separate service if practical |

## Studio schema extensions to investigate

Do not modify schema until current code is inspected. Candidate additions to `agentic` scenario metadata v2 or a clean v3 extension:

```yaml
scientific_verification:
  claim: "..."
  reference_outcome: supported|refuted|null
  protocol: blind_commit_reveal
  minimum_independent_investigators: 3
  require_commit_before_reveal: true
  require_independent_evidence: true
  followup_on:
    - disagreement
    - weak_evidence
    - failed_replication
  seeded_faults: []

independence:
  blind_until: reveal
  forbidden_cross_agent_context: true
  required_distinct_evidence_sources: null

commit_reveal:
  required: true
  canonicalization_version: v1
  reject_hash_mismatch: true
```

Prefer general names that are useful beyond this hackathon. If extending v2 would create awkward semantics, create a backwards-compatible schema v3 rather than stuffing arbitrary data into `metadata`.

## Trace/interchange standards

### Prefer OpenTelemetry + OpenInference
Do not create a proprietary trace format.

Use OpenTelemetry as transport and OpenInference semantic conventions where possible for:
- LLM spans;
- agent/tool/retriever spans;
- inputs/outputs when content capture permits;
- session/trace identifiers;
- trace/session evaluations and annotations;
- artifact IDs and RepliClaw protocol metadata as namespaced attributes when no standard field exists.

Studio can continue normalizing incoming provider/framework traces into its provider-neutral trajectory for judging.

### Instrumentation libraries to reuse
Before hand-instrumenting a framework, check OpenInference instrumentation packages. Current ecosystem includes OpenAI Agents, LangChain/LangGraph, LlamaIndex, DSPy and others. Phoenix is a useful reference implementation and optional debugging viewer, but should not replace Studio's owned experiment/audit plane unless it gives a concrete capability we lack.

## External libraries/products worth selectively reusing

### Arize Phoenix / OpenInference
Use for:
- semantic conventions;
- auto-instrumentation packages;
- reference behavior for agent traces/evaluations;
- optional local trace debugging during development.

Do **not** duplicate Phoenix's full observability UI inside RepliClaw. Studio already owns run storage, comparisons, auditing, and trace-aware UI.

### AgentEvals / LangSmith patterns
Use as references or small dependencies where useful for:
- exact trajectory matching;
- trajectory LLM judges;
- single-step vs whole-trajectory evaluation patterns.

Prefer implementing any RepliClaw-specific metric in SimpleAudit/Studio when it needs frozen experiment provenance or must work across frameworks.

### Braintrust patterns
Use as inspiration for turning production/real-event traces into reusable scored datasets and regression cases. Avoid adding another hosted evaluation dependency unless it materially reduces work.

### NetworkX
If a graph library is needed for evidence/provenance analysis, prefer a mature graph package such as NetworkX rather than creating graph algorithms by hand, unless ScienceClaw's artifact DAG utilities already suffice.

### statistical/scientific stack
Reuse established libraries for metrics and analysis (`numpy`, `scipy`, `pandas`, `statsmodels`, `scikit-learn` where already appropriate) rather than custom statistical tests. Pin/report versions in generated experiment metadata.

## What should live upstream where?

### Upstream to ScienceClaw when generic
Changes belong in ScienceClaw when they improve any decentralized scientific collective, for example:
- artifact visibility states / sealed artifacts;
- generic commit/reveal artifact support;
- generic independence metadata;
- unmet need categories for replication/falsification;
- OTel/OpenInference instrumentation of ScienceClaw execution.

### Upstream to SimpleAudit/SimpleAuditStudio when generic
Changes belong in Studio/core when useful for auditing any agent system, for example:
- new agentic scenario schema capabilities for multi-agent independence;
- trace checks for information leakage, commit-before-reveal, evidence independence;
- multi-agent trajectory normalization;
- scientific evidence/verdict evaluator interfaces;
- experiment-level error-correlation and robustness metrics;
- strategy/baseline comparison visualization.

### Keep in RepliClaw when experiment-specific
Keep only the research protocol and benchmark-specific pieces in RepliClaw:
- blind-replication coordination policy;
- fault-injection benchmark fixtures;
- architecture/baseline adapters;
- competition demo configuration;
- ScienceClaw-to-Studio glue that is not yet generic enough upstream.

## Mandatory reuse reconnaissance gate
Before M1 begins, create a reuse matrix in `DECISIONS.md` covering at least:
- agent creation/configuration;
- scientific agent execution;
- durable task execution;
- artifact storage/provenance;
- trace transport/instrumentation;
- trajectory normalization;
- scenario/dataset versioning;
- judges/evaluators;
- baseline experiment scheduling;
- progress/live UI;
- metrics and comparison visualization;
- cross-team API/CLI.

For each row choose exactly one of:
- `REUSE_AS_IS`
- `EXTEND_SCIENCECLAW`
- `EXTEND_SIMPLEAUDIT`
- `ADOPT_LIBRARY`
- `BUILD_REPLICLAW`

`BUILD_REPLICLAW` requires a short explanation of why the alternatives are insufficient.
