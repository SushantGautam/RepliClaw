# REPLICLAW RESEARCH MISSION (v2, supersedes older completion targets)

**Primary scientific problem:** decentralized, independently precommitted, experimentally verified **AI failure cause diagnosis** using a shared evidence ledger and local experiment selection. Build only what can be rigorously measured. See `docs/EVIDENCE_ESCROW_SWARM.md`, `docs/EXPERIMENT_PROTOCOL_V2.md`, `docs/PRIOR_ART_NOVELTY_GATE.md`, `docs/FLAGSHIP_CASE.md`. The RepliClaw prototype's historic goals AC01–AC18 remain archival. Next work tickets are P00–P12 in `IMPLEMENTATION_PLAN.md`. Resume safely using `docs/AGENT_MIGRATION.md`. A green old test suite or deterministic toy benchmark does NOT complete these scientific acceptance criteria. Scientific originality relative to AutoScientists/AgentRx remains to be demonstrated, not presumed. Human review owns any external publication of results.

---

# RepliClaw — Task Specification

## Goal
Build a research-grade prototype for the RepliClaw research program that tests and demonstrates the following scientific/engineering hypothesis:

> Preserving epistemic independence between autonomous scientific agents before they exchange conclusions reduces correlated errors and false scientific consensus compared with single-agent, fixed-workflow, isolated-vote, and open-debate systems under comparable resource budgets.

Working name: **RepliClaw**.

The product is a decentralized blind replication/falsification collective, not another generic hypothesis-generation swarm.

## Project constraints
RepliClaw is an independent research project (SimuMet AI Safety research
department); there is no external submission target. Design constraints that
shape the work:

- Scientific/Technical Impact and rigorous, falsifiable measurement are the
  top priorities; results must be reproducible from committed evidence.
- Collective capability must be demonstrated, not assumed (independent
  pre-outcome commitments, verified counterfactual execution, decentralized
  selection — each measured against a strong central-manager comparator).
- Problem significance and complexity are stated in
  [docs/EVIDENCE_ESCROW_SWARM.md](docs/EVIDENCE_ESCROW_SWARM.md).
- Decentralized agency must be real: no hidden central coordinator on the
  EESS arm (audited in code + traces).
- Execution & validation: every claim backed by committed run artifacts and
  an independent review.
- Collaboration: a minimal reusable interface for other research teams (see
  Cross-team collaboration surface below).

Optimize the implementation for convincing measured capability, not architectural complexity.

## Existing ScienceClaw primitives to reuse when available
The current upstream ScienceClaw repository already provides an artifact DAG, immutable/content-hashed artifacts, per-agent stores, a shared global index, `NeedItem`/needs broadcasts, `ArtifactReactor` plannerless follow-ups, mutation/conflict handling, scientific skills, persistent investigation state, and Infinite publishing/provenance.

Do not rebuild these generically if the installed/current upstream implementation can be extended cleanly. Inspect the actual repository/version first.

Relevant upstream areas observed on 2026-10-07 include:

- `artifacts/artifact.py`
- `artifacts/needs.py`
- `artifacts/reactor.py`
- `artifacts/mutator.py`
- `autonomous/deep_investigation.py`
- `memory/investigation_tracker.py`

Current upstream: https://github.com/lamm-mit/scienceclaw

## Reuse-first implementation constraint

RepliClaw must not become a parallel agent/audit platform. Treat these existing systems as first-class dependencies and extension targets:

- **ScienceClaw** = decentralized scientific execution, skills, artifacts, lineage, unmet needs and plannerless reactions.
- **SimpleAuditStudio/SimpleAudit** = agent configuration, versioned audit scenarios/judges, reproducible frozen runs, durable Hatchet execution, OTLP evidence ingestion, provider-neutral trajectory normalization, deterministic agent checks, semantic judging, comparisons and trace-aware UI.
- **OpenTelemetry/OpenInference** = preferred interoperability and instrumentation layer.

