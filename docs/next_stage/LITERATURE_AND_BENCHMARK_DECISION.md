# RepliClaw Stage 2 — Literature review and benchmark decision

Status: RESEARCH DECISION / PROPOSED (2026-10-09). This document is a literature-grounded selection, not a claim that integrations or reruns have succeeded.

## Why Stage 2 exists: counterevidence from P08

The live 120-run P08 single-case campaign establishes a protocol contrast: S5 diagnosis M1 1.00 vs S4 0.20, within-case bootstrap Δ=0.80 [0.60,0.95]. **But S5, no-escrow A1 and random selection A3 ALL achieved 1.00 because all execute I_R/I_P/I_J; S0/S3/S4 never execute them.** The scientific result supports executable counterfactual discrimination of the retrieval-vs-judge confound, not swarm autonomy, escrow or decentralization. Read docs/experiments/P1_RESULT_STATEMENT_20261009.md and independent reviews before coding. Do not recast P08 as evidence for autonomy.

## Evidence-grounded shortlist — no bespoke benchmark by default

| Benchmark / reference | Real problem and source | Reusable evaluation | Intervention semantics | Stage-2 decision |
|---|---|---|---|---|
| **AgentRx (Barke et al., 2026, arXiv:2602.02475)** | 115 human-annotated failed agent trajectories, three reported domains (tau-bench, Flash, Magentic-One). github.com/microsoft/AgentRx ; huggingface.co/datasets/microsoft/AgentRx | First critical failure step + category, taxonomy, trace normalization, published baseline implementation | Primarily **offline recorded traces**; cannot presume executable intervention/replay | **Track O-A (HIGH)**: externally validated observational RCA, compare paper's runnable AgentRx baseline using identical accessible subset |
| **RCAEval (Pham et al., ASE'24/WWW'25, arXiv:2412.17015)** | 735 microservice failure cases across RE1/RE2/RE3 (Online Boutique/Sock Shop/Train Ticket), 11 fault types. github.com/phamquiluan/RCAEval | Root-cause service/indicator, official ranking evaluator, BARO/RCD/CIRCA and other reproducible baselines | Recorded telemetry with injected-fault ground truth; **NOT** a replayable intervention interface for stored cases | **Track O-R (HIGH)**: many-case, cross-domain ground-truth external evaluation and cost curves. Begin with selected RE1 and RE2 stratified cases |
| **AIOpsLab (Chen et al., MLSys'25, arXiv:2501.06706)** | github.com/microsoft/AIOpsLab ; benchmarked detection, localization, diagnosis, mitigation in instrumented services | Real fault injection, workload, telemetry, interactive agent/orchestrator APIs, official evaluators | Genuine executable fault injection is supported; **counterfactual resets and equivalent policy access require feasibility verification** | **Track I (HIGH, decisive)**: intervention-matched centralized vs decentralized test; engineer only a thin adapter, no new AIOps benchmark |
| **Causal Agent Replay / CAR (Shah, 2026, arXiv:2606.08275)** | github.com/jaineet17/causal-agent-replay | Step-level do_resample/do_action/do_observation/do_context/do_policy; repeated policy replay + uncertainty | Executable trajectory-level interventions; different estimand from RepliClaw's audited-system-factor tests | **Strong causal-method comparator**, where API/case/outcome equivalence is demonstrable; no unqualified cross-method scoreboard |
| **ScienceAgentBench verified (Chen et al., ICLR'25, arXiv:2410.05080)** | github.com/OSU-NLP-Group/ScienceAgentBench ; HF osunlp/ScienceAgentBench split=verified (Apr 2026 update) | 102 tasks from 44 published papers, executable program outputs, VER/SR/cost, verified evaluation artifacts | Scientific programming tasks, NOT directly failure localization or intervention | **Track S (DEFER)** until intervention-matched result. Later test transfer of scientific-investigation policies without redefining official metrics |
| **DiscoveryBench (Allen Institute for AI)** | github.com/allenai/discoverybench | Data-driven hypothesis discovery and open-ended hypothesis evaluation | Static datasets; hypothesis scoring, NOT root-cause replay | Optional later scope, not a stage-2 critical dependency |

Sources and access notes:
- AgentRx: https://arxiv.org/abs/2602.02475 ; https://github.com/microsoft/AgentRx ; https://huggingface.co/datasets/microsoft/AgentRx . **Official HF dataset is gated**; obtain authorized access, never bypass gate. The public card describes two domain splits; paper describes three domains. Reconcile the accessible release against the paper and document exactly which examples are available. The GitHub README describes a 10-category taxonomy while a March blog describes nine; use the exact **versioned release** taxonomy without quietly remapping categories.
- RCAEval: https://github.com/phamquiluan/RCAEval ; https://huggingface.co/datasets/phamquiluan/RCAEval ; https://arxiv.org/abs/2412.17015 . The repo lists 735 annotated cases, official evaluation and many ranking baselines; full data can be many GB. Pin tag/commit, index and per-suite sample manifest.
- AIOpsLab: https://github.com/microsoft/AIOpsLab ; https://arxiv.org/abs/2501.06706 ; https://microsoft.github.io/AIOpsLab/pages/leaderboard/ . May need Python>=3.11, Kubernetes/Helm, cluster resources and isolated namespaces; no production cloud mutation. The published leaderboard is contextual only, NOT an apples-to-apples baseline score against a different model/environment.
- CAR: https://arxiv.org/abs/2606.08275 ; https://github.com/jaineet17/causal-agent-replay . Requires replay fidelity check first; stochastic re-execution must report residual nondeterminism.
- ScienceAgentBench: https://github.com/OSU-NLP-Group/ScienceAgentBench ; https://huggingface.co/datasets/osunlp/ScienceAgentBench . The verified split/revised artifacts matter; some benchmark source data must not be redistributed.

## The research question after P08

**Does evidence escrow and/or decentralized experiment selection improve causal diagnostic quality, falsification, diversity, or efficiency AFTER the centralized manager has the SAME counterfactual tool interface and intervention budget?**

Separate the outcomes of two distinct protocols:
1. **Observational diagnosis** (AgentRx/RCAEval): no live intervention capability. Judge external generalization and compare directly to official baselines; do **not** label it a causal-intervention victory.
2. **Interactive causal diagnosis** (AIOpsLab or another independently validated, replayable fault environment): all strategy arms have equivalent action sets and controlled intervention opportunities. This tests coordination/selection effects separately from mere access to interventions.

## Reuse-first engineering

- AgentRx: first run unmodified official baseline on fixed examples; inspect IR, labels and scorer. Wrap its loader/format; do not reimplement failure taxonomy or scoring.
- RCAEval: pin evaluator package, load canonical case index (cases.parquet), use official service-ranking metrics; start CPU metrics RE1 then logs/traces RE2. Do not translate service identification into RepliClaw's unrelated five-way defect labels.
- AIOpsLab: wrap official problem registry/Orchestrator and fault injection; prove reproducible reset, non-leaking oracle and evaluator independence before running human-costly campaigns. Expose identical admissible diagnostic actions to all arms.
- CAR: test an apples-to-apples small replay case; if impossible, report qualitative comparison and incompatibility, not head-to-head accuracy.

## Acceptance gates for selecting any benchmark

1. Pin upstream git SHA/version, dataset edition, license, access conditions and hashes.
2. Define agent-visible observation, permissible actions, ground truth, scorer and failure-denominator **before** evaluations.
3. Demonstrate zero-label-leak test with evaluator-only files, logs, search index, tool metadata and prompts.
4. Reproduce ≥1 official baseline end-to-end, record its evaluation command and environment; missing capability => BLOCKED with evidence, not fake completion.
5. Demonstrate same tool APIs, intervention executors, timeouts, retry semantics, oracle isolation, information timing and permissions across strategies.
6. Have independent Science Judge sign off on protocol before accessing holdout labels, and Code Judge sign off on reproducibility.
7. Register unavailable/gated/incompatible sources as honest blockers; proceed on other independent tracks rather than waiting.

## Priority for fleet execution

- P0: official benchmark access/contract probes for AgentRx + RCAEval + AIOpsLab in parallel. Decide within a short time box; evidence-based go/no-go.
- P1: RCAEval/AgentRx adapters + official baseline repro, and AIOpsLab controlled reset/intervention-matching feasibility, in parallel.
- P2: pre-register isolated benchmark suites and matched-intervention hypotheses with heldout split hashes, before final outcomes.
- P3: run smoke/pilot, independent judges, then HUMAN-approved final trials.
- P4: honest evidence tables, cluster-level CIs, zero-effect and failure reporting, repeatability packages. No fabricated published numbers.

## Literature review limitations

This is a targeted comparative review of directly relevant open source sources, **not** a comprehensive systematic review. Published benchmark performance is not directly comparable unless dataset edition, split, model, available tools, scoring and run count match. Do not infer that more agents equals a better scientific method. Check source updates during implementation and log them in docs/next_stage/DECISIONS.md.
