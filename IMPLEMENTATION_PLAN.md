# RepliClaw — Living Implementation Plan

This is a working plan, not a contract. The agent should revise it as repository evidence changes. Preserve the acceptance criteria in `TASK_SPEC.md`; change implementation details freely when a better route is demonstrated.

## M0 — Repository reconnaissance and architecture decision
Status: `TODO`

Deliverables:
- inspect repo structure, existing tests, dependency manager, CLI/API patterns, agent framework, persistence, and current git state;
- determine whether this is ScienceClaw itself, a fork, or a separate integration repo;
- inspect the installed/current ScienceClaw version and relevant upstream files rather than relying only on this plan;
- identify the minimal extension points for artifact creation, needs, reactions, execution, and provenance;
- discover exact project commands for install, unit tests, integration tests, lint/typecheck/build;
- record material architecture decision(s) in `DECISIONS.md`;
- update this plan with concrete file/module targets.

Verification:
- run existing focused smoke/test command before edits where practical;
- record baseline failures separately from new failures.

Parallel work candidates:
- codebase architecture reconnaissance;
- upstream ScienceClaw/API research;
- existing test/benchmark reconnaissance;
- threat/independence-model review.

## M1 — Minimal domain model and vertical skeleton
Status: `TODO`

Implement the smallest stable interfaces for:
- claim/subclaim;
- investigator identity/context;
- commitment;
- reveal;
- evidence/provenance relation;
- verification need;
- verdict/report;
- coordination strategy interface so baselines can share the same task plumbing.

Prefer extending existing ScienceClaw Artifact/Need structures rather than parallel storage if compatible.

Build one deterministic in-memory/local-fixture vertical path before introducing model/tool complexity.

Verification:
- unit tests for serialization/canonicalization/stable hashes;
- one smoke command from claim → empty/fixture report.

## M2 — Blind commit/reveal independence protocol
Status: `TODO`

Implement:
- pre-reveal context isolation;
- >=3 investigator execution path;
- canonical commitment payload;
- persisted commitment before reveal;
- reveal verification;
- explicit failure on mismatched/tampered reveal;
- audit metadata proving what each investigator could see at each phase.

Do not rely on prompt wording alone for independence if the runtime can enforce it structurally.

Verification:
- test that investigator B cannot access A's unrevealed content through normal system APIs/context;
- test tampered reveal rejection;
- concurrent/parallel investigation test if runtime supports it.

## M3 — Evidence graph, disagreement, and emergent follow-up
Status: `TODO`

Implement:
- relations such as supports / contradicts / replicates / fails-to-replicate / depends-on;
- deterministic or well-tested disagreement detection boundary;
- creation of follow-up Need when evidence conflicts or is insufficient;
- fulfillment through native ScienceClaw ArtifactReactor/NeedItem when viable, otherwise through a thin adapter preserving the same plannerless semantics;
- new evidence attached as child/related provenance rather than overwriting history.

Verification:
- fixture where initial investigators conflict;
- verify a new need is emitted;
- verify an eligible independent worker fulfills it without a hardcoded full trajectory;
- verify lineage from claim → initial evidence → follow-up → verdict.

## M4 — Verdict engine
Status: `TODO`

Implement a transparent evidence-aware verdict layer:
- SUPPORTED;
- REFUTED;
- INCONCLUSIVE;
- confidence/calibration field or explicit uncertainty representation;
- unresolved conflicts surfaced, not hidden;
- independent evidence/provenance references in output.

Do not use simple majority as the sole decision rule.

Verification:
- fixtures covering all verdict classes;
- contradictory evidence must be visible in report;
- missing/insufficient evidence must support abstention/inconclusive rather than forced certainty.

## M5 — Coordination baselines
Status: `TODO`

Implement the same task interface for:
- single agent;
- fixed central DAG;
- isolated independent agents + simple aggregation;
- open debate/shared-context agents;
- RepliClaw blind/decentralized protocol.

Keep model, tool access, task data, and budget as comparable as practical. Make differences explicit in generated run metadata.

Verification:
- a single command/config can execute each strategy on the same fixture;
- result schema is common enough for automatic comparison.

## M6 — Controlled benchmark and failure injection
Status: `TODO`

Create known-answer scientific/technical tasks with at least three seeded failure modes. Favor tasks that execute quickly and deterministically enough for repeated architecture comparisons.

Implement metrics:
- correctness;
- false accept / false reject;
- inconclusive;
- error-correlation metric/proxy;
- recovery under bad evidence;
- independent evidence count/diversity;
- latency;
- resource/cost data exposed by the runtime.

Generate machine-readable results plus a concise Markdown/CSV summary. Never hard-code desired scores.

Verification:
- benchmark runs from a clean documented command;
- rerun at least a small subset to detect nondeterministic breakage;
- metric unit tests with synthetic expected values.

## M7 — Real task adapter
Status: `TODO`

After the controlled benchmark is stable, integrate a small real executable scientific task set. Candidate: a carefully selected FIRE-Bench subset or another benchmark compatible with available tooling.

Do not let external dataset/tool instability block the controlled benchmark or demo.

Verification:
- at least one real-task end-to-end run saved with provenance and raw outputs.

## M8 — Cross-team verifier surface
Status: `TODO`

Expose a minimal reuse path:
- CLI `repliclaw verify ...` and/or Python/API function;
- accepts a claim and optional existing ScienceClaw artifacts/files;
- produces a stable machine-readable result and a human-readable report;
- document a <5 minute quickstart for another team.

If practical, make the interface installable/usable without modifying the caller's main project.

Verification:
- fresh-shell or clean-environment smoke test following the documented quickstart exactly.

## M9 — Demo, reporting, and competition evidence
Status: `TODO`

Create one reproducible demo with:
- visible blind phase;
- commitments;
- reveal;
- misleading/faulty evidence;
- disagreement;
- autonomous follow-up;
- final verdict;
- baseline comparison using actual saved results.

Save outputs under a stable path and generate a competition-ready result summary from data, not manually typed numbers.

## M10 — Final hardening
Status: `TODO`

- run self-review and independent code review;
- run relevant full tests/build/lint/type checks;
- inspect git diff/status;
- remove debug residue;
- validate docs/quickstart from scratch;
- map every AC01–AC18 item to evidence;
- mark `EXECUTION_STATE.md` `COMPLETE` only when mandatory criteria are satisfied.