We own `SimulaMet/SimpleAuditStudio` and may change it upstream. Prefer a clean generic Studio/SimpleAudit extension over implementing duplicate audit/evaluation infrastructure inside RepliClaw. Likewise, prefer a generic ScienceClaw upstream extension for sealed artifacts, commit/reveal, independence metadata, replication needs or tracing when those concepts belong naturally there.

Read `REUSE_STRATEGY.md` before architecture decisions. M0 is not complete until a reuse matrix documents whether each major capability is reused, extended upstream, adopted from an established library, or genuinely needs RepliClaw-specific code.

## Core protocol
A verification run begins with a scientific claim plus optional artifacts/data/code.

1. **Claim normalization**
   - Convert the incoming claim into a structured claim record and, where useful, atomic subclaims/assumptions.

2. **Blind independent investigations**
   - Launch at least 3 investigator paths with isolated pre-reveal context.
   - Before commit, an investigator must not receive another investigator's conclusion, analysis plan, or result.
   - Investigators may differ in tools, evidence sources, methods, or models.

3. **Commit**
   - Persist a tamper-evident commitment before reveal.
   - At minimum commit to canonicalized hypothesis/conclusion, analysis/experiment plan, evidence/result metadata, and content hash/timestamp/agent identity.
   - Reuse ScienceClaw artifact integrity/lineage where appropriate rather than inventing unnecessary cryptography.

4. **Reveal**
   - Reveal committed outputs and verify them against their commitments.
   - A post-hoc edit that changes committed content must be detectable.

5. **Evidence graph**
   - Build a provenance-aware graph relating claims, assumptions, experiments, evidence, replications, contradictions, and agents.
   - Independence/provenance must be inspectable rather than asserted.

6. **Emergent follow-up**
   - Agreement may close a branch when evidence suffices.
   - Disagreement, weak evidence, or failed reproduction creates an unmet replication/falsification need.
   - Available agents autonomously pick up appropriate needs; the entire future investigation path must not be pre-scripted as one fixed DAG.
   - Prefer native ScienceClaw `NeedItem`/`ArtifactReactor` mechanisms if they fit.

7. **Verdict**
   - Output one of `SUPPORTED`, `REFUTED`, or `INCONCLUSIVE` (extensions allowed if justified), with confidence/calibration information and direct provenance links to evidence.
   - Do not turn majority vote alone into the verdict. Weight executable/independent evidence and unresolved contradictions explicitly.

## Required baselines
Implement reproducible runners for the same task under comparable model/tool/compute or token budgets:

1. single strong agent;
2. fixed central workflow/DAG (research → analysis/experiment → critique/judge or repository-equivalent);
3. isolated independent agents followed by simple aggregation/vote;
4. open shared-context multi-agent debate;
5. RepliClaw blind commit → reveal → evidence-driven decentralized follow-up.

Log actual resource usage sufficient to make comparisons interpretable.

## Evaluation
Create an automated evaluation harness that supports at least a controlled benchmark with objectively known outcomes and seeded scientific failure modes.

Seeded failures may include:

- wrong statistical test;
- data leakage/test contamination;
- incorrect parameter/unit;
- fabricated or unsupported citation/evidence;
- cherry-picked result;
- plausible but wrong conclusion;
- corrupted/misleading upstream artifact;
- one intentionally unreliable/persuasive agent.

At minimum report:

- task/claim correctness;
- false-accept rate;
- false-reject rate;
- abstention/inconclusive rate;
- pairwise/cross-agent error correlation or an explicit proxy;
- recovery rate after misleading/bad evidence;
- independent evidence diversity/count;
- cost/token/tool-call usage where available;
- wall-clock latency.

Do not manufacture desired results. If RepliClaw underperforms, preserve the result, diagnose why, and improve or refine the hypothesis based on evidence.

A small real benchmark adapter (for example a suitable FIRE-Bench subset or another executable scientific task suite) is desirable after the controlled benchmark works, but must not block the core demo.

## Cross-team collaboration surface
Provide a minimal reusable interface suitable for another research team, e.g. conceptually:

```bash
repliclaw verify --claim "..." [--artifact ...]
```

and/or a small Python/API surface such as:

```python
verify(claim, artifacts=None, config=None)
```

Another team should be able to submit its central claim/artifacts and receive a provenance-linked verification report without adopting the whole codebase.

