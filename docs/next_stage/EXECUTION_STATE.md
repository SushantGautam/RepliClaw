# Stage 2 — authoritative execution state (dev only)

**Timestamp:** 2026-10-09T23:45+02:00 (I0 checkpoint committed; Wave 1 launching).
**I0 checkpoint:** dev @ 5a7833f756119042bbb37bd7479be69a0bd5ea3c (24 files; 301 passed/8 skipped; ruff clean; P08 artifacts untouched). J-CODE conditions all closed in I0 (6 citation fixes, schema hardening F4/F5 with documented dataclass-subset relationship, F6-F8 low fixes, 3 regression tests). J-SCI conditions recorded as D-V3-007 A1-A6 (A2/A5/A6 are freeze-time requirements; A4 goes into C-EQ implementation; A1/A3 go into protocol amendment).
**Development branch:** `dev` (created from public `main` at 97a455947895e48fb551503e8fd1158d03a293af).
**Integration worktree:** `/Users/sushantgautam/Documents/RepliClaw-stg2-dev` (dev @ a8e2b0e725bb6eb1c106d975663c1de0ee188f56).
**Public-facing branch:** `main`; never update without explicit human release approval.
**Current milestone:** C00 DONE (doc QA pending judge reports). **C01 UPSTREAM-PINS DONE pending judge review** (all three tracks pinned + hash-verified). C02 PARTIAL (RCAEval/BARO reproduced; AgentRx judge stage BLOCKED on LLM provider). C03 design drafted (ceq_arm_design.md, not yet implemented). G0 baseline test suite GREEN (296 passed/8 skipped on clean dev; +48 new L6 tests → 306/8 after lane work, ruff clean).
**Experiment authorization:** NOT GRANTED for stage-2 live campaign; G4 cannot pass until specific human approval. No paid/live runs have been launched by any lane.
**V3 protocol:** DRAFT, not preregistered, not approved.

## Wave 0 fleet results (2026-10-09, this checkpoint)
| Lane | Status | Evidence |
|---|---|---|
| L1 AgentRx | G0 DONE / G1 BLOCKED (LLM provider) | contract: adapters/agentrx_contract.md — repo 7a18c797 MIT; **73 annotated trajectories** (44 magentic + 29 tau), NOT paper's 115; 10 canonical categories; 334 failure instances (orchestrator-corrected); dataset hashes verified; judge stage needs Copilot CLI/Azure — unavailable, documented not faked |
| L2 RCAEval | G0 DONE / G1 PASSED | contract: adapters/rcaeval_contract.md — repo 259ea41 MIT; 735 cases confirmed (RE1 375/RE2 270/RE3 90); **BARO reproduced offline**: 10-case RE1-OB cpu pilot Avg@5-CPU 1.0 (chance 0.23, lift 0.77) |
| L3 AIOpsLab | G0 DONE (feasibility) | contract: adapters/aiopslab_contract.md — repo ccf08d0 MIT; 6 mitigation problems FEASIBLE on macOS locally (kind+k8s); hotel-res/astronomy-shop need VM (approval); detection/localization BLOCKED (no intervention actions) |
| L4 C-EQ design | DONE (design only) | design/ceq_arm_design.md — reuses P08 executor verbatim (fairness-critical); one new module ceq.py (~450 LOC); 15 offline tests + 10 cripple-canaries specified; not yet implemented |
| L5 statistics | DONE + verified | science/statistical_protocol_v3.md — case-level paired estimand, cluster bootstrap B=10k PCG64 seed 20261009, percentile 95% CI, ITT, multiplicity, prereg template; reference sim re-runs deterministically (self-test PASSED, orchestrator-verified) |
| L6 infra | DONE + independently verified | src/repliclaw/benchmarks/common/ (4 schemas + records + provenance + resume + dep-free validator); 48 new tests pass; full suite 306 passed/8 skipped; ruff clean |
| L8 novelty | DONE | live-verified prior-art report; ONE defensibly novel claim (matched-tools topology+escrow-ablation protocol on official RCA benchmarks, paired case-level inference — evaluation-methodology novelty); kill-condition recorded; new 2026 threats logged (DeLM 2606.10662, ECLoop 2607.28815, LATS-RCA 2605.03505, MAAC 2601.21972, 2606.22936); AgentRx scale fix 170/115→pin version; full report in L8 agent transcript |
| J-CODE | RUNNING | independent Wave-0 code review in progress |
| J-SCI | DONE (APPROVE-WITH-CONDITIONS) | reviews/SCIENCE_JUDGE_WAVE0_20261009.md — 14 findings; P08 recast check CLEAN; G0 per track: agentrx PASS, rcaeval PASS (heldout must span RE2/RE3), aiopslab PASS-CONDITIONAL (G2 blocked until smoke+digest+live-estimand note); amendments A1–A6 recorded as DECISIONS D-V3-007 |

