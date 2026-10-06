# Stage 2 — append-only decisions, amendments, failures and recovery

## D-V3-001 (2026-10-09, proposed design)
Decision: primary research estimand is decentralized escrow pipeline vs **adaptive centralized with the same executable counterfactual tools**, across independent heldout cases. Evidence: P08 S5/A1/A3=1.00, S4=.20, S3=.05; intervention presence explains the result, not autonomy. Alternatives: repeating P08 single-case (rejected), giving only swarm interventions (rejected). Stage-2 V3 prereg remains DRAFT.

## D-V3-002 (2026-10-09, proposed reuse)
Decision: external benchmark tracks are AgentRx + RCAEval observational, AIOpsLab executable/controlled, CAR method comparator only if replay semantics align. ScienceAgentBench verified transfer deferred. No custom dataset unless external benchmark feasibility genuinely fails and Science Judge approves a versioned controlled supplement.

## D-V3-003 (2026-10-09, safe release)
Decision: `dev` holds agent-facing docs, implementation and orchestration. Public-facing `main` receives only explicitly human-approved, reviewed release updates. Dev on public GitHub is still publicly browseable: no secrets/hidden labels/restricted datasets.

## D-V3-004 (2026-10-09, scientific integrity)
Decision: observational traces are not counterfactual experimental runs; intervention tool parity, safe environment reset, evaluator blindness and case-level uncertainty are preconditions for a causal coordination claim. Preserve all null results and legacy P08 data.