## Demo target
The final demo should be able to show, using real generated outputs:

1. a scientific claim;
2. independent agents working without seeing peer conclusions;
3. visible commitments before reveal;
4. a disagreement or corrupted-evidence case;
5. an autonomously generated follow-up replication/falsification need;
6. evidence that resolves or preserves the disagreement;
7. a final provenance-linked verdict;
8. a comparison chart/table against at least the most relevant baselines;
9. ideally, evidence of another team/system using the verifier.

## Mandatory acceptance criteria
- [ ] AC01: Repository setup/install/test path is documented and reproducible from a clean environment supported by the project.
- [ ] AC02: Structured claim ingestion exists through a CLI, API, or both.
- [ ] AC03: At least 3 independent investigators can run with enforced pre-commit information isolation.
- [ ] AC04: Commit records are persisted before reveal and tampering/content mismatch is detected.
- [ ] AC05: Reveal produces provenance-linked evidence artifacts.
- [ ] AC06: Agreement/disagreement is computed from revealed evidence/results.
- [ ] AC07: A disagreement/weak-evidence case creates a follow-up need that is fulfilled without hardcoding the entire future workflow.
- [ ] AC08: Final verdict supports `SUPPORTED`, `REFUTED`, and `INCONCLUSIVE` behavior with evidence references.
- [ ] AC09: Runners exist for all five required coordination baselines.
- [ ] AC10: Controlled evaluation includes known-answer tasks and at least three seeded error modes.
- [ ] AC11: Evaluation reports correctness, false accepts/rejects, inconclusive rate, error-correlation/proxy, robustness/recovery, latency, and resource-use data available from the stack.
- [ ] AC12: At least one end-to-end scenario demonstrates detection/recovery from a misleading or faulty scientific artifact/agent.
- [ ] AC13: Cross-team `verify` interface is documented and works end-to-end.
- [ ] AC14: Core behavior has automated tests, including isolation, commit/reveal integrity, contradiction/follow-up behavior, and verdict provenance.
- [ ] AC15: Relevant test suite plus build/type/lint checks for changed code pass, or pre-existing unrelated failures are precisely documented with evidence.
- [ ] AC16: A reproducible demo command produces inspectable outputs under `artifacts/` or another documented output location.
- [ ] AC17: README/docs explain the scientific hypothesis, architecture, baselines, how to reproduce results, and why the decentralized behavior is not equivalent to a fixed DAG.
- [ ] AC18: No reported metric/demo value is fabricated or manually hard-coded as if produced by an experiment.

## Non-goals until core acceptance criteria work
- elaborate web UI (reuse/extend SimpleAuditStudio UI instead);
- blockchain infrastructure;
- custom cryptography beyond what integrity/provenance requires;
- recreating ScienceClaw orchestration primitives already present upstream;
- recreating SimpleAuditStudio experiment storage, agent configuration, Hatchet execution, OTLP ingestion, trajectory normalization, judges, result comparison, or progress UI;
- proprietary trace schemas when OTel/OpenInference can represent the data;
- broad support for every scientific domain;
- optimizing leaderboard numbers before the experiment is reproducible.

## Engineering quality bar
Prefer a small testable core with explicit interfaces. Maintain deterministic fixtures where possible. Separate orchestration/coordination policy from scientific task adapters so baselines differ primarily in coordination regime rather than unrelated code.


## 2026-10-08 research-program extension — authoritative for new work
The acceptance criteria AC01–AC18 above describe historical prototype scope, NOT the current research-program finish line. Active acceptance tickets F00–F10, dependency order and verification gates are in `IMPLEMENTATION_PLAN.md`, `docs/COMPETITION_STRATEGY.md`, `docs/QUALITY_GATES.md`. Program COMPLETE requires a *real executable scientific finding*, genuinely decentralized need claim/fulfillment, verified per-agent commit-before-reveal, faithful resource-matched baselines plus ablations, independent scientific and code reviews, and reproducible experiment artifacts. Cross-team demonstration is bonus but should be actively sought. Keep negative/null outcomes. Do not invent release details.