## Blockers / risk register
- AgentRx official HF data gated; confirm permitted access and release split/count. **RESOLVED (token-scoped read access works; actual release = 73 annotated, not 115).**
- Different public AgentRx release descriptions show two vs three benchmark domains and nine vs ten taxonomy categories. **RESOLVED: 2 domains in release (flash unreleased), 10 canonical categories, normalize_category() authoritative.**
- AgentRx G1 baseline reproduction requires an LLM provider (Copilot CLI quota exhausted; Azure/trapi unavailable). **OPEN — needs human decision: authorize a provider or use the existing sigma2 endpoint if permitted for this benchmark.**
- RCAEval recorded failures are not counterfactual replay. **Documented in contract (observational caveat).**
- AIOpsLab may need Kubernetes/Helm/deployment and safe reset proof. **Feasible locally on macOS for 6 mitigation problems; VM + human approval needed for heavier suites.**
- P08 high accuracies ceiling-saturated on one case; diverse heldout independent cases required.
- Stage-2 provider/token/time/cluster budget unspecified; **do not launch paid/live experiment.**
- AGENTS and fleet instructions on a public `dev` branch are publicly visible to anyone browsing GitHub; never use for secrets.

## First actions for orchestrator
1. Read AGENTS.md and both docs/next_stage/{LITERATURE_AND_BENCHMARK_DECISION,EXPERIMENT_PROTOCOL_V3_DRAFT}.md.
2. Spawn independent read-only L1 AgentRx, L2 RCAEval, L3 AIOpsLab contract probes; L5 science methods; L6 schemas; integrate source pins. **DONE — see Wave 0 table.**
3. Create lane/worktree log; verify baseline official commands and expected exact metric schema; report blockages with evidence. **DONE.**
4. Request approval only for truly necessary paid model/cluster/holdout activity; continue offline parallel work.
5. Update this file at every checkpoint; **do not edit historical P08 artifacts.**

### Next dependency-ready tasks (after judge verdicts land)
- If J-CODE/J-SCI APPROVE-WITH-CONDITIONS or PASS: commit Wave 0 as integration checkpoint I0 on dev.
- L4 implementation ticket: build ceq.py + 15 offline tests per design (Wave 1, unblocked by design doc).
- L1 adapter: read-only AgentRx loader/scorer wrapper (no LLM needed for loader + metric schema); LLM-judge comparison waits on provider authorization.
- Human decision needed: (a) LLM provider authorization for AgentRx official judge stage + any live benchmark runs; (b) AIOpsLab VM/deployment approval; (c) stage-2 budget ceiling.

## P08 historical evidence — must remain unchanged
120 live runs / six arms / one seeded case `policy_rag_v1`; M1 S5/A1/A3=1.00, S4=.20, S0=.15, S3=.05; P1-v1.2 protocol contrast supported but not attribution to decentralization. M3 corrected from 0 to .50; 1,716,411 total tokens; no oracle leak detected. See `docs/experiments/P1_RESULT_STATEMENT_20261009.md`. Historical CI is within-case, not evidence of generalization.

## Milestones
| ID | Status as of document creation | Exit |
|---|---|---|
| C00 Documentation and dev agent rules | DONE for content creation; pending independent doc QA | new dev branch + AGENTS + review + protocol + fleet + seed |
| C01 Upstream version/license/access | **DONE** (pending judge sign-off) | source pins/access/provenance — 3 contracts, SHA+hash verified |
| C02 Published baseline reproduction | **PARTIAL** — RCAEval/BARO reproduced (G1 pass); AgentRx BLOCKED on LLM provider; AIOpsLab n/a until deployment | official executable baseline/scorer |
| C03 Intervention-matched parity | **DESIGN DONE** (implementation NOT STARTED) | dynamic strong central, same causal tools — ceq_arm_design.md |
| C04 Oracle/isolation + reset canaries | NOT STARTED | independent pass |
| C05 Bounded multi-case pilot | NOT STARTED | human scope authorization + exploratory evidence |
| C06 Frozen prereg + approval keys | NOT STARTED | science sign-off + explicit full-run authorization |
| C07 Case-level heldout study | NOT STARTED | case-weighted scores, reproducibility |
| C08 Human-approved main release | NOT STARTED | curated public results |

## Blockers / risk register
- AgentRx official HF data gated; confirm permitted access and release split/count.
- Different public AgentRx release descriptions show two vs three benchmark domains and nine vs ten taxonomy categories. Reconcile exact pinned version, NEVER quietly convert.
- RCAEval recorded failures are not counterfactual replay; data larger than a small smoke; select by predeclared strata.
- AIOpsLab may need Kubernetes/Helm/deployment and safe reset proof; deployment incurs resource cost and needs human approval.
- P08 high accuracies ceiling-saturated on one case; diverse heldout independent cases required.
- Stage-2 provider/token/time/cluster budget unspecified; **do not launch paid/live experiment**.
- AGENTS and fleet instructions on a public `dev` branch are publicly visible to anyone browsing GitHub; never use for secrets.

## First actions for orchestrator
1. Read AGENTS.md and both docs/next_stage/{LITERATURE_AND_BENCHMARK_DECISION,EXPERIMENT_PROTOCOL_V3_DRAFT}.md.
2. Spawn independent read-only L1 AgentRx, L2 RCAEval, L3 AIOpsLab contract probes; L5 science methods; L6 schemas; integrate source pins.
3. Create lane/worktree log; verify baseline official commands and expected exact metric schema; report blockages with evidence.
4. Request approval only for truly necessary paid model/cluster/holdout activity; continue offline parallel work.
5. Update this file at every checkpoint; **do not edit historical P08 artifacts**.