## D-V3-005 (2026-10-09T22:50+02:00, Wave 0 integration — orchestrator)
Decision: G0 passes provisionally for all three tracks subject to J-CODE/J-SCI Wave-0 verdicts. Pinned upstreams: AgentRx `7a18c79708e7671be15124460f4f7296107c2a55` (MIT; dataset CC-BY-4.0, gated/auto, token-scoped read verified), RCAEval `259ea4167160256a74ad30004aa3d96a998c846e` (MIT; public), AIOpsLab `ccf08d0d1d5fa5b30f120e2e8549662d44411b35` (MIT). Dataset reconciliation: AgentRx actual release = **73 annotated trajectories** (44 magentic_one + 29 tau_retail), 2 domains (flash unreleased), 10 canonical categories, 334 failure instances (orchestrator re-verified against raw JSONL; contract's original "368" was an arithmetic error and has been corrected). RCAEval 735-case claim confirmed exactly (RE1 375 / RE2 270 / RE3 90). G1 evidence: BARO reproduced offline on a predeclared 10-case RE1-OB cpu stratum (Avg@5-CPU 1.0, chance 0.23, lift 0.77 — treat as an easy-stratum smoke, NOT a generalization claim). AgentRx G1 blocked on LLM provider (documented, not faked). Alternatives considered: bypass gate (rejected, policy), use mirrors (rejected, provenance), remap categories (rejected, V3 rule). Next verification: independent judge reviews (J-CODE 8ee48b9f…, J-SCI 02f27ec8…, L8 novelty 28284cff…). Human authorization needed: (a) LLM provider for AgentRx judge stage / any live runs; (b) AIOpsLab VM/deployment; (c) stage-2 budget ceiling.

## D-V3-006 (2026-10-09T23:10+02:00, novelty gate + protocol amendment — orchestrator, on behalf of L8 report and J-SCI verdict)
Decision: the ONLY defensibly novel claim is the **matched-tools adaptive-central vs decentralized + escrow ablation protocol, evaluated on official RCA benchmarks with paired case-level inference** — an *evaluation-methodology* contribution, not an algorithm. Verified unoccupied in 2025–2026 literature (L8, live-checked arXiv today). Required framing changes (binding on all later docs): (1) "multi-agent hypothesis-competition diagnosis" → "we build on" (LATS-RCA arXiv:2605.03505; AutoScientists arXiv:2605.28655); (2) "pre-outcome forecast commitment" → "we introduce *research-forecast escrow* (hashed packets, phase-boundary sealed reveal, machine-scored accuracy) and MEASURE its effect" (prior owners: arXiv:2606.11217 prereg-for-AI-agents, AutoScientists prediction fields, arXiv:2606.22936 "commitment" vocabulary); (3) "counterfactual causal diagnosis" → "we apply" (CAR arXiv:2606.08275); (4) headline stays on the mechanism (escrow/selection effect on diagnostic quality), NOT on "decentralization wins" (DeLM arXiv:2606.10662 preempts the topology narrative; MAAC arXiv:2601.21972); (5) ECLoop arXiv:2607.28815 added to prior-art table — "evidence" branding must not blur with action-gating; (6) KILL-CONDITION recorded in protocol now: if escrow/decentralization does not change measured diagnostic quality vs C-EQ, the honest title is a negative-result study — no burying. AgentRx citation fix: current abstract says 170 trajectories/11 settings (v1 said 115); accessible release = 73 annotated — pin version in any citation.

## D-V3-007 (2026-10-09T23:10+02:00, V3 protocol amendment v1 — conditions imposed by J-SCI APPROVE-WITH-CONDITIONS)
Amendment to EXPERIMENT_PROTOCOL_V3_DRAFT (draft remains unfrozen; this records the required corrections before freeze):
- **A1 (was F1, HIGH):** "MEANINGFUL_POSITIVE" is renamed a verdict tier with a **minimum effect floor Δ_min predeclared at freeze** (proposed default 0.10 absolute per-case success difference, pending statistician sign-off); below floor with CI>0 = "POSITIVE_SUBTHRESHOLD". A predeclared **HARM_SIGNAL** (upper CI < −Δ_min) may be reported as a true harmful finding — "not established" no longer swallows demonstrated harm.
- **A2 (was F2, HIGH):** Track-I freeze now **requires** a live action-set manifest for AIOpsLab (frozen list of admissible actions, max_steps, escrow-selection→action mapping, reset digest) before any G2 pass. Until then track-I claims are explicitly "offline-fixture only".
- **A3 (was F3, MED):** power derived by **Monte Carlo simulation of the frozen percentile bootstrap** (not two-sided normal approximation); formula N≈7.85σ²/MDE² demoted to a planning heuristic only.
- **A4 (was F4–F6, MED, C-EQ):** manager-consultation channel bounded and logged; token-volume canary made two-sided; D-E round budget explicitly specified so C-EQ's 4-round cap is a matched cap, not a hidden handicap in either direction. (J-SCI note of record: agent-cap asymmetry currently favors C-EQ, not decentralization.)
- **A5 (was F10, MED):** live mitigation problems give ALL arms full causal access — a track-I positive can only claim **selection/coordination** effects, never "access" effects; P08's mechanism (intervention access) does NOT transfer to live track-I and must not be cited as transfer evidence.
- **A6 (was F7, MED):** RCAEval heldout must include RE2/RE3 strata; BARO's 1.0 on the cheapest RE1-CPU stratum is recorded as an easy-stratum smoke, non-generalizable.
Next verification: J-CODE verdict (in progress); both A1–A6 to be folded into the frozen prereg at G4 — no amendments after freeze without versioned record.

## D-V3-008 (2026-10-10T01:35+02:00, power + saturation gate — closes J-SCI A3/F3)
Decision (Monte-Carlo re-derivation of power from the FROZEN percentile bootstrap; 254 cells × 10,000 reps; doc: science/monte_carlo_power_v3.md, SIMULATION-ONLY):
- **Recommended heldout design: N = 24 cases, k = 4 seeds/case, MDE = 0.20** (~84% power). k=2 reaches only 0.555 power; MDE 0.15 is NOT achievable at N=24, k≤4 (needs N≈55) — if the human-approved budget cannot cover k=4, MDE must be re-scoped to 0.20, not silently kept at 0.15.
- **Mandatory S-sat stop rule (supersedes protocol §4.3 judgment trigger):** if at either-arm saturation ≥ 25% of PILOT cases, STOP and re-stratify before any heldout (one-arm saturation at true Δ=0 fires MEANINGFUL_POSITIVE ~83% of the time — the rule cannot separate capability from difficulty exhaustion); joint two-arm saturation erases the contrast (power Δ=0.15: 0.35 → 0.10 as s 0→0.75). Saturation fraction must be disclosed in every result report.
- **Protocol §4.2 two-sided normal-approximation formula is RETIRED** (wrong by ~3.4× in the 0.15–0.20 region; measured effective σ_d ≈ 0.44 vs 0.18 between-case σ). MC simulation of the frozen rule is now the sole power authority. Type-I at Δ=0 measured 0.026 (≤0.05, conservative).
- A1 (J-SCI): the pending minimum-effect floor Δ_min should be set at freeze to a value justified by this MC grid (candidate: 0.15 — below it, the S-sat rule, not the CI, is the operative guard).
Next verification: J-SCI to re-check S-sat rule wording at G4 freeze. Human decision: N=24×k=4 budget authorization.

## D-V3-009 (2026-10-10T02:35+02:00, Wave-1 judge condition triage — orchestrator)
Wave-1 reviews (CODE_JUDGE_WAVE1 + SCIENCE_JUDGE_WAVE1) both APPROVE-WITH-CONDITIONS. Triage:
- **CLOSED in I1.1 (this checkpoint):** F1/S1 (ground-truth service out of agent-visible strata; opaque-id requirement documented in schema + leak test), F3/S3 (template static parts sha-pinned; band [0.6,1.25] calibrated against pin; docstring 0.8→0.6), F2 (forbidden-literal set derived from shared sources), F7 (AgentRx `data_dir` required), S6 (I1 wording corrected), S8 (bit-exact wording scoped), S2 (L5 sha256s + env recorded in MC doc; repo pin deferred to G3 as C-SCI-2).
- **HONEST CAVEAT (S1, G2/G4 gate):** upstream RCAEval case IDs embed the root-cause service (`re1ob_adservice_mem_1`) and data files are named by case id. We cannot fix this; the V3 runtime MUST present opaque random case ids to agents and keep upstream ids evaluator-side only. A2 (live action-set manifest, J-SCI) is still open — Track-I and the RCAEval side of G2 remain blocked until both land.
- **ACCEPTED AS LOW (F4–F6):** timing-vs-content parity nuance and C-EQ/D-E capability deltas (no intervention retry, no per-agent deadline) are disclosed in `design/ceq_arm_design.md`; they do not change the matched-tools claim. F5 helper/test ratio drift folded into the F3 pin.
- **Still open for freeze (G4):** A1 (Δ_min floor from MC grid), A2 (live action-set manifest), A5 (no access-claim drift), C-SCI-1 (scorer-only ground-truth gate), C-SCI-2 (L5 repo pin at G3).
Next verification: G2 offline canaries (Track-II only) on I1.1; independent re-review at G4 freeze.

## Pending decisions
- exact dataset versions, access permissions, stratified splits, license constraints
- AIOpsLab cluster deployment/cost authorization and safe reset support
- detailed sample-size/power from pilot, primary scorer frozen version, number of arms
- exact model/provider, caps, full experimental cost budget, explicit two-key authorization
- when/how a curated public subset may be released to main

## Append future entries
For each: ID, UTC time, proposer, source hashes, issue/failed attempt, alternatives compared, independent reviews, chosen action, scope of prereg amendment, next verification and whether human authorized. Never rewrite an older entry to make a failure disappear.
