# Stage 2 — authoritative execution state (dev only)

**Timestamp:** 2026-10-10T10:10+02:00 (Wave 2 integrated; I2 checkpoint; see bottom section for authoritative current state).
**I1 summary:** dev now contains merged W1 branches: C-EQ arm (`src/repliclaw/experiments/v3/ceq.py` 1113 LOC + 23 offline parity/canary tests, J-SCI A4 closed: bounded logged consultation, two-sided token canary band [0.6,1.25] + anti-starve, explicit D-E round budget; ceq.py-only equivalents of four P08-side behaviors added, each test-pinned — the C-EQ commit touched shared `arm.py`/`runner.py` in a **behavior-neutral** way for P08, token-diff verified, so NO P08 artifact correction is required (J-SCI W1 S6)). AgentRx read-only adapter (73-case hash-pinned loader, verbatim normalize_category, label-free manifest, baseline-agnostic scorer, F8 provenance), RCAEval heldout candidate (42 cases spanning RE1/RE2/RE3, label-mask invariance tested; BARO RE2-OB cpu smoke Avg@5 0.66 vs RE1 1.00 — A6 confirmed: RE2 not saturated), MC power (254 cells × 10k reps: N=24×k=4, MDE 0.20 recommended; S-sat stop rule mandatory; D-V3-008). Integrator mypy sweep fixed 6 type errors in L6 common package (baseline mypy was clean pre-I0; post-I1: 72 files clean). Branch naming convention: `dev-<lane>` or `w1/<lane>` (git ref namespace forbids `dev/` prefix).
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

## Wave 1 fleet results (2026-10-10, I1 @ 99eb764)
| Lane | Status | Evidence |
|---|---|---|
| W1 C-EQ | DONE (merged) | experiments/v3/ceq.py 1113 LOC; 23 offline parity/canary tests; reuses P08 executor; J-SCI A4 closed |
| W1 AgentRx | DONE (merged) | benchmarks/agentrx/ — 73-case hash-pinned read-only loader, verbatim normalize_category, label-free manifest, baseline-agnostic scorer, provenance |
| W1 RCAEval | DONE (merged) | benchmarks/rcaeval/manifest.py + data/cases.parquet (sha256 c49a2889…); 42-case heldout spanning RE1/RE2/RE3, label-mask invariance tested |
| W1 MC power | DONE (merged doc) | science/monte_carlo_power_v3.md — 254 cells × 10k reps; N=24×k=4 MDE 0.20; S-sat stop rule; D-V3-008 |
| J-CODE W1 | DONE (APPROVE-WITH-CONDITIONS) | reviews/CODE_JUDGE_WAVE1_20261010.md — F1 HIGH (root_cause_service in strata), F2/F3 MEDIUM, F5–F8 low |
| J-SCI W1 | DONE (APPROVE-WITH-CONDITIONS) | reviews/SCIENCE_JUDGE_WAVE1_20261010.md — S1 HIGH (ground truth in strata + 6 root_cause.txt), S2 MED (L5 pin), S3 (floor 0.6 vs 0.8 docstring + missing template-SHA pin), S6/S8 LOW; G2 scannable for Track-II C-EQ/D-E, NOT for Track-I (A2) / RCAEval (S1) |

## I1.1 remediation (J-CODE + J-SCI W1, this checkpoint)
- **F1/S1 (HIGH):** `root_cause_service` removed from agent-visible `CaseManifest.strata` (replaced by non-informative `quota_service_order` ordinal). Documented upstream fact: RCAEval case IDs themselves embed the service → `case_manifest.schema.json` note + leak-free test require the V3 runtime to present opaque random IDs. The 6 `root_cause.txt` files live only under `.artifacts/` (gitignored, not in-repo).
- **F3/S3 (MEDIUM):** C-EQ prompt-template static parts extracted as constants + sha-pinned in `test_canary_templates_pinned`; prompt-volume band [0.6, 1.25] now calibrated against the pinned hash; module docstring floor corrected (0.6, not 0.8).
- **F2 (MEDIUM):** no-fixed-script canary `FORBIDDEN_LITERALS` now derived from `load_interventions()` + `DEFECT_TAXONOMY` (all intervention ids + all defect classes, not a hand-maintained subset).
- **F7 (MEDIUM):** AgentRx loader `data_dir` now required (no default-path leak).
- **S2 (MED):** L5/MC scratch-code provenance (sha256 + env) recorded in `science/monte_carlo_power_v3.md`; repo pin (C-SCI-2) is a G3 action.
- **S6 (LOW):** I1 "4 bug fixes in P08 arm code" wording corrected → ceq.py-only; P08 change behavior-neutral (token-diff verified).
- **S8 (LOW):** MC "bit-exact" wording clarified (verbatim L5 + 40-pair twin + judge cell-0 repro; grid reproducible to 3rd decimal).
- **Remaining J-CODE F4–F6 (LOW):** documented as acceptable in review triage (timing-vs-content parity, C-EQ/D-E deltas disclosed in design doc: no intervention retry, no per-agent deadline).
- **Gate:** full suite 352 passed/8 skipped; mypy clean (72 files); ruff clean; schema JSON valid.

**Open items (human decision required):** (a) LLM provider for AgentRx official judge stage; (b) AIOpsLab VM/deploy + budget ceiling; (c) N=24×k=4 heldout budget. **No paid/live work started.**
**Next:** Track-II G2 offline canaries (leak/parity/oracle-isolation/replay) on I1.1 + A2 live action-set manifest (J-SCI condition) → then Wave 2.

## S7 (LOW) RCAEval artifact pointer fix
- Copied the BARO smoke log, 10 per-case result JSONs, and download_manifest.json from the w1-rcaeval worktree `.artifacts/rcaeval/` into the dev worktree `.artifacts/rcaeval/` (gitignored — never committed). The `src/repliclaw/benchmarks/rcaeval/README.md` pointer now resolves in the dev worktree.
- download_manifest.json sha256 = `bffa99801535a029ec6bb5cbc65a2e99e4fe4747514ee7787254133b9e899812` (10 metrics.parquet files, hf://phamquiluan/RCAEval).

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

## Wave 2 checkpoint (I2) — 2026-10-10, authoritative current state
**HEAD:** `ba9bc56` (I2a doc batch) on `dev`. Merges this wave: W2b `a9f353d`, W2c (L5 pin, after a9f353d), W2a `a06f764`, W2g `51ded8b`.
**Gate (post-merge, full):** pytest all green (W2g branch: 367 passed/8 skipped), mypy clean 77 files, ruff clean.

| Worker | Result | Evidence |
|---|---|---|
| W2a G2 canaries | MERGED | 9 pass + 3 documented strict-xfail: (1) oracle-vocab scan is the guarantee — full derived literal set legitimately appears in executor artifacts (files keyed by intervention id); (2) replay byte-identical except `wall_s`; (3) rcaeval manifest module docstring lacks S1 caveat (tracked). Reset behavior pinned: rerun into existing out_root fails loud (DuplicateCommitment), both arms. |
| W2b scorer gate (C-SCI-1) | MERGED | gating.py ScorerContext (audited resolve, caller tags) + heldout_ground_truth evaluator-only helper; 8 tests; synthetic labels only. |
| W2c L5 pin (C-SCI-2) | MERGED | cluster_bootstrap.py byte-identical to scratch (sha256 e14d28ad… verified post-merge); power_pin.py verifier; frozen self-test constant bit-identical under numpy 1.26.4 AND 2.4.6; 5 tests. |
| W2d novelty refresh | RUNNING | report pending (L8 follow-up, 2026-09-01..now). |
| W2e prereg amendments | COMMITTED (I2a) | pure-insertion +34; A1 Δ_min=0.15, A2, A5, D-V3-008 power+S-sat, S1/S4/S7 block, frozen-constants appendix (shas re-verified); 4 conflicts flagged for G4. |
| W2f A2 manifest | COMMITTED (I2a) | 7 actions × 14 problems code-cited @ ccf08d0; explicit_table_lookup_v1; reset digest spec; max_steps 20; VM problems GATED-PENDING-APPROVAL; contract correction (mongodb problems = SocialNetwork, verified auth_miss_mongodb.py:22). |
| W2g SimulaChat (D-V3-010) | MERGED | probe REACHABLE (Qwen3.8-27B, /api/v1); AgentRx adapter + patch, reversible, env-only creds; REAL smoke (contract §10 step 2): 2 tau trajs, 1/2 root-cause correct, 21.4K tokens, every artifact labeled MODEL-SUBSTITUTION (NOT official baseline); secret scan clean; 13 offline tests. |
| J-CODE W2 | RUNNING | independent review of W2a/b/c/g branches + xfail scrutiny. |

**G2 status: PASS-OFFLINE** — Track-II parity/oracle-isolation/replay/reset canaries green; RCAEval-side leak canary green (S1 closed); scorer-only ground-truth gate green (C-SCI-1); A2 manifest frozen (design, no deployment). Track-I LIVE remains human-gated (VM/budget). G3 (bounded pilot) requires: human approval of scope/spend + J-CODE W2 verdict.
**D-V3-010 (human, chat):** SimulaChat default (Qwen3.8-27B) authorized for AgentRx G1 (model-substitution label mandatory) and V3 live arms (arm-identical).
**Still open (human):** (a) AIOpsLab VM/deploy + budget ceiling; (b) N=24×k=4 heldout budget; (c) G3 pilot authorization. **No paid/live work beyond the authorized free SimulaChat smoke.**
**Next:** J-CODE W2 verdict → remediate if conditions → W2d novelty commit → then G3 pilot prep (pilot spec doc, cost estimate at SimulaChat rates, prereg §pilot) — pilot LAUNCH waits on (a)/(b)/(c).

## I2.3 — J-CODE W2 conditions closure (2026-10-10T10:50+02:00)
All J-CODE W2 conditions closed:
- F-W2-1 (CRITICAL→resolved, D-V3-011): pre-existing public URL, zero keys in any branch; G7 re-examination noted.
- F-W2-2 (undo fail-loud/idempotent): FIXED in W2i (826b248), 6 tests.
- F-W2-3 (audit persistence): FIXED in W2j (0fea410), 5 tests + 4 pre-existing mypy errors in gate test also fixed (mypy now clean 78 files).
- F-W2-10 (mechanical label): FIXED in W2i — SimulaChatNotStampedError, env-keyed stamped run dirs, tests-only override.
- F-W2-11 (execution-scope overclaim): FIXED in W2i — contract line struck-through + SUPERSEDED correction (judge + LLM-free IR executed; static/dynamic/check UNEXECUTED).
- F-W2-4 (commit a9f353d says "8 tests", actual 6): commit message cannot be rewritten (history); recorded here as the correction of record.
- F-W2-12 (summary.json zeroes tokens): DEFERRED to G4 doc pass (state.json simula_run_extra is record of truth; note to be added to contract then).
Gate at 826b248: 390 passed/8 skipped/3 xfailed, mypy clean (77 src), ruff clean.

## I2.4–I2.7 — J-SCI W2 fix round + W2k MC re-run (2026-10-10)
**HEAD:** `e1fe19a` on `dev` (merges I2.5/I2.6/I2.7).

| Item | Result | Evidence |
|---|---|---|
| J-SCI W2 report (I2.4, `1b9b953`) | COMMITTED | reviews/SCIENCE_JUDGE_WAVE2_20261010.md: prereg READY for G4 after one fix round (S-W2-1/5/9 + 3 human conflicts); pilot NOT launchable as written (S-W2-2/3/5/6/10); verified 645-disjointness, 2.88M ceiling, wall-time correction 43,200 s/12.0 h, A2 arm-neutrality. |
| W2k rule_a1@0.15 MC (I2.7) | MERGED | 40 cells × 10k reps SIMULATION-ONLY; reproduction of cell 247 EXACT (0.6151/0.6144/θ 0.14917); mid-variance: a1@0.15 power 0.484 @Δ=0.15 (−0.131 vs base), 0.756 @Δ=0.20 (−0.083), type-I 0.009 (floor REDUCES false-fire); doc mc_rule015_sensitivity.md; artifacts preserved .artifacts/statistics/ (json sha256 eda939c3…). |
| W2m prereg fixes (I2.6) | MERGED | S-W2-1 floor gate ADDED (dual stop rule; W2g smoke + P08 S3=0.050/S4=0.200/S0=0.150 cited as capability disclosure; frozen contingency, no silent model switch); 3-sentence model-conditioned results language verbatim in protocol; conflict #1 (ceq §5.3 superset wording, strike-through), #2 (stat §4.2 in-file strike), #3 (0.6 floor STAYS — J-SCI W1 fair-parity rationale recorded); S-W2-7 max_steps semantics sentence in Track-I. |
| W2n A2+provenance (I2.5) | MERGED | S-W2-7 in A2 manifest (orchestrator.py:145/:161 verified @ccf08d0); S-W2-8 exec_shell residual risk + scoped per-namespace SA RBAC pre-flight design (UNTESTED-DESIGN, DEPLOYMENT-GATED; canaries a–d added); S-W2-9 authoring numpy NOT RECORDED flagged + results-JSON sha256 22096e60… pinned. |

**Δ_min status (harmonized):** candidate 0.15 (A1), confirmed-or-lowered-only post-pilot, never raised. W2k result gives the prereg its exact frozen variant: at N=24, k=4, a true Δ≈0.15 effect yields MEANINGFUL_POSITIVE only ~48% (no-sat) — power cost disclosed, coherent with D-V3-008.
**Still open:** W2l pilot-spec fix round (RUNNING); W2d novelty refresh (RUNNING). After both land: I3 checkpoint = G2 formal sign-off + G4 human-decision package (unchanged: (a) AIOpsLab VM/budget, (b) N=24×k=4 heldout budget, (c) G3 pilot launch — plus amendments §4 conflicts now RESOLVED in-file pending human ratification at G4).
**No paid/live work beyond the authorized free SimulaChat smoke.**

## I2.9–I3 — W2l merged, scoreable-pool integrity finding, G4 readiness (2026-10-10T12:25+02:00)
**HEAD:** `38583a2` on `dev` (I2.10). Merges this block: I2.9 `80d2a34` (w2/pilot-fixes).

| Item | Result | Evidence |
|---|---|---|
| W2l pilot-spec fixes (I2.9) | MERGED | S-W2-2 (43,200 s/12.0 h, 44 runs), S-W2-3 (351, not 443), S-W2-4 (per-arm trip prob + coarse-screen sentence), S-W2-5 (Δ_min "confirmed at 0.15, LOWERED only, never RAISED"), S-W2-6 (freeze table current: band [0.6,1.25], C-SCI-2 done, J-CODE W2 cited), S-W2-10 (§5.1 pre-registered difficulty ladder L4–L8 = 44/30/110/22/110 + MAX 2 re-pilots + third trip → INCONCLUSIVE-STRATIFICATION). |
| Scoreable-pool integrity finding (pre-merge, this checkpoint) | RESOLVED + D-V3-012 | Independent recompute on pinned parquet: scorer label = index col `root_cause_service` (all 735 rows, 0 nulls) via manifest.py:234/ScorerContext — NOT the 8 `root_cause.txt` prose files (reps 1–2 RE3-SS only). Draft's availability rationale was factually wrong; wording corrected (`d1bcea3`+`ca118dc`) — reps 1–2 restriction STAYS (deterministic ordering + conservatism; safe: 336 rows/168 strata ≫ n=10+2 re-pilots). All pool numbers re-verified: 645 eligible/168 strata; ladder counts; 42 heldout/18 tuples. Bonus measured fact: case name encodes index-label service in 690/735 (93.9%) — upstream reality, guarantees unchanged (opaque runtime ids + scorer-only gate + manifest hygiene). |
| W2d novelty refresh | ALREADY ON dev (ea7c83c, 2026-10-09, agent e1df7b0a) | PRIOR_ART_NOVELTY_GATE.md: NOVEL WITH DISCLOSURES; CAR (arXiv 2606.08275) added as material prior art for element (b). The "W2d RUNNING" entries above are stale — this commit predates the I2 wave records and was integrated in an earlier pass; no new report pending. |
| Post-merge gate (dev, this checkpoint) | GREEN | pytest: all pass (100%; 3 xfail + 7 skip as before), mypy clean (77 src), ruff clean on src/scripts (repo-root ruff errors are pre-existing at parent commit e1fe19a — not introduced by W2l). |

**G2 formal sign-off: PASS-OFFLINE** (Track-II parity/oracle-isolation/replay/reset canaries; RCAEval leak canary S1; scorer-only gate C-SCI-1; L5 pin C-SCI-2). Track-I LIVE remains HUMAN-GATED (VM/budget). All J-SCI W2 conditions closed (W2k/W2l/W2m/W2n). **G4 (prereg freeze + full-run approval) is READY to request from the human** — decision package:
1. **(a) AIOpsLab VM/deploy budget** — without it Track-I stays out of V3 (design-only, as frozen).
2. **(b) N=24 × k=4 heldout budget** — cost model in statistical_protocol_v3.md; true Δ≈0.15 → MEANINGFUL_POSITIVE only ~48% (W2k).
3. **(c) G3 pilot launch** — 2,880,000-token ceiling, free SimulaChat (Qwen3.8-27B, MODEL-SUBSTITUTION), 10 cases D-E+C-EQ, dual stop rules (ceiling S-sat ≥25% + S-W2-1 floor gate), ladder §5.1, MAX 2 re-pilots, 43,200 s / 12.0 h wall.
4. **Ratifications (in-file RESOLVED, human sign-off needed at G4):** 0.6 prompt-volume floor (conflict #3); pilot spec as amended (I2.9 + I3 ceiling-scope close); token ceiling scope: **per-pilot-round 2,880,000, worst-case campaign total 3 rounds × 2,880,000 = 8,640,000 tokens, $0 on free tier** (spec §5.1, was MISSING-WITH-REASON #2); 2 open pilot-spec notes carried into G4 record (L1–L3 empty-by-anti-leak → L4–L8 takeover at T0).
**Fleet:** all W2 workers idle/complete. No paid/live work beyond the authorized free SimulaChat smoke. Next on human no-op: none blocked on workers — only the (a)/(b)/(c) human decisions above.

## I3.2 — pilot-spec consistency closure (2026-10-10T12:40+02:00)
Direct consistency audit of the G4-bound docs (subagent dispatch hit a 402 quota error; orchestrator executed the checks inline instead — evidence below):
- **A/B (cross-doc rationale):** protocol §disclosure + pilot spec §2/§5.1/§9 all now agree: scorer label = index col `root_cause_service` (735/735); reps 1–2 = deterministic ordering + conservatism, NOT availability. No stale "reps 3–6 lack ground truth" sentence survives in either doc (grep-verified).
- **D (dual gates):** protocol floor gate (S-W2-1, <2/20 run-level OR ≥9/10 per-case all-seeds=0 → MODEL-CAPABILITY-SCREEN-FAILED, heldout canary 6/24 at 25% checkpoint) + ceiling S-sat ≥25% both mandatory. The pilot spec was MISSING the floor gate in its stop rules — ADDED as stop rule 4, verbatim-consistent, with the explicit rule that the §5.1 ladder does NOT run on a floor trip (a floor trip is a capability failure, not stratification).
- **C/E (numbers/scope):** stop rule 3 now unambiguously per-round (2,880,000 resets per round; campaign worst-case 3 rounds = 8,640,000, $0 free tier); human-decision item 2 updated likewise; freeze table row now "Stop rules 1–4" including the floor gate. All other cross-checks (43,200 s/44 runs, ladder 44/30/110/22/110, Δ_min 0.15 lower-only, band [0.6,1.25], 60,000/900 s/4 agents) consistent.
Gate unchanged (docs-only): pytest/mypy/ruff green at b5baba0. Pilot spec is now internally consistent and protocol-conformant — **ready for the G4 human decision package**.

## I4 — G4 met, T0+0..T0+3 (2026-10-10, Track-II-only campaign per D-V3-013)
**HEAD:** see commits below; `dev` (local only; never pushed).
| Item | Result | Evidence |
|---|---|---|
| D-V3-013 (I4.0 `2551244`) | HUMAN APPROVAL | AIOpsLab DECLINED (Track-I out of V3, design-only); heldout N=24×k=4 approved; G3 pilot approved; 0.6 floor + L1–L3-empty ratified. |
| T0+1 telemetry (I4.1 `7d1b868`, I4.2 `a1f35dd`) | DONE | `scripts/rcaeval_pilot_download.py` (id-sha asserted pre-fetch); 32 files / 49 MiB / per-file sha256; manifest pinned `docs/next_stage/data/download_manifest_pilot.json` (RE1-OB ships metrics-only — dataset layout fact, not a defect). |
| Substrate defect + addendum (I4.1) | RESOLVED | Frozen D-E/C-EQ arms run on the SimpleAudit substrate (policy_rag_v1 factors) — NO RCAEval intervention path; Track-I declined. Versioned ADDENDUM `design/v3_telemetry_arm_addendum.md`: access-matched observational arms D-E-TELEM (3 investigators, pre-outcome escrow, committee adjudication) + C-EQ-TELEM (≤4 planner rounds, forecast-before-tools, union view, volume band [0.6,1.25]), one leak-guarded shared sandbox, official service-level accuracy@5 via scorer-only path. Intervention contrast represented by frozen P08 + Track-I design; limitation disclosed verbatim. |
| W3a sandbox `36d77b5` | MERGED | telemetry.py 531 lines; opaque ids RCA-P-01..10 (roster sha-pinned); 5 OBS tools; leak scanner (12 literals incl. all 10 upstream ids); submit-once; 24-call budget; 20 tests. |
| W3b arms `b3ad13a` | MERGED | telemetry_arms.py 1038 lines; LLMToolSession JSON protocol; D-E-TELEM escrow ledger; C-EQ-TELEM loop; volume-ratio parity hook; ArmRunResult; 21 tests; NO GT import (tested). |
| Gate fix (I4.3) | GREEN | static ground-truth caller scan: agent-side docstrings cleared; full suite 454 passed/8 skipped/3 xfailed, mypy 79 clean, ruff clean (new files). |
| W3c BARO feasibility `234b0d2` | DONE | OFFICIAL main.py @259ea41 rcarun venv: Avg@5-DELAY **0.60** ∈ [0.4,0.85] IN RANGE; W1 cpu re-run reproduced **0.66 EXACT** (harness confirmed); 4/4 top-5 hits; spec defect "8 RE2-OB delay" → corrected to 4 (strike-through in spec, artifact pinned). |
| W3d driver `58e66df` | MERGED | `scripts/pilot_run.py` plan/canary/run/status; scorer-side scoring post each arm run; 4 stop evaluators; resume; pre-emptive ceiling; refusals; 12 tests. |
| T0+2 canaries | ALL 5 PASS | both_arms_complete (10 real cases, fake client), payload_parity, scorer_path, label_gate (forbidden literal → crash, not silent), reset. Clean stdout, exit 0. |
| W3e hardening `a033883` | MERGED | canary label-gate crashes demoted (fake-echo confirmed, NOT a real leak; no production payload contains upstream ids); token accounting fixed (O(turns²) history recount → usage/marginal); stderr crash logs; 454 green. |
| T0+3 PILOT RUN | LAUNCH #4 STOPPED — VALID stop-2 trip (see I4.7) | launches: #1 adapter crash (W3f) / #2 re-prompting blowout (W3g) / #3 denominator-defect stop at case 1 (W3h) / #4 on corrected driver → genuine cohort-scale stop-2 (D-E 6/20) at case 3. |

### I4.5 — pilot launch #1/#2 crash diagnosis + W3g harness-side fix (2026-10-11)
| Item | Result | Evidence |
|---|---|---|
| Launch #1 | STOPPED (stop-2 crash) | All runs crashed: `AttributeError: '_Chat' object has no attribute 'create'` — SimulaChatClient exposes `chat.completions.create` (W2g), not `chat.create`. **W3f `e4d60f9`** added `_ChatCreateAdapter`/`_SessionClientAdapter` in `scripts/pilot_run.py` + regression test. Harness bug, NOT a science result. |
| Launch #2 | STOPPED (stop-2 crash, stop-1/3/4 not tripped) | Real MODEL-SUBSTITUTION runs, RCA-P-01 only: 4/4 runs `aborted_budget` at 60,600–64,336 tokens, 22–23 tool calls, ranking=null → per-arm crash 1.0 > 0.25 → stop-2. Cumulative round tokens 250,553 « 2,880,000 (stop-3 not tripped). STOP.json written 16:16:12Z. |
| Root cause (from audit_llm.json, real gateway usage) | FULL-HISTORY RE-PROMPTING, not model weakness | Model behaved correctly: system_context → top_anomalies → one service_metrics per each of 13 services → `commit` as final action. D-E inv-a: 43,343 prompt / 600 completion tokens over 15 calls; C-EQ manager: 52,609 / 480 over 14 calls. Per-service observations only ~180–200 tokens each; the 60K envelope was blown by O(turns²) re-sent transcript billed by the gateway. Spec §4 stop-2 ("60,000 cap structurally too small") premised on post-fix persistence — NOT yet applicable. |
| W3g fix (commit pending) | MERGED-PENDING | `LLMToolSession._compacted_view`: provider send-view keeps system + first instruction + recent 6 verbatim; older tool observations (idempotent, re-fetchable) stubbed ≤120 chars; model responses never compacted. UNCHANGED: 60K envelope, 900 s wall cap, information access, audit transcript (full text), volume canary (self.prompts), 24-call tool budget. New regression test `test_session_compaction_bounds_send_view_keeps_full_audit`. Full suite 455 passed / 8 skipped / 3 xfailed; mypy clean; ruff clean. Addendum §6.3 records the amendment. |
| Smoke (real, RCA-P-01, 2 arms × 2 seeds, ~9 min) | C-EQ COMPLETES / D-E still aborts | Post-W3g: C-EQ manager prompt 52,609 → **44,568** (compaction effective), both C-EQ seeds `completed` at 54,783/54,822 tokens (< 60K) with a coherent adservice-top-5 ranking. D-E still `aborted_budget` (62,058/61,129): compaction helped (inv-a 43,343 → 30,064) but the model's genuinely verbose investigation (re-querying already-seen services, 15–18 calls × 2 investigators, 3rd investigator never scheduled) exceeds the frozen 60K. This is now an HONEST FEASIBILITY SIGNAL for the model-substitution (the §4 stop-2 "structurally too small" branch), not a harness defect — the pilot's stop rules (stop-2 crash, stop-4 floor) are exactly the instrument for it. Max 2 re-pilot counter NOT consumed (smoke = harness verification, case 1 only, no case completed, wiped before full launch). |
| Launch #3 (full) | STOPPED @ case 1 (harness defect) | Wiped smoke, canaries 5/5, `run --round 1 --autonomous` launched 15:45Z. Ran RCA-P-01 on real MODEL-SUBSTITUTION traffic (4 runs) then STOPPED after case 1 with stop-1_ssat + stop-2_crash. **Diagnosis = harness stop-rule denominator defect (W3h), NOT a model/science result** → see I4.6 below. Round-1 budget 2,880,000 consumed 232,726. |

### I4.6 — pilot #3 stopped at case 1: stop-rule denominator defect diagnosed + fixed (W3h) (2026-10-11)
| Item | Result | Evidence |
|---|---|---|
| Pilot #3 real-run (RCA-P-01, 4 runs) | C-EQ completes+HITs; D-E aborts | C-EQ-TELEM: both seeds `completed` (54,717 / 54,721 tokens; manager held under 60K by W3g compaction) with `hit=true` both (adservice top-1 = ground truth). D-E-TELEM: both seeds `aborted_budget` (62,751 / 60,537): inv-a alone used 23 calls / ~60K prompt (system_context 1× + top_anomalies 4× + service_metrics 17–18×); inv-b/inv-c got 0 calls. STOP.json tripped stop-1_ssat + stop-2_crash. Snapshot: `docs/next_stage/data/pilot3_round1_defect_snapshot.json`. |
| ROOT CAUSE | DRIVER stop denominators, not model, not arms | `evaluate_stop_rules` fired on a RUNNING denominator: `sat_per_arm` = sat/recorded-cases (1/1=1.0 ≥ 0.25 trip) and `crash_rate_per_arm` = crashes/ledgered-runs (2/2=1.0 > 0.25 trip). Spec §5 verbatim denominators are the FULL cohort: sat over **n_pilot=10** ("3 of 10"), crash over **20 runs/arm** ("≥ 6 of 20"). Correct values at case 1: C-EQ sat = 1/10 = 0.10 (< 0.25, NO trip); D-E crash = 2/20 = 0.10 (< 0.25, NO trip). Pilot should have CONTINUED to case 10. |
| W3h fix (pilot driver) | denominators corrected to frozen-spec text | `sat_per_arm` → `/ TOTAL_CASES` (10); `crash_rate_per_arm` → `/ (TOTAL_CASES × len(PILOT_SEEDS))` (20). THRESHOLDS (0.25 / 25% / 2,880,000 / floor 2-of-20 & 9-of-10) UNCHANGED; only denominators matched the frozen spec. D-E aborted_budget runs REMAIN crashes in the cohort denominator (signal not softened). Regression: `test_stop_denominators_full_cohort_after_case_1` (exact pilot-#3 state → no trip); existing trip-point tests (`_trip_at_3_of_10`, `_trip_at_6_of_20`) now pin the true trip points; `test_run_fake_artifacts_and_score_schema` updated (single saturated case → pause exit 0). Addendum §6.4 records the amendment. |
| Verification | FULL GATE GREEN | `pytest -q`: all pass; `mypy scripts/pilot_run.py scripts/pilot_report.py`: clean; `ruff` clean. New T0+4 report writer `scripts/pilot_report.py` (spec §5/T0+4: per-arm s + binomial trip prob, σ̂_D, feasibility, ledger snapshot, stop outcomes, NO-effect clause) unit-tested on a synthetic round + run on round1. |
| Re-run consequence | round 1 = harness-defect artifact, discard | No §5.1 re-pilot budget consumed (a ladder rung is only consumed by a GENUINE cohort-scale trip on the fixed checker). Round 1 re-runs fresh. D-E aborted_budget cohort data preserved as legitimate stop-2 input for the corrected run. |

| Launch #4 interim (case 1–2, real traffic) | W3h fix VERIFIED live; genuine crash mode observed | Case 1 completed with `any_tripped: False` (pre-W3h this was the exact point of the false stop). Case 2 shows a GENUINE D-E crash mode: the model emits `"action": "service_metrics"` (missing the `tool_call` discriminator) → 1 protocol error → `status=crashed` (55,271 tokens, 19 calls); D-E crashes are model protocol violations, a legitimate stop-2 input. C-EQ also showed one `aborted_budget` (61,295) — verbose-sweep exhaustion can hit either arm; cohort accounting will tell. Pilot continues autonomously (shellId 1267); expected wall ≈ 10 cases × 4 runs × ~10–60 s. |

### I4.7 — pilot #4 result: VALID cohort-scale stop-2 trip; T0+4 report; both judges clear (2026-10-11)
| Item | Result | Evidence |
|---|---|---|
| Pilot #4 (launch #4, W3h driver, autonomous) | STOPPED after case 3, exit 10, **stop-2_crash TRIPPED (genuine)** | 12 real MODEL-SUBSTITUTION runs (Qwen3.8-27B via SimulaChat). D-E-TELEM: 6/20 = 0.30 > 0.25 (4× aborted_budget + 2× crashed protocol). C-EQ-TELEM: 4/20 = 0.20 (2× aborted_budget + 2× crashed volume-band). stop-1 ok (sat 0.0/0.1); stop-3 ok (663,214 / 2,880,000); stop-4 ok (floor per-arm conjunct 2/6-unevaluable < 2/20 path not hit: D-E 0/6, C-EQ 2/6). STOP.json 16:49:36Z. |
| Crash-cause decomposition (from captured driver stderr, persisted `docs/next_stage/data/pilot4_round1_stderr.log`) | cause-MIXED, not a single model-capability verdict | D-E ×2: `AgentProtocolError: agent 'inv-a': two consecutive malformed action outputs` (model protocol violation). C-EQ ×2: `ValueError: prompt-volume ratio 1.2883/1.2845 outside canary band [0.6, 1.25]` (harness parity canary — a NEW mode seen only now that D-E itself burns ~60K+ and inflates the ratio baseline). 4× aborted_budget: frozen 60K envelope vs verbose sweeps (can hit either arm). |
| Status.json backfill (provenance-labeled) | 4 crashed status.json now carry `crash_error` + `crash_error_provenance` ("recovered post-hoc from captured driver stderr") | Additive field; round pre-dates the `crash_error` field added to `ArmRunResult` this segment (so future runs record it natively). No existing field modified. |
| T0+4 report (pilot_report.py, science-judge Q-D applied) | `round1/pilot_report_round1.json/.md` | Per-arm s + binomial trip P at observed s; crash rate on the FULL 20-run cohort (code-judge running-denominator observation fixed); crashes tabulated BY CAUSE per arm (budget_exhaustion / protocol_violation / volume_canary_harness); verdict line "**TRIPPED**: stop2_crash — FEASIBILITY-FAILED (cause-mixed)"; explicit no-causal-claim note (a majority-protocol attribution would route to the frozen contingency: human decision on a stronger model — spec §5 stop-2 line; NOT a capability verdict here); NO effect estimate / power / superiority clause. |
| Independent code judge (task agent, diff review + targeted tests) | **NO BLOCKERS** — W3g PASS, W3h denominators PASS (exact match to spec §5 verbatim; thresholds untouched; no remaining running denominators in stop decisions), pilot_report PASS (no ground-truth access; binomial verified against spec worked example P(Bin(10,0.20)≥3)=0.32), tests PASS (14/14 driver + 6/6 compaction) | Non-blocker: report running denominator (fixed this segment). |
| Independent science judge (task agent, frozen-spec review) | **NO BLOCKERS** — A (W3h diagnosis) CLEAN; B (re-run legitimacy, no §5.1 cap consumed) CLEAN; C (pilot-#3 evidence = valid feasibility differential; 5 invalid interpretations enumerated) CLEAN-WITH-NOTE; D (cause attribution: spec silent; report must be cause-mixed-labeled, no causal claim) CLEAN-WITH-NOTE → note APPLIED via the report enhancements above; E (still "one pilot" under frozen prereg) CLEAN-WITH-NOTE | Admissibility per frozen spec: stop-2 trip → pilot NOT admissible for heldout launch; stop-2 has NO §5.1 ladder — the verdict is the report + feasibility conclusion. |
| Post-hoc harness field | `ArmRunResult.crash_error: str \| None`; `_record_crash` stores `Type: message`; driver writes it into status.json | Additive (dataclass default None). Full suite green; mypy clean; ruff clean (2 pre-existing E501s in report also fixed). |

**G4 status: MET** (human approval D-V3-013; prereg operative wording = pilot spec freeze table + protocol amendments; final prereg freeze doc still due at T0+6 with data-file hashes + doc sha).
**NEXT = HUMAN DECISION POINT (autonomous action stops here by design):** The G3 pilot tripped stop-2 at cohort scale (D-E 6/20). Per frozen spec this is a FEASIBILITY-FAILED verdict for the MODEL-SUBSTITUTION (Qwen3.8-27B under the frozen 60K/run envelope); the pilot is NOT admissible for heldout launch and stop-2 has no ladder. T0+5 (pilot-σ MC recompute) / T0+6 (final prereg freeze) / T0+7 (heldout, D-V3-013(b) N=24×k=4) are FROZEN pending a human decision among the frozen contingency options: (a) request a human decision on a stronger model (re-run pilot, same frozen instrument), (b) re-scope the envelope/roster via a versioned amendment (new spec amendment + new freeze, NOT silent), or (c) record the negative/feasibility result as the deliverable and stop. Options (a)/(b) would consume real spend — no re-pilot or heldout is launched autonomously. Note for (a): C-EQ completed 2/6 and HIT on the only fully-completed case both seeds; a stronger-model run also needs the two cause-modes watched (protocol robustness; the volume-band canary baseline shifts when D-E burns ~60K).

### I4.8 — re-pilot round 2 (Borealis2-preview) result + W3i caching-investigation closure + judges (2026-10-10/11)
| Item | Result | Evidence |
|---|---|---|
| D-V3-015 | HUMAN APPROVED stronger-model re-pilot (option a) + "full permission" for remaining work | DECISIONS.md D-V3-015. Model candidates probed (`scripts/probe_models.py`, `docs/next_stage/data/model_probe_20261010T184411Z.json`): `Borealis2-preview` PASS (protocol-compliant strict JSON, usage reported, 231 tokens); `glm-5-2-fp8` 401 "api key expired" ×2 (per-model access gate — recorded blocker, not retried further); `autoroute` rejected (non-deterministic router; arm-identical model identity unverifiable — would need versioned amendment). |
| Pre-launch | canaries 5/5 on current driver (post-I4.7 crash_error change) | `canary_report.json` 18:46Z, no_llm_network. |
| Round 2 (12 MODEL-SUBSTITUTION runs, Borealis2-preview) | STOPPED after case 3, exit 10, **stop-2_crash TRIPPED again** (D-E 6/20 = 0.30 > 0.25) | D-E 0/6 completed, all 6 × `aborted_budget` (60,182–64,089 tokens) — **no protocol violations** (Qwen-specific mode did not recur); C-EQ 3/6 completed (54,721–55,108, **hit=true on all 3** incl. RCA-P-03/20261011, a case Qwen crashed on) + 2× aborted_budget + 1× crashed `ValueError: prompt-volume ratio 1.2891 outside canary band [0.6,1.25]` (same structural mode as round 1, same case). 713,441 / 2,880,000 tokens. STOP.json 18:48:02Z. |
| Finding (cross-model, disclosure-level) | D-E protocol violation is MODEL-SPECIFIC (Qwen); D-E budget exhaustion is MODEL-INVARIANT (both models 0/6 under the frozen 60K envelope) — the 60K/run envelope is the structural constraint on D-E, not model protocol quality. C-EQ improves with model strength (2/6→3/6, 3/3 hits) but one structural canary crash (case RCA-P-03, ratio ≈1.29 both models). NO effect estimate / no superiority claim (frozen clause). | Round 1 + round 2 reports + ledgers. σ̂_D = 1 in both rounds (RCA-P-01, C-EQ-only saturation). |
| T0+4 report round 2 | `round2/pilot_report_round2.json/.md` (regenerated after label fix) | Report model label now derived from actual per-run status.json (round 1 = Qwen3.8-27B, round 2 = Borealis2-preview — a prior report-generation bug hardcoded round 1's label; fixed + both reports regenerated + gates green). |
| Re-pilot authorization | **CONSUMED (1/1 per D-V3-015 option-a read)** | Correcting the earlier "2/2" entry: the frozen §5.1 "MAX 2 re-pilots" cap governs the **S-sat difficulty ladder only** (spec §5.1: "On an S-sat trip … re-pilot on the next ladder rung"); stop-2 has **no ladder** (frozen D, I4.7), so D-V3-015's option (a) — "re-run the pilot once under the SAME frozen instrument" — authorized exactly one re-pilot, and round 2 consumed it. Either reading, no further autonomous re-pilot is authorized. |
| Judge — code (98e62b1e) | **PASS, no blockers** | 5/5 questions: label derivation clean + both reports correct; no credential leak in probe output; stop arithmetic exact (6/20, 3/20, 713,441; ledger↔status tokens 12/12); stop-4 correctly unevaluable (per-arm 20-run conjunct at 6 runs); cross-round invariants hold; gates green. Non-blockers: mixed-model label drops per-model strings (low risk); probe output embeds raw provider error strings (low risk); UTC vs +02 timestamp conventions mixed. |
| Judge — science (f7542a77) | **Q2/Q5 BLOCKER (now resolved, see W3i row); Q1/Q3/Q4/Q6 CLEAN-WITH-NOTE** | Q1 re-pilot lawful under D-V3-014 frozen contingency (not a §5.1 ladder rung). Q3: (a) 60K-structural finding VALID, (b) Qwen-protocol finding VALID as disclosure only, (c) robustness finding VALID but ANY "C-EQ > D-E" superiority claim is FORBIDDEN, (d) "a stronger model would make D-E feasible" NOT SUPPORTED by round 2 (still 0/6!), (e) "3/3 hits" not a valid accuracy claim (n=3, ITT n=6). Q6 minimal amendment set for option (b) if chosen: per-investigator envelope ~90K justified from observed near-cap; freeze canary-baseline definition when D-E aborts; floor gate unchanged; pre-freeze sha + goalpost guards; no confirmatory reuse. |
| W3i — caching-investigation (science-judge BLOCKER closure) | **C1 REFUTED as stated; C2 downgraded to bounded NOTE** | Science judge's BLOCKER: R2 C-EQ P-01 cells cross-round byte-identical token totals + near-identical manager responses → suspected undisclosed caching/replay. Investigation (persisted: `docs/next_stage/data/w3i_caching_investigation_20261011.json`): E1 no client-side cache (simula.py code); E2 identical token totals are the **deterministic length-estimate fallback** (chars//4) on byte-identical deterministic sandbox prompts, 14 identical calls — expected arithmetic, not replay; E3 strict content diff: 12/14 responses identical both seeds, 2/14 genuinely differ per seed (explains the judge's "26/28": identical short JSON actions on deterministic data at temp 0.2); E4 faithful live replays of the R2-1011 view: Qwen reproduces R1's original EXACTLY, Borealis returns a DIFFERENT answer → prompt-keyed replay layer REFUTED; E5 backends demonstrably distinct (temp-1 divergence; identity probe: Borealis2-preview **self-identifies as Qwen3.8-27B** — treat as Qwen-base-class variant, NOT an independent frontier model); E6 **RESIDUAL (bounded)**: the live R2 C-EQ P-01/20261011 commit matched Qwen's R1 answer exactly while 0/14 controlled Borealis replays matched it — one cell carries a contamination caveat (likely transient auto-fallback / heterogeneous worker); R2 P-01/20261012 and P-03/20261011 are live Borealis-class; E7 D-E arm shows no caching signature (all runs tok-diff, low response identity) — **the D-E 6/20 budget-exhaustion finding is unimpaired**. Verdict: BLOCKER closed as CLEAN-WITH-NOTE + disclosure: (i) round-2 evidence is a same-base-variant (Qwen-base-class) instrument re-test, NOT a test of a demonstrably stronger model — the D-V3-014 option-(a) premise remains untested by a genuinely stronger model (glm-5-2-fp8 access-blocked 401); (ii) one C-EQ cell flagged. The R2 report's "MODEL-SUBSTITUTION (SimulaChat Borealis2-preview)" label is retained but the state record now carries the variant caveat. |
| T0+5 + T0+6 (stats-worker 0864f806) | DELIVERED (pending orchestrator verification commit) | T0+5: `scripts/t05_pilot_sigma_mc.py` — MC power grid at pilot-estimated σ̂_D per frozen protocol; on round-1 data emits the deterministic INSUFFICIENT-ESTIMATE artifact (3 paired-contrast cases < 8 minimum, spec §2 fallback — nothing fabricated); reproduction gate exact match. T0+6: `docs/next_stage/design/v3_prereg_final_freeze.md` DRAFT (orchestrator stamps freeze only at T0+6 after human G4); all embedded hashes verified zero mismatches. Gates green on its changes. Flag: operative T0+5 cells need numpy 1.26.4 (venv has 2.4.6). |

**NEXT = HUMAN DECISION POINT #2 (D-V3-015 does NOT authorize it; frozen instrument):** both pilots tripped stop-2 at cohort scale on their respective models; the one D-V3-015 re-pilot is consumed. Heldout (T0+7) is NOT admissible (frozen rule: launch only if a pilot completes without a mandatory stop trip). **Both option deliverables are now fully drafted, ready for one-word approval:**
- **(b)** `docs/next_stage/design/amendment_v31_pilot_envelope_DRAFT.md` — AMEND_V3_1_PILOT_ENVELOPE, exact minimal set (A1: 60K→90K per-run envelope, evidence-justified from observed near-cap aborts 60,182–64,089; A2: frozen canary baseline — ratio not computed / run not crashed when the D-E partner is non-completed, unchanged otherwise; A3: round ceiling 2.88M→4.32M (=48×90K); A4: `backend_model` provenance field from gateway echo, W3i-immunity). Goalpost guards listed; execution surface (code+tests+freeze+pilot V3.1 on free endpoint) specified; approval record block included.
- **(c)** `docs/next_stage/g3_pilot_outcome_statement.md` — the honest G3 record-and-hold deliverable: FEASIBILITY-FAILED cause-mixed (envelope structural + canary interaction + Qwen-protocol model-specific), round ledger exact, anti-claim list, negative finding preserved, evidence pointers.
- **(d)** New-spec next pilot — meaningful only with a genuinely stronger model (GLM-5.2 key currently 401 expired) or new scope.

**RESOLVED (D-V3-016, 2026-10-10T21:36+02:00, human via chat):** **b + c APPROVED, d NOT.** (c) `g3_pilot_outcome_statement.md` stands as the G3 record for the frozen V3 instrument (committed; retained either way). (b) executes now under AMEND_V3_1_PILOT_ENVELOPE (approved, **A2 REPEALED at approval** — the draft's D-E-partner mechanism claim was verified false from audit data + code; the volume canary is a legitimate C-EQ-internal fairness guard and stays unchanged per the human's binding model-fairness clause). Pilot V3.1 model pinned to SimulaChat `default` (Qwen3.8-27B echo), unlimited spend within the approved 4,320,000/round ceilings. Full record: DECISIONS.md D-V3-016.

## V3.1 implementation (I4.9) — code complete, gates green, pending freeze + canaries
- **Code (integrator, verified):** A1 `MAX_TOKENS_PER_RUN` 60,000→90,000 (telemetry_arms.py, shared by both arms; `_Envelope` default now reads the shared constant lazily + rejects any explicit value above it — the A1 parity guard, making per-arm divergence a runtime error per the D-V3-016 fairness clause); A3 `ROUND_TOKEN_CEILING` 2,880,000→4,320,000 (pilot_run.py + pilot_report.py, mechanical 48×90K); A4 `backend_model` provenance — `LLMToolSession.record_backend_model()` captures the gateway-echoed `response.model` on the first LLM response, aggregated per-agent into `ArmRunResult.backend_models`, written to status.json. **A2 repealed: no canary change** (band 0.6/1.25 + crash-on-violation unchanged; verified P-03 crash mode is case-intrinsic C-EQ volume 1.284–1.2895, D-E not in the denominator).
- **Tests:** new — `test_v31_amended_envelope_constants`, `test_v31_envelope_parity_guard` (A1), `test_v31_backend_model_provenance_recorded` (A4), `test_v31_canary_invariance_after_envelope_amendment` (A2-repeal guard); updated — D-E token-budget test to 90K, driver stop-3 arithmetic to 4.32M/90K, new `test_v31_amended_constants`. P08 surface untouched (still 60K literals, separate frozen instrument).
- **Gates:** full pytest **462 passed / 8 skipped / 3 xfailed** (457 baseline + 5 new/updated); mypy telemetry_arms.py clean; ruff src+scripts+tests clean.
- **Freeze:** `docs/next_stage/design/v31_prereg_freeze.md` stamped (pre-freeze `dev` @ `e602041f…`, constant file hashes, full unchanged-vs-amended table, launch protocol, non-authorizations).
- **Offline canaries (V3.1 instrument):** 5/5 PASS — `.artifacts/v31_canary_offline/canary_report.json` (both_arms_complete, payload_parity, scorer_path, label_gate, reset).
- **Live canary (real `default` traffic, RCA-P-01, 4 runs, will be WIPED pre-launch):** GATEWAY/ECHO VERIFIED — every LLM response echoes `Qwen3.8-27B`; A4 `backend_model` populated per agent in status.json (3rd D-E investigator `None` = never scheduled, correctly null); C-EQ both seeds `completed` at 54,717/54,719 tokens (same regime as round 2); D-E both seeds `aborted_budget` at **91,734 / 90,842** (now exceeding the 90K envelope cleanly — confirms A1 lifted the round-2 60K truncation; D-E remains budget-bound, model-invariant finding holds); no stop trips (canary scope only).
- **Judges (IN-FLIGHT → RESOLVED):** code-judge-v31 (4f5733ba) **PASS, no blockers** (6/6 questions: A1 parity + guard, A3 consistency, A4 side-effect-free + no audit/token-accounting leak, A2 repeal byte-verified, tests non-vacuous, suite 462 green; 3 non-blocking docstring hygiene fixes). science-judge-v31 (a8f6cafc) **PASS — 3 CLEAN, 2 CLEAN-WITH-NOTE, 0 CONCERN, 0 BLOCKER** (Q1 fairness CLEAN; Q2 A2 repeal CLEAN-WITH-NOTE N1 calibration disclosure; Q3 pre-record CLEAN-WITH-NOTE N2 corrections; Q4 provenance CLEAN-WITH-NOTE N3 heldout echo rule; Q5 no retroactive rewrite CLEAN). **BOTH NON-BLOCK → launch gate satisfied.**
- **Judge-fix remediation (I4.9b):** 3 docstring hygiene fixes (code-judge) + freeze-doc pre-record corrected per N2 (aborted_budget IS a stop-2 crash; P-03 already crashed at 60K — 90K-induced transition is P-02 only, ratio is a projection; 90K is neutral-to-favorable for C-EQ) + N1 calibration disclosure + N3 implemented: `pilot_report.py` now emits `backend_model_echoes` (per-run, per-agent gateway echoes) + `backend_echo_inconsistent_runs` (within-run cross-agent consistency check) + heldout-mandatory note; new test `test_report_backend_echo_provenance` (consistent + inconsistent cases). Verified live on canary round (4/4 runs, 0 inconsistent) and round-2 data (field absent → empty, label derivation intact). Gates: **463 passed / 8 skipped / 3 xfailed**, ruff + mypy clean.
### I4.10 — PILOT V3.1 ROUND 3 EXECUTED: stop-2 TRIPPED (D-E 6/20), feasibility verdict for D-E is now triply confirmed
| Item | Result |
|---|---|
| Run | Launched after both judges PASS + canary wipe; autonomous; model `default` (all 12 status.json echo `Qwen3.8-27B`, 0 inconsistent runs); stopped after case 3 (RCA-P-03), exit stop-2. Evidence: `.artifacts/rcaeval/pilot/run_v31/round3/` (STOP.json, ledger, per-run status, T0+4 report). |
| Ledger (12/20 runs) | D-E 0/6 completed: 3× `aborted_budget` at **90,710 / 92,599 / 92,847** tokens (still exceeding the NEW 90K envelope — ~1–3% over), 2× `ToolBudgetExhausted` (24-call cap, at 70,417/83,642) — **newly surfaced in R3** (absent R1/R2; deterministic resource-cap failure, not a harness defect; a second binding constraint on D-E per science-judge-r3), 1× `AgentProtocolError` (inv-a malformed ×2, 46,348). C-EQ 4/6 completed: **4× hit=true** (P-01/1011, P-01/1012, P-03/1011, P-03/1012 — verified against all four score.json; earlier "3 hits" was an integrator misread, corrected per judge) + 2× crashed `prompt-volume ratio 1.3476` on **RCA-P-02 both seeds** — the N2 pre-recorded 90K-induced transition, exactly as flagged. |
| Stop values | stop-2 D-E 6/20 = 0.30 > 0.25 **TRIPPED**; C-EQ 2/20 = 0.10 not tripped (the unchanged canary crashed 2 C-EQ runs — stop tripped on D-E alone). stop-1 sat 0.0/0.2 not tripped; stop-3 815,858/4,320,000 not tripped; stop-4 floor unevaluable (1 allzero case < 9). |
| Cross-round structural finding (disclosure-level, no superiority claim; judge-refined) | D-E infeasibility: 0/6 completed in all three rounds (R1 4 budget + 2 protocol; R2 6 budget at 55–64K; R3 3 budget at 90.7–92.8K + 2 tool-cap + 1 protocol) — **multi-resource**, not single-envelope (token budget AND 24-call tool budget both bind in R3), and "model-invariant" is precisely **same-Qwen-family-invariant** (two same-family variants tested; no genuinely stronger/different-family model was ever testable — glm-5-2-fp8 401). C-EQ is envelope-comfortable (52–55K), **4/4 hits** on completed runs (3 distinct cases, P-03 both seeds), but carries one case-intrinsic canary exceedance per case (P-02 @ 1.3476 at 90K; P-03 @ ~1.289 at 60K). **Fairness disclosure (science-judge-r3 Q2):** the 6:2 D-E:C-EQ non-completed gap is partly an artifact of the C-EQ-internal canary's contested calibration (N1) — stop-2 tripped on D-E alone, which is fair and canary-independent, but any envelope raise or band recalibration must first show the human this asymmetry. The original mission question (value of decentralization/escrow beyond intervention access) remains UNANSWERED — no round has both arms simultaneously feasible. |
| Provenance | N3 field live in round-3 report: `backend_model_echoes` 12/12 runs, `backend_echo_inconsistent_runs` = []. |
| Protocol position | Frozen: stop-2 has no ladder; D-V3-015 re-pilot consumed; this was the D-V3-016 instrument. **No further autonomous runs authorized.** → HUMAN DECISION POINT #3. |
| T0+4 report | `round3/pilot_report_round3.json/.md` (label MODEL-SUBSTITUTION (SimulaChat default, Qwen3.8-27B); 815,858 tokens; D-E causes 3 budget/2 tool-cap/1 protocol; C-EQ 2 canary). |
| Judge — code (2c80d578) | **PASS both (a) accept round 3 as valid feasibility record, (b) route to human** | 6/6 questions: stop arithmetic exact (6/20=0.30 D-E tripped, 2/20=0.10 C-EQ not; stop-1/3/4 correctly not tripped); cause decomposition matches report crashes_by_cause exactly; 1.3476 P-02 matches N2 pre-record, no unexpected crash modes; N3 12/12 echoes consistent; instrument byte-identical to frozen I4.9b (all 4 file hashes match); canary wipe verified; suite 463 green. Note: code-judge's "3× hit=true" was an undercount — ground truth is 4/4 (all four score.json verified). |
| Judge — science (a910b114) | **RECORD-AND-HOLD recommended; 2 CONCERN (refinements, not invalidations), 2 CLEAN, 1 CLEAN-WITH-NOTE** | Q1 CONCERN: "envelope-structural" valid in outcome but D-E's constraint is MULTI-RESOURCE (token + tool budget both bind in R3 via newly-surfaced ToolBudgetExhausted); the "just raise the envelope" forward inference is NOT supported — the 24-call cap aborted 2 of 6 D-E runs at 70–84K tokens, i.e., BELOW any token envelope that fixes the 91–93K aborts. Q2 CONCERN: stop-2 verdict is fair + canary-independent (tripped on D-E alone), but the C-EQ-internal canary (N1 contested calibration) distorts the apparent 6:2 gap — human MUST be shown this asymmetry before any envelope raise or recalibration. Q3 CLEAN: mission question UNANSWERED is the correct honest status; no-confirmatory-reuse verified. Q4 CLEAN-WITH-NOTE: `default`+echoes adequate for same-family treatment; token-parity with R2 weaker than it looks (deterministic length-estimate fallback, not provider usage). Q5 CLEAN: routing to human is correct AND only lawful step. Recommended: (i) record-and-hold NOW with the R3 corrections; a both-constraints V3.2 (higher token envelope AND tool-budget change, + canary recalibration) is the only path to the mission question but is high-risk and still non-confirmatory; baseline pivot as fallback. |
| Judge record corrections applied | C-EQ hits 3→**4** (score.json ground truth); "no new crash classes" → ToolBudgetExhausted newly surfaced in R3 (deterministic, second binding constraint) | Both recorded above before the decision point. |

**NEXT = HUMAN DECISION POINT #3 (frozen protocol; both judges PASS the record + routing):**
- **(i) RECORD-AND-HOLD (science-judge recommended):** extend `g3_pilot_outcome_statement.md` with round 3 as the final feasibility record (D-E infeasible = multi-resource: token envelope + 24-call tool budget, same-Qwen-family-invariant; C-EQ 4/4 hits when completing + canary constraint; mission question unanswered). Free, zero further runs.
- **(ii) NEW V3.2 instrument (only path toward the mission question, high-risk, still non-confirmatory):** human-approved amendment addressing BOTH binding constraints (token envelope to cover observed 91–93K demand + headroom, AND the 24-call tool budget) + formally re-justified/recalibrated C-EQ volume band (N1) — the asymmetry disclosure above must be acknowledged in the approval. Free endpoint; per-round ceiling scales with the new envelope.
- **(iii) STOP the pilot track; pivot remaining effort** to the AgentRx / RCAEval literature-standard baselines (official benchmarks, published baselines) as the deliverable path.
FORBIDDEN after round 3 (frozen + judges): any effect estimate or C-EQ>D-E superiority claim; any "decentralization/escrow adds value" claim; treating rounds 1–3 as confirmatory or heldout evidence; "a stronger model would make D-E feasible" (untested — no different-family model was accessible); C-EQ "4/4 accuracy" as a generalization claim (3 distinct cases, ITT 4/6).
- **Pre-recorded honest expectation (disclosure, NOT a forecast of the verdict):** at 90K, C-EQ on RCA-P-02 (ratio ~1.33-1.35) and RCA-P-03 (~1.29) that previously budget-aborted before the canary may now reach it and crash — counted ITT per frozen stop-2.

## I4.11 — V3.2 implemented, judges PASS, live canary: D-E STILL infeasible at 150K/48 (2026-10-11)
- **Code (commit 2082640, LOCAL-ONLY dev):** B1 150K/run, B2 48 tools, B3 band 1.40, B4 7.2M ceiling; NEW `scripts/pilot_parallel.py` (threads, concurrency 6, atomic stop-claim, TOCTOU-safe pre-claim ceiling gate, rc==10 stop-trip propagation, parallel provenance + parallel_meta.json); `perform_case` lock param (sequential unchanged); pyarrow `_PARQUET_READ_LOCK` (science-judge C1) + concurrency regression test. P08 surface untouched (60,000 verified).
- **Gates:** 467 passed / 8 skipped / 3 xfailed; ruff + mypy clean; offline canaries 5/5.
- **Judges (post-fix, both PASS):** code-judge — SHOULD-FIX #1/#2 + C1 lock + freeze hashes all verified, no new blockers (4 informational launch notes: uncommitted freeze doc → now committed; driver-failure ledgering; trip_info last-write-wins benign; ceiling gate non-binding this round). science-judge — C1–C5 all SATISFIED; pyarrow venv is 26.0.0 (19.0.0 discrepancy recorded in DECISIONS.md); **LAUNCH-WITH-CONDITIONS** (4 documentation conditions: canary disclosure item [added to freeze stamp], driver docstring fix [deferred post-round, file kept frozen-hash-identical], pyarrow note [recorded], T0+4 per-sandbox repeated-call decomposition [noted]).
- **LIVE V3.2 canary (run_v32_canary/round0, RCA-P-01, model `default`, SIMULACHAT_MODEL unset, 12/12 backend_model echoes Qwen3.8-27B, cumulative 413,104/7.2M):**
  - C-EQ-TELEM: completed both seeds (54,759 / 54,721 tok, 10 tools, 17 llm, ratio 1.235/1.233, hit=True both, scorer_sha a8c545f2…).
  - D-E-TELEM: **aborted_budget both seeds (152,824 / 150,800 tok, 53/50 tools, 60/55 llm, no submission)**. Both phase-1 escrow commits present; phase-2 synthesis never reached.
  - **KEY NEGATIVE FINDING (multi-case-validated pattern):** D-E fails via a non-convergent repeating-tool-call loop (inv-b: 28 llm / 22 service_metrics calls; repeated top_anomalies/service_metrics verbatim), NOT a single-point budget wall. 150K/48 is NOT enough. **Round 4 will very likely trip stop-2 (or stop-1) after 3–4 D-E non-completions → pre-registered feasibility-only negative.** Confounding disclosure added to freeze stamp (decentralization overhead vs per-agent non-convergence composite; attribution post-hoc from audit_sandboxes.json).
- **Freeze:** `docs/next_stage/design/v32_prereg_freeze.md` stamped at 2082640 (5 file hashes verified by both judges), 7-item disclosure list, launch protocol, non-authorizations.
- **Next (launch sequence):** commit freeze + state → launch round 4 via `pilot_parallel.py run --round 4 --out .artifacts/rcaeval/pilot/run_v32 --autonomous --concurrency 6 --label "..."` (SIMULACHAT_MODEL unset) → on completion/trip: T0+4 report (pilot_report.py) with required decomposition → both outcome judges → state/PROGRESS → checkpoint.

## I4.12 — Round 4 EXECUTED: tripped stop-1 + stop-2 at 16/40 runs (2026-10-11) — HUMAN GATE
- **Launch:** commit e770c06, all 5 frozen code hashes verified identical to v32_prereg_freeze.md; SIMULACHAT_MODEL unset; model `default` (12/12 canary echoes Qwen3.8-27B); parallel driver (threads, concurrency 6); label MODEL-SUBSTITUTION. Evidence: `.artifacts/rcaeval/pilot/run_v32/round4/` (parallel_meta.json, STOP.json, 20 per-run dirs, T0+4 report pilot_report_round4.json/.md).
- **Outcome: STOP (exit 10) — stop1_ssat + stop2_crash** written after the 16th ledger line (cumulative 1,132,481/7,200,000 tokens, ~2 min — cumulative at STOP time, verified: sum of ledger lines 1–16). Four in-flight D-E runs finished after the stop decision (design: in-flight runs complete and are recorded) → ledger has **20 lines total (1.74M)**, 20 per-run dirs. Stop-2 tripped on D-E alone: at trip time D-E 8/20=0.40 > 0.25; C-EQ 5/20=0.25 is NOT > 0.25 (strict inequality — the `stop2_crash.tripped=true` in STOP.json reflects any-arm semantics, D-E was the tripping arm; code-judge-r4 is recomputing to confirm). Per D-V3-017 governance: "on any stop trip → human again." **All further runs are PAUSED pending human decision.**
- **Cause decomposition (disclosure item 7 evidence):**
  - **D-E 0/12 completed (100% infeasible, 6 cases × 2 seeds; final ledger includes all 12):** 8/12 `aborted_budget` at 151.7K–154.2K tokens / 43–49 tools (non-convergent repeating-tool-call loops — per-sandbox audit shows inv-a/b repeating IDENTICAL service_metrics calls 2–4×, inv-c sometimes 0 tools); 4/12 early crashes (2× `AgentProtocolError: inv-a two consecutive malformed action outputs`; 2× per-tool sub-budget exhaustion `service_logs`/`service_traces` at 4 calls — B2 raised the total to 48 but per-tool caps stayed at 4). Multi-resource infeasibility confirmed: token wall + tool-loop pathology + per-tool caps all independently bind.
  - **C-EQ 3/8 completed, 5/8 CRASHED BY THE B3 CANARY BAND (instrument artifact):** live ratios 1.711/1.732/1.787/1.803/1.601 vs 1.40 ceiling. Same case/seed/arm that COMPLETED in the canary at ratio 1.235 (RCA-P-01/s20261011) re-ran at 1.601 → **the volume ratio is non-deterministic run-to-run under the live model** (manager prompt accumulation scales with model output length), so the crash-on-violation band fails the CONTROL arm. The 3 C-EQ completions: all hit=True (P-02 1.348, P-03 1.226, P-04 1.336).
- **Feasibility-only negative (NO effect estimate, per pre-registration):** D-E-TELEM does not complete within 150K/48 on any case (0/12 across 6 cases × 2 seeds); C-EQ-TELEM completes when the volume canary does not trip (3/3 completions hit=True). Both arms are currently infeasible — for DIFFERENT reasons (arm pathology vs instrument over-sensitivity). This extends (does not overturn) the prior finding of no demonstrated decentralization/escrow advantage.
- **Pending:** two independent outcome judges (dispatched on committed state I4.12); human decision on next step — options on the table: (a) accept the negative as the V3 campaign result and close out; (b) new V3.3 amendment (human approval required): e.g. de-escalate B3 from crash-gate to logged-canary for the control arm, raise/replace per-tool sub-caps, and/or dedupe repeated identical tool calls (anti-loop guard) for D-E — each a new frozen instrument with fresh preregistration + judge review; (c) change model (not authorized — `default` only per D-V3-017).

## I4.13 — Round-4 outcome judges BOTH returned; defect fixes applied (2026-10-11)
- **Science judge (round-4 outcome):** PASS on execution integrity (frozen hashes verified; halt per protocol; no fabrication); **FAIL-WITH-DEFECT on stop-1 computation**; RECOMMEND (b) minimal V3.3 amendment. Key: stop-1 co-trip was a FALSE trip (seed-level running-denominator defect in `arm_saturated`; spec-correct sat = 0.0; stop-2/D-E 0.40 is the sole valid trip). D-E's decentralized mechanism (phase-2 commit-reveal, phase-3 committee) NEVER executed in any of the 12 D-E runs — 48.1% of all 378 D-E tool calls were identical (tool,args) repeats; token-burn split ~60–75% agent non-convergence, ~0% genuine decentralization overhead. C-EQ band crashes = instrument over-sensitivity (P-01 same case/seed 1.235→1.601 proves live-model variance > the 0.05 B3 margin); the crash-gate is control-only and biases any D-E-vs-C-EQ contrast IN FAVOR of D-E. Added disclosures 8–11 (stop-1 defect; STOP.json 16/20 snapshot gap; phase-2/3 never executed; asymmetric volume gate).
- **Code judge (round-4 outcome):** **PASS — evidence ADMISSIBLE** for the feasibility-only negative. Refuted the stop-2 mislabel (D-E 0.40 tripped; C-EQ 0.25 correctly did not, strict `>`). Spend: 1,132,481 at stop time (lines 1–16) / 1,744,526 final (20 lines), both < 7.2M. Envelope overshoot bounded by one LLM call (check-after-respond). 20 status.json ↔ 20 ledger lines, 0 dups, 0 ground-truth leaks in D-E transcripts, score.json in exactly the 3 C-EQ completions. SHOULD-FIX: no STOP.json resume guard (both drivers).
- **Defect fixes applied (commit 57d1e1f, NOT a scientific amendment):** (1) `arm_saturated` now requires all k=2 seeds recorded+successful (regression tests: one-seed not saturated / two-seed still trips at 3/10); (2) STOP.json closed-round guard in BOTH drivers (regression tests both). 471 passed / 8 skipped / 3 xfailed, ruff + mypy clean. Round-4 evidence + V3.2 freeze UNCHANGED.
- **Human gate (per D-V3-017, stop trip → human).** Options: **(a)** accept the round-4 negative as the V3 campaign result and close out; **(b)** authorize V3.3 minimal amendment (new prereg + 2 fresh judges + new freeze + human approval): B3→logged canary (drop crash, keep measurement), symmetric anti-loop cache in both arms' sandboxes, per-tool sub-caps→total-budget-only, (seed-saturation fix already applied as a code defect). Model stays `default`; no-confirmatory-reuse preserved. **(c)** model change — NOT authorized per D-V3-017.

## I4.14 — Final disclosures 8–11 recorded (2026-10-11)
Any report or claim citing round 4 must carry these (beyond the 7-item freeze-stamp list):
8. **Stop-1 miscalculation:** stop-1's trip is a seed-level saturation implementation defect (0.30 from 3 one-seed C-EQ successes; spec-correct sat = 0.0). The halt is justified by stop-2 (D-E 0.40) alone. (Defect now fixed at 57d1e1f; STOP.json itself remains an unaltered historical artifact.)
9. **STOP.json vs ledger snapshot gap:** STOP.json reflects 16 runs / 1,132,481 tokens at the trip checkpoint; 4 in-flight D-E runs completed afterward (design: in-flight runs finish and are recorded). Final ledger = 20 runs / 1,744,526 tokens (both < 7.2M ceiling). Reports must state both numbers.
10. **D-E phase-2/3 never executed:** in all 12 D-E runs the commit-reveal consultation and committee phases were never reached (one investigator looped to exhaustion, 48.1% of 378 tool calls were identical repeats, the third agent made 0 LLM calls). D-E non-completion is attributable to phase-1 non-convergence under the substituted model, NOT to the decentralized mechanism's cost.
11. **Asymmetric volume-gate instrument:** the crash-on-band gate exists only on C-EQ-TELEM, was set 0.05 above the observed deterministic maximum, and demonstrated live-model variance (P-01 1.235→1.601) exceeds it — C-EQ control-arm crashes are instrument outcomes, not diagnostic failures; left in place they bias any D-E-vs-C-EQ contrast in favor of D-E.

## I4.15 — Human-gate paths made turnkey (2026-10-11)
- **Path (a) close-out deliverable:** `science/v3_campaign_final_report.md` — self-contained feasibility report over rounds 1/2/4, strongest-honest-negative paragraph, MUST-NOT-claim list, all 11 disclosure riders, decision point, evidence pointers.
- **Path (b) V3.3 amendment deliverable:** `design/amendment_v33_both_arms_repair_DRAFT.md` — DRAFT (NOT authorized/frozen), code-level spec: remove per-tool sub-caps (total-budget-only), add symmetric anti-loop cache to TelemetrySandbox (both arms), demote C-EQ volume canary to logged flag (keep measurement), carry seed-saturation fix; exact code sites (telemetry.py:279-286/:85-86, telemetry_arms.py:1108-1113), test plan, re-freeze plan, non-authorizations.
- Both are documentation-only (no live code/spend). Next action is HUMAN: choose (a) or (b) [(c) not authorized]. If (b): human approves change set + spend → 2 fresh judges on the applied diff → new v33_prereg_freeze.md → round 5 (feasibility-only).

## I4.16 — V3.3 built, judged, canaried (path b, human-approved 2026-10-11)
- **Worktree:** `/Users/sushantgautam/Documents/RepliClaw-stg2-v33` (branch `wip/v33-both-arms-repair`, base 57d1e1f). Frozen V3.2 `dev` untouched.
- **Implemented** (commit 520f6859): (1) symmetric anti-loop cache in `TelemetrySandbox` (repeated identical (tool,args) → cached payload, `repeated_cached=True`, NO budget consumed; all 5 OBS tools, both arms); (2) per-tool sub-caps removed (total 48 only); (3) C-EQ volume canary demoted crash→logged `volume_band_violation` flag (ratio still measured); + judge fixes: flag persisted to `status.json` + report count; dead per-tool constants removed.
- **Gates:** 472 passed / 11 skipped / 3 xfailed; ruff + mypy clean.
- **2 fresh judges (PASS):** code-judge PASS-WITH-SHOULD-FIX (5/5 hashes verified, cache symmetric/per-instance/no-aliasing/no-leak, submit_diagnosis uncached, one SHOULD-FIX = flag not persisted → FIXED); science-judge RECOMMEND, no blocker (anti-loop fair-by-symmetry but arm-asymmetric-in-practice; must NOT claim "mechanism validated"; requires a single-agent+cache control in any CONFIRMATORY campaign; band excursions were 0.20–0.40 above ceiling, not 0.05).
- **Live V3.3 canary (8 runs, model `default`):** C-EQ 4/4 completed (all hits, ratios 1.23/1.35 in-band, no crash). D-E 0/4 (3× budget-abort at 119–151K tok, 1× malformed-output). Anti-loop cache fired (10–19 repeated calls made free) but D-E still exhausts 150K via ~30 DISTINCT tool calls/investigator. **The instrument repair is validated, but D-E's phase-1 non-convergence persists as a distinct-call rate under the substituted model; phases 2–3 still not reached. Round 4's negative is preserved and more precisely characterized.**
- **Freeze:** `v33_prereg_freeze_DRAFT.md` (commit 9ac14c3b) with hashes @520f6859 + canary findings + disclosure 12.

## HUMAN GATE — decision for full round 5
The V3.3 instrument is repaired, frozen, and both-judged, BUT the live canary shows
D-E still does not complete under 150K/envelope on the substituted model (the failure
is now a distinct-call rate, not repeat-loop waste). Options:
- **(a) Run full round 5** (10 cases × 2 seeds × 2 arms = 40 runs, ≤7.2M tok, model
  `default`): a clean feasibility record. Expected: C-EQ largely completes (no more
  volume crashes); D-E likely still 0-complete → a more precise negative (no
  decentralization advantage; D-E mechanism still doesn't execute under this model).
- **(b) Raise the per-run envelope** (e.g. 300K, symmetric, both arms, re-freeze +
  re-judge) to give the substituted model headroom to reach phases 2–3 — only then
  does the contrast become *meaningfully* instantiable. Larger instrument change.
- **(c) Stop the V3 feasibility series** — accept the negative (no demonstrated
  advantage; mechanism doesn't execute under the substituted model) as the result.
- **(d) Change model** — NOT authorized per D-V3-017 (would need refreshed access +
  re-prereg).
Awaiting explicit human choice. NO full round launched; NO public release; `main` untouched.

## I4.17 — V3.3 full round 5 launched (2026-10-11)
- Full feasibility round 5 running in the v33 worktree: 10 cases × 2 seeds × 2 arms
  = 40 runs, ≤7,200,000 tok ceiling, concurrency 6, model `default` (SimulaChat,
  Qwen3.8-27B), frozen code @520f6859. Out: `.artifacts/rcaeval/pilot/run_v33/round5/`.
- Per the canary (I4.16) the expectation is: C-EQ largely completes (no volume
  crashes), D-E likely still 0-complete under the envelope → a 40-run feasibility
  record that precisely characterizes the negative. Awaiting completion → T0+4
  report → 2 fresh outcome judges.

## I4.18 — V3.3 round 5 executed + decisive result (2026-10-11)
Round 5 (10×2×2, model `default`, frozen 520f6859) stopped at stop-2 after 16 runs
ledgered (1,264,453 / 7,200,000 tok; D-E crash-equiv 8/20 = 0.40 > 0.25).
- **C-EQ-TELEM: 7/7 ledgered runs completed, all 7 hits** (54,943–71,866 tok),
  crash rate 0/20. 2 runs (P-05/P-06 s11) were out-of-band (ratio >1.40) →
  **logged `volume_band_violation=True`, NOT crashed** (confirming the demotion
  works live on real data).
- **D-E-TELEM: 1/9 ledgered runs COMPLETED — and it executed the full decentralized
  machinery**: P-01 s12 (138,126 tok, **hit=True**). Its escrow ledger shows
  **phase1 + phase2-final commits from all 3 investigators** (inv-a/b/c) — the
  commit-reveal / multi-agent mechanism ran END-TO-END for the first time across the
  whole V3 series and got the diagnosis right. The 8 non-completions: 4×
  budget-abort (150,397–154,253 tok; P-02s11, P-04s12, P-05s11, P-06s11;
  distinct-call non-convergence) + 4× AgentProtocolError (two consecutive malformed
  outputs, inv-a/inv-b; P-01s11, P-03s11, P-03s12, P-04s11 at only ~21–22K tok).
  11 D-E runs never reached at trip. D-E crash-equiv 8/20 = 0.40 > 0.25 → stop-2.
- **Scientific interpretation (feasibility record, NOT an effect estimate):** the
  V3.3 repair (anti-loop cache + no per-tool caps + volume demoted) **successfully
  instantiated the contrast** — the decentralized mechanism is demonstrably capable of
  completing AND being correct, but under the substituted model it does so only 1/9 of
  the time (the model's distinct-call rate still exhausts the 150K envelope in most
  D-E runs; other runs emit malformed actions). The negative finding (no demonstrated
  decentralization advantage) is PRESERVED but now more precisely characterized: the
  mechanism works but is model-limited under substitution; C-EQ is far more reliable
  (7/7 all-hits, zero crashes) at lower cost.
- Report: `.artifacts/rcaeval/pilot/run_v33/round5/pilot_report_round5.md`
  (D-E crashes_by_cause protocol_violation=4, budget_exhaustion=4).
- Next: 2 fresh independent OUTCOME judges (code + science) on round 5, then the
  refined V3 campaign report. NO confirmatory claim (no-confirmatory-reuse).

## I4.19 — Round-5 outcome judges + both SHOULD-FIX applied (2026-10-11)
Two fresh independent round-5 OUTCOME judges (code + science) on the executed run:
- **Code judge: PASS (no BLOCKER, no SHOULD-FIX).** All 6 integrity questions PASS:
  * **Stop-trip:** tripped at the **11-run trip snapshot, D-E 7/20 = 0.35 > 0.25**
    (STOP.json/case_check.json boundary); stop-1 correctly NOT tripped (sat D-E 0.0,
    C-EQ 0.10 < 0.25); stop-3 (774,411 < 7.2M) and stop-4 (floor) correctly NOT
    tripped. The report's 8/20 = 0.40 is the final-ledger state; 5 in-flight runs
    landed after the trip. **Both 0.35 and 0.40 > 0.25 → trip valid either way.**
  * **Metrics:** every reported figure recomputed and matched the raw ledger
    exactly (D-E tokens 834,994; C-EQ 429,459; round 1,264,453; hits 1/1 & 7/7).
  * **D-E completion integrity:** 6 escrow entries (3 phase1 sealed + 3
    phase2-final, all 3 investigators, commit→reveal ordered); ground truth
    `re1ob_adservice_cpu_1 → adservice` verified in case data (parquet), not the
    score file; 138,126 tok < 150K; tool_calls 49 = sum over 4 sandboxes, each ≪48.
  * **Volume demotion live:** P-05/P-06 C-EQ ratio 1.7506/1.8696 →
    `volume_band_violation=true`, `status=completed` (NOT crashed); no C-EQ crashed.
  * **No post-freeze change:** all 4 frozen hashes recompute @520f6859; the
    520f6859→9ac14c3b diff is **docs-only**, zero source changed.
  * **No leakage/cherry-pick:** no ground-truth in any agent-facing payload;
    report is the full 16-run ledger.
- **Science judge: PASS, contingent on 2 SHOULD-FIX (both now APPLIED):**
  * **(Q4) Gate clearance not evidenced in the freeze doc** (header still "DRAFT —
    pending judges" 47 s before launch). FIXED: added a gate-clearance record to
    `v33_prereg_freeze_DRAFT.md` (now "FINAL") documenting that the 2 fresh
    pre-run judges DID PASS (I4.16), both SHOULD-FIX applied pre-freeze, and the
    human re-confirmed scope/spend — v33 worktree commit `ca827ac8`.
  * **(Q6/Q3) Throughput gap must be labeled confounded, not an effect.** FIXED:
    added the mandatory characterization to the campaign report (C-EQ 7/7 vs D-E
    1/9 is an architecture×fixed-envelope token-cost product, inflated by model
    substitution; the anti-loop cache asymmetry is **pro-D-E**, not against it) —
    dev commit `aa79e41b`.
- **Net verdict:** round 5 stands as a defensible **feasibility + refined-negative**
  record. The D-E completion is a genuine, hash-sealed, budget-respecting,
  ground-truth-verified end-to-end execution of the decentralized mechanism
  (n=1); the negative finding is preserved and refined (mechanism capable +
  occasionally correct but not reliable under the substituted model + 150K
  envelope; no advantage demonstrated). No n=1 statistics computed by either judge.

## I4.20 — V3.4 prepared: symmetric 300K envelope, D-E reliability round (D-V3-018) (2026-10-11)
Under the standing full-permission + unlimited-`default` approval and the
round-5 science judge's Q5 recommendation, I proceeded with **option (ii)** —
a V3.4 reliability-characterization round at a **symmetric 300K per-run
envelope** (round 6), to disambiguate whether D-E's round-5 1/9 completion was
envelope-bound or mechanism/model-bound.
- **Isolated worktree** `/Users/sushantgautam/Documents/RepliClaw-stg2-v34`
  (branch `wip/v34-de-envelope`, parent = V3.3 frozen `ca827ac`).
- **Single symmetric change:** `MAX_TOKENS_PER_RUN` 150_000 → 300_000 (the ONE
  A1-parity-guarded shared constant → both arms get 300K identically), and
  `ROUND_TOKEN_CEILING` 7_200_000 → 12_000_000 (mechanical: 40 runs × 300K).
  Files: `telemetry_arms.py`, `pilot_run.py` (ceiling), `pilot_parallel.py`
  (stale comment only). `telemetry.py` + `pilot_report.py` byte-identical.
- **Gates GREEN:** 463 passed / 20 skipped / 3 xfailed / 0 failed; ruff clean;
  mypy clean. Tests updated for new constants (test_v32_amended_constants,
  test_stop3_ceiling_preemptive, parallel_meta + envelope assertions,
  test_v32_amended_envelope_constants).
- **Frozen hashes @0672615d:** telemetry.py 3149ff75 (unchanged),
  telemetry_arms.py d62b4638, pilot_run.py e040650c, pilot_parallel.py bbec3e00,
  pilot_report.py 897d10b7 (unchanged).
- **Freeze:** `design/v34_prereg_freeze_DRAFT.md` @ `54f5267f` (DRAFT — pending
  2 fresh independent judges + human re-confirm). Case data copied to v34
  worktree (cases.parquet md5 matches the working v33 copy).
- **Preregistered interpretations (anti-post-hoc):** (a) D-E completion rate
  RISES at 300K w/ stable accuracy → envelope-bound; (b) stays ~1/20 →
  mechanism/model-bound. Either is valid; NOT preregistered that D-E wins; no
  effect/superiority claim; no-confirmatory-reuse.
- **Next:** dispatch 2 FRESH independent pre-run judges (code + science) on the
  V3.4 diff; apply any SHOULD-FIX + re-stamp; then launch round 6 on
  SimulaChat `default` (concurrency 6). Model change (c) still NOT authorized.

## I4.21 — V3.4 freeze FINAL; round 6 LAUNCHED (2026-10-11)
- **Both fresh V3.4 pre-run judges PASSed** (independent, V3.5-round not reused
  from V3.3):
  - **Code judge: clean PASS.** 6/6 questions satisfied (no leakage, no
    cherry-pick, parity guard intact, ceiling arithmetic 39×300K fits /
    40×300K breaches, reservation auto-scales). 1 SHOULD-FIX:
    `pilot_report.py:46` display-only ceiling stale at 7_200_000.
  - **Science judge: conditional PASS, 4 minimum amendments** — all applied:
    (1) D-E-only docstring → both-arms symmetric [applied];
    (2) wall-cap confound → prereg **Amendment A2**: third outcome class
    `wall-cap-bound`, calibrated NON-BINDING (round-5 max wall 70.2 s vs 900 s;
    2× token work ≈ 140 s ≪ 900 s); (3) baseline denominator → **A3**:
    per-ledgered-run (round-6 D-E / its ledgered runs vs round-5 **1/9**, not
    blended ~1/20); (4) C-EQ non-envelope-boundness → **A4**: C-EQ@300K is a
    reproducibility check, NOT a new reference (round-5 C-EQ@150K 7/7 stands).
- **Applied + re-verified:** code-judge fix made `pilot_report.py` derive
  `ROUND_TOKEN_CEILING` from `pilot_run` (no drift possible); verified via
  report regeneration (`"round_token_ceiling": 12000000`). Gates at final code:
  **472 passed / 11 skipped / 3 xfailed / 0 failed; ruff clean; mypy clean**
  (6 files); offline smoke 4/4, v32_constants 300000/12000000.
- **Freeze:** `design/v34_prereg_freeze.md` (FINAL) @ v34 worktree `5fd3075`;
  frozen hashes @ `6e32153`: telemetry.py 3149ff75 (unchanged),
  telemetry_arms.py **d907a13c**, pilot_run.py e040650c, pilot_parallel.py
  bbec3e00, pilot_report.py **8eda6095**.
- **Launch authority:** standing full-permission + unlimited SimulaChat
  `default` approval; scope re-confirm recorded per launch protocol (option
  (ii) was explicitly authorized).
- **ROUND 6 LAUNCHED** (2026-10-11, ~00:15Z local): worktree
  `/Users/sushantgautam/Documents/RepliClaw-stg2-v34`,
  `scripts/pilot_parallel.py run --round 6 --out .artifacts/rcaeval/pilot/run_v34
  --concurrency 6`, model `default` (echoes Qwen3.8-27B, MODEL-SUBSTITUTION),
  40 runs (10 cases × 2 seeds × 2 arms), 12M safety ceiling, 900 s wall.
- **Next:** on completion → verify escrow + STOP.json, dispatch 2 FRESH
  round-6 outcome judges (code + science), record I4.22, update campaign
  report §2c per preregistered A2/A3/A4 interpretations (envelope-bound vs
  mechanism/model-bound — whichever the data shows). Model change (c) still
  NOT authorized.

## I4.22 — Round 6 (V3.4) completed: prereg interpretation (a) confirmed; judges PASS; report updated (2026-10-11)
- **Round 6 outcome** (git_rev 5fd3075, model `default`, 21/40 runs, stop-1
  C-EQ-sat 0.30 @ 16-run snapshot, 1.52M of 12M spent, exit 10):
  - **D-E: 6/12 ledgered completed, ALL 6 hit=True** (121,236–282,525 tok,
    mean 194,742). Prereg A3 comparison vs round-5 1/9: completion rate rose
    11%→50% at 300K with 100% accuracy on completions ⇒ round-5 1/9 was
    largely **envelope-bound** (prereg interpretation (a) confirmed).
  - D-E non-completions: 4 crashed (AgentProtocolError malformed actions,
    18,445–26,698 tok, 14–21 s — envelope-INVARIANT, same class as round 5)
    + 2 aborted_budget (277,097 / 300,732). **P-05 = counter-evidence**:
    152,364 (R5@150K) → 277,097 (R6@300K), ~1.8× more tokens, still no
    submission ⇒ budget-truncated non-convergence, abort class NOT clean
    "needs N tokens".
  - **C-EQ: 9/9 completed, all hits, 54,759–78,652 tok** — reproduces
    round-5 7/7 (6 of 9 per-case counts within <0.5%; P-05/P-06 s11 +9.4/9.5%
    backend nondeterminism; case_sha256 identical across rounds). Per A4:
    reproducibility check, NOT a new reference.
  - **Snapshot gap (rider 13):** STOP.json 16 runs vs final ledger 21; 2
    post-trip D-E completions (P-07 s11, P-04 s12); full-cohort D-E
    non-completion 6/20 = 0.30 > 0.25 would have tripped stop-2 — C-EQ stop1
    pre-empted it ⇒ terminal state is a D-E-favorable transient, not a
    full-cohort rate. 19/40 runs (P-08 s12…P-10) never launched.
- **Both fresh round-6 outcome judges PASS with SHOULD-FIX** (all applied as
  doc/wording in the campaign report, none required code change to the frozen
  instrument):
  - **Code judge (PASS, 3 SHOULD-FIX):** (1) D-E arm hardcodes
    `prompt_volume_ratio=None` (telemetry_arms.py:954) — parity metric
    C-EQ-observed only → recorded as known instrument gap (rider 13);
    (2) envelope abort can overshoot (P-08 300,732 > 300,000; pre-call check
    at telemetry_arms.py:744) → disclosed; (3) my own claimed C-EQ token
    range 54.7–61.3K was WRONG — actual 54.7–78.7K with P-05/P-06 +9.4/9.5%
    cross-round drift → corrected in report with nondeterminism explanation.
    Also verified: all 5 frozen hashes match @6e32153, 6e32153→5fd3075
    docs-only, STOP.json snapshot arithmetic exact, 35/35 escrow hash
    recomputes clean (all 3 investigators commit+reveal on every completed
    D-E run), 0 ground-truth strings in non-hit D-E audit logs.
  - **Science judge (PASS, 6 SHOULD-FIX, all doc):** (1) add round 6 to
    report (done: §2 row, §2c, §4c, rider 13); (2) never write blanket
    "D-E is envelope-bound" → "partially envelope-bound; crash class is
    envelope-invariant mechanism/model-bound"; (3) no latent-success booking
    of the 2 aborts (P-05 counter-evidence); (4) snapshot-gap rider (done);
    (5) cost = 3.2× mean / 2.2–3.8× per-case (not "~4×"), same-budget at
    per-run cap only; (6) truncation caveat (n=12 of 20, in-flight-inclusive,
    feasibility readout not a rate comparison).
  - **Judge-mandated round-6 wording** (≤5 sentences) adopted verbatim as §4c.
- **Strongest-paired-cell facts (undermine, not support, D-E advantage):**
  P-03 (only fully-paired case): C-EQ 2/2 hit vs D-E 0/2 (both crashed).
  P-06 s11 (only fully-paired seed): both hit, D-E 282,525 vs C-EQ 74,883
  (3.77×).
- **Standing negative STANDS, refined**: "model-limited under substitution"
  → "partially envelope-bound (abort class) + mechanism/model-bound (crash
  class)"; no demonstrated advantage of decentralization/escrow at any
  envelope tried; cost asymmetry WIDENED (2.4×→3.2–3.8×).
- **Campaign report updated** (this commit): scope/verdict, §2 row 6, §2c,
  §4c, §5 MUST-NOT +4, rider 13, §7 decision point (round 6 executed; new
  options: (i) accept as V3 record / (ii) round 7 @600K disambiguation /
  (iii) stop / (c) model change still not authorized), §8 pointers.
- **Next (HUMAN GATE):** decision per §7 — most defensible default is (i)
  accept round 6 as the terminal V3 feasibility record (envelope question
  answered; crash class is the remaining D-E blocker and is envelope-
  invariant, so only a model/protocol change — not authorized — can address
  it), or (ii) authorize round 7 @600K for abort-class disambiguation. Model
  change (c) still NOT authorized. No confirmatory campaign, no heldout, no
  release without fresh G4/G7 approvals.

## I4.23 — Round-6 crash class root-caused; V3.5 instrument built + probes; 2 fresh pre-run judges launched (2026-10-11)

**User question this turn:** "(i) a model change? why crash? maybe used
forced-JSON — Qwen3.8 (default) supports it. (ii) unlimited spend approval
for SimulaChat `default` reaffirmed." **Answer to (i): NO model change is
needed.** The crash is a schema-discriminant drift on the SAME model; the
forced-JSON hypothesis is SUPPORTED by a live diagnostic probe (below).

**Root cause (established from round-6 live transcripts `audit_llm.json`):**
all 4 round-6 crashes were `inv-a` (D-E investigator) emitting **valid JSON**
whose `action` field held the tool name — `{"action": "service_metrics",
"args": {...}}` — instead of the literal `"tool_call"` sentinel.
`parse_action` (telemetry_arms.py:301) rejected it as "unknown action"; the
`_CORRECTION_PROMPT` (:271) **misdiagnosed** it as "not a single valid JSON
object"; the model repeated the same payload; the session then raised
`AgentProtocolError: two consecutive malformed action outputs`. Crash runs:
RCA-P-01/s11, P-02/s12, P-03/s11, P-03/s12. **This is NOT malformed JSON** —
it is discriminant spelling drift. Parity: both arms share the SAME
`parse_action` + `ACTION_PROTOCOL` (A1), so the brittleness is a
shared-instrument artifact, not a D-E handicap — but D-E's 3-investigator
design (4 agents vs C-EQ's 1 manager) hits it ~4× more often, which is why all
crashes landed on D-E. This was a measured cost AND a fixable instrument
artifact.

**Live diagnostic probe (`scripts/diag_crash_probe.py`, committed in v3.5):**
replays the exact P-01/s11/inv-a crash exchange (17 messages cut at the
trigger prompt) under 2 send-conditions × 8 reps on live `default`, scoring
each output under the current `parse_action` and a tolerant normalizer that
accepts only the real `_OBS_TOOLS` names (no metric gaming). Results
(`/tmp/crash_probe.json`, ephemeral):
- **C1 forced-JSON (`response_format={"type":"json_object"}`): 8/8 clean
  protocol-compliant** `{"action":"tool_call","tool":...}` with **zero prose**.
- **C0 plain: 8/8 parse-OK** but all outputs are **prose + embedded JSON**.
- Honest caveat: at this SINGLE replay point the model did NOT crash in either
  condition (8/8 vs 8/8) ⇒ the original crash was **stochastic/low-probability**,
  and C0's single-point compliance does NOT fully quantify the drift rate.
  Forced JSON is nonetheless a real output-discipline improvement (kills the
  prose wrapper that co-occurred with the drift). The proper evidence for
  crash-rate REDUCTION is round 7 itself, not the probe.

> **CORRECTION ADDENDUM (2026-10-11, post-4-point-probe):** the single-point
> probe above OVERSTATED forced-JSON's effect. An upgraded **4-point, 64-call
> probe** (`docs/next_stage/design/v35_probe_all4points.json`, 8 reps × 4
> crash points × 2 conditions, on live `default`) **refuted the
> single-point narrative**: the crash did NOT reproduce at ANY point in
> EITHER condition (both **32/32** parsed under both the current and the
> tolerant parser); prose appeared **only at P-01 in plain mode** (the other
> 3 points were already pure JSON in both conditions). So (B) forced-JSON is
> **NOT independently crash-reducing** — it is a secondary output-discipline
> hardening. The transcript-evidenced **PRIMARY** fix is (C) tolerant
> discriminant; (D) unbounded envelope-bounded retry eliminates the crash
> class by construction. See `v35_prereg_freeze.md` probe rider.

**V3.5 instrument built** (separate worktree/branch `wip/v35-forced-json` off
the frozen V3.4 code `6e32153`→docs `5fd3075`; committed `1f3786a`):
- **(B) Forced-JSON:** `LLMToolSession.ask()` requests
  `response_format={"type":"json_object"}`; if a transport rejects the
  optional param it disables JSON mode for the session and falls back to plain
  mode (a run is never crashed on an optional transport param).
- **(C) Tolerant discriminant + mode-aware correction:** `parse_action`
  recovers tool-name-in-`action` / missing-`action`-with-valid-`tool` into a
  `tool_call`, **only when the tool ∈ `_OBS_TOOLS`** (can never accept a
  fabricated action; `_execute_tool` rejects unknown tools identically).
  `_MalformedActionError` carries `had_valid_json`; the retry prompt names the
  actual failure mode instead of mislabeling it.
- Both fixes are in the **shared** session/parser → both arms, A1 parity
  intact, no capability transfer. Envelope stays 300K/12M (V3.5 does NOT
  change the abort class — that is orthogonal and would need a 600K scope
  decision).
- **Verification (at `1f3786a`):** full suite **472 passed / 0 failed** (20
  skipped / 3 xfailed in this worktree — data-gated skips); ruff clean
  (v3 module + probe + test file); mypy clean (3 instrument files); +9 new
  tests (tolerant recovery ×2 forms, unknown-tool rejection, args-required,
  `had_valid_json` flag, mode-aware prompt, JSON-mode send, JSON-mode
  fallback); offline fake smoke (both arms, full cohort) **15/15 completed,
  all hit, 0 crashes** — validates the crash-recovery path mechanically.
- Only `telemetry_arms.py` differs from the V3.4 frozen blob
  (`d907a13c…` → `0463e6b2…`); telemetry.py / pilot_run.py / pilot_parallel.py
  / pilot_report.py byte-identical (verified via `git rev-parse`).
- **Prereg:** `docs/next_stage/design/v35_prereg_freeze.md` DRAFT written
  (D-V3-019), preregistering: crash-class reduction as primary expected
  effect; abort class expected UNCHANGED; no-confirmatory-reuse; no
  pre-registered "should win"; C-EQ round-7 = reproducibility check per A4.

**Gate status:** this is a NEW instrument ⇒ 2 **fresh** independent pre-run
judges REQUIRED before launch (V3.4 round-6 judges not reused). **Both
launched** (code + science, background, read-only). ⏳ **PENDING:** judge
verdicts → apply any SHOULD-FIXes → re-stamp freeze FINAL → **human
scope/spend re-confirm** → launch round 7 (SimulaChat `default`, 300K/12M,
concurrency 6). Unlimited `default` budget covers spend; the re-confirm
record follows the I4.21 precedent.

**Standing negative STANDS, further refined:** the crash class is
envelope-invariant (crashed at 18–26K, far below cap) and is a FIXABLE
instrument artifact on the same model; the abort class is the
envelope-bound class. V3.5 separates them for the first time. No model change
required; no demonstrated D-E advantage at any envelope yet — round 7
tests whether removing the parse-drift artifact changes D-E's completion
picture, NOT whether D-E "should win."

**Next:** (1) collect the 2 judge verdicts; (2) apply SHOULD-FIXes, re-stamp
freeze FINAL with new hashes; (3) record the human scope/spend re-confirm;
(4) launch round 7 on `default` (unlimited budget pre-authorized for spend);
(5) on completion: escrow/STOP verification, 2 fresh outcome judges, I4.24,
campaign report §2d/§4d. Model change (c) still NOT authorized.

---

## I4.24 — V3.5-D built (unbounded retry); 4-point probe refutes single-point B narrative; B+C+D judges pass; scope/spend re-confirmed (2026-10-11)

**User input this turn:** "(i) model change? why crash? maybe forced-JSON —
Qwen3.8 (default) supports it. (ii) unlimited spend approval for SimulaChat
`default` reaffirmed." + "Go! Spin the fleet." **Answer to (i): NO model
change is needed or authorized** (model change remains out of scope); the
crash is schema-discriminant drift on the same model.

**4-point live probe (64 `default` calls) — refutes the I4.23 single-point
narrative** (see correction addendum above): both conditions 32/32 parsed at
all 4 replay points; prose only at P-01 plain. **(B) forced-JSON is therefore
downgraded to secondary output-discipline hardening, NOT a crash-reduction
mechanism.** (C) tolerant discriminant is the transcript-backed primary; (D)
eliminates the crash class by construction.

**V3.5-D fix (commit `11e7e63a`, instrument blob `1b33c002…`):** `ask()` now
retries on malformed output **until valid**, bounded by a `budget_gate`
wired to each arm's `_enforce_envelope` (300K tokens / 900s wall). A
never-valid model burns the envelope and terminates as an honest
`aborted_budget`, never `crashed`. All 12 `ask()` call sites (D-E
phase1/phase2/committee + C-EQ forecast/planner/continuation/commit) pass
`budget_gate=self._enforce_envelope`. JSON-mode fallback is now logged
(`json_mode_events` + per-prompt transcript `json_mode` flag) for the
cross-arm parity check. Code-judge fixes applied (permissive fallback
documented; `saw_json` set before `isinstance` check; tolerant extra-key
comment).

**Verification (evidence):** full suite **483 passed / 11 skipped / 3
xfailed / 0 failed**; ruff clean; mypy clean; offline fake smoke (round 99,
both arms) crash rate **0.0** on both arms (stop1_ssat trip expected on fake
client).

**2 FRESH pre-run judges on the B+C+D instrument (`11e7e63a`)** (required
because (D) postdated the earlier B+C judges):
- **Code Judge: PASS** (0 required, 1 recommended — persist `json_mode_events`
  to audit, deferred with disclosure; the per-prompt transcript `json_mode`
  flag suffices for the symmetry check).
- **Science Judge: CONDITIONAL PASS** (3 REQUIRED R1–R3 + 5 recommended
  A1–A5). **All applied** as freeze amendment v3 (`9369b5b8`): R1
  crash-vs-budget via `status.json:crash_error` + scope sentence; R2 wall vs
  token derived from `status.json` `tokens`/`wall_s`; R3 drift trigger =
  terminal payload; A1 both-arms rule; A2 B retained cost/hygiene-only;
  A3 arm-asymmetry → reliability-only framing; A4 unified both-arms accuracy
  caveat; A5 first-class negative-result commitment.

**Freeze:** `v35_prereg_freeze.md` amendment v3 at `9369b5b8` (code
`11e7e63a`). Both code + docs are stamped; **only remaining gate = human
scope/spend re-confirm.**

**Scope/spend re-confirm — RECORDED.** The standing user approval "unlimited
spend for SimulaChat `default` model" (reaffirmed twice this session) +
"Go! Spin the fleet." constitutes the explicit re-confirm for the V3.5-D
instrument + round 7, consistent with the I4.21 precedent for V3.4. Scope:
round 7, SimulaChat `default` (no model change), 300K per-run envelope / 12M
round ceiling / 900s wall, 10 cases × 2 seeds × 2 arms = 40 runs,
concurrency 6. **Model change still NOT authorized.**

**Standing finding preserved:** round 6 negative result (no demonstrated
advantage of decentralization/escrow beyond counterfactual access) is
unchanged and is carried forward into the V3.5 freeze in BOTH possible
outcomes. No retroactive rewrite of P08 or preregistered claims.

**Next:** (1) launch round 7 (detached) on `default`; (2) on completion:
escrow/STOP verification + adjudicate non-completions per the prereg rule
(I4.24 freeze), 2 fresh OUTCOME judges, campaign report §2d/§4d, checkpoint;
(3) clean up /tmp/crash_probe*.json + smoke artifact. `main` untouched; dev
LOCAL-ONLY.

---

## I4.25 — Round 7 (V3.5-D) completed: crash class machine-verified eliminated (0/14 vs 4/12); 2 live drift emissions recovered by (C); 2 fresh OUTCOME judges; standing finding UNCHANGED (2026-10-11)

**Round 7 executed** on the V3.5-D instrument (`11e7e63a`, blob `1b33c002…`;
instrument code verified unchanged since launch — only docs committed after).
Stopped at a 22-run snapshot (stop1_ssat + stop2_crash); **final 24-run
ledger** (14 D-E, 10 C-EQ) after 2 post-trip D-E aborts (P-07 s11, P-08 s11;
token delta reconciles exactly: STOP 3,734,441 + 302,152 + 275,300 =
4,311,893 = final total). 16 of 40 planned runs never launched.

**Results (machine-verified from status.json + score.json + audit_llm.json):**
- **C-EQ: 10/10 completed, 10/10 hit (100%), 49,030–77,228 tok; case-level 6/6.**
- **D-E: 6/14 completed, 6/6 hit (100% of completions), 232,273–295,234 tok
  (case-level 2/8 — only P-01, P-03 both seeds).**
- **CRASH CLASS: 0/14 `status=crashed`** (vs round-6's 4/12). The round-6
  parse-drift `AgentProtocolError` class is **machine-verified gone**.
- **2 drift-form EMISSIONS recovered by (C)** (P-04 s11/inv-c, P-06
  s12/inv-c, both `{"action":"service_metrics",...}`): recovered into valid
  tool_calls → run continued → later aborted on the orthogonal tool cap.
  **Direct live evidence (C) works; NOT crashes, NOT fix failures.**
- **8 D-E non-completions = all `aborted_budget`, all orthogonal (not crash
  class):** 4 token-cap (≥300K) + 4 phase-2 tool-cap (`DE_PHASE2_TOOL_CAP=4`,
  D-E-ONLY, pre-existing V3.4, sub-envelope 178–275K tok).
- **JSON-mode parity held:** 0 plain-mode drops in either arm (C-EQ 176/176,
  D-E 1210/1210). Escrow commit-reveal intact on all 14 D-E runs (66 entries,
  0 commit-after-reveal violations).

**⚠️ Adjudication bug caught and fixed (honesty):** my first adjudicator used
`role=="assistant"` but the audit uses `role=="response"`, so it returned
`drift=False` vacuously and I initially reported "0 parse-drift" — a **false
negative**. The independent science OUTCOME judge caught this; I re-derived and
it now matches the judge exactly. **Corrected headline: "0 crash-class
crashes," NOT "0 parse-drift"** (2 drift emissions occurred and were recovered).

**2 fresh OUTCOME judges on the round-7 artifact:**
- **Code Judge: PASS** — frozen code confirmed; no GT leak; no fabricated
  score.json (scorer_sha on all 16); artifacts complete/consistent; escrow
  intact; STOP-vs-ledger snapshot gap reconciled.
- **Science Judge: CONDITIONAL PASS → both REQUIRED applied:** (R1) crash-class
  vs drift-emission distinction documented in the freeze rule-3 clarification
  (freeze commit `4c972e9`) + the "0 crash-class / not 0 parse-drift"
  correction; (R2) the freeze-mandated **raw-vs-adjudicated dual-count** now in
  campaign report §2d (raw stop-2 8/14, full-cohort 8/20=0.40; adjudicated
  crash-class 0/14). RECOMMENDED (snapshot-gap annotation, /20 denominator)
  applied in §2d/disclosure 14.

**Campaign report updated** (`v3_campaign_final_report.md`): round-7 row in
§2 table; §2d (round-7 detail + dual-count table); §2e (what changes / does
not); §4d (refined negative); 3 new §5 MUST-NOT items; disclosure rider 14;
§7 decision point re-based (round 8 @600K now the open disambiguation option);
§8 evidence pointers. **Standing negative finding preserved and refined, NOT
flipped.**

**Standing finding: UNCHANGED** — no demonstrated advantage of
decentralization/escrow beyond counterfactual access, at any envelope
(60/90/150/300K). Round 7 refines *reliability* (crash class gone) while the
*mechanism* question stays unresolved: D-E still completes only 6/14 at ~5×
C-EQ cost with case-level 2/8; residual non-completions are orthogonal
(token-cap + D-E-only tool-cap).

**Next / decision (HUMAN GATE, §7):** (i) accept the round-7 refined negative
as the V3 record and close out; OR (ii) authorize round 8 @600K to
disambiguate the remaining token-cap abort class (genuine budget-need vs
burn-through) — new freeze + 2 fresh judges + human scope/spend approval; OR
(iii) stop the series. Model change (c) still NOT authorized. `main`
untouched; dev LOCAL-ONLY.

---

## I4.26 (2026-10-11) — HUMAN GATE CLEARED: round 8 @600K authorized (option ii); unlimited SimulaChat default spend; fleet dispatched

**Human approval (verbatim substance):** "I give you unlimited authorization power plus spend approval for SimulaChat default model! no need to wait for me! do what you need to! parallelize the things. I need results fast!" — resolves §7 option **(ii)**: round 8 @600K authorized, no further human wait needed for the round-8 cycle (freeze → judges → launch → adjudicate → report). Model change (c) STILL NOT authorized (SimulaChat default / Qwen3.8-27B only). This approval covers provider spend; the round keeps its preregistered 24M stop-3 ceiling as a safety bound, not a spend request.

**V3.6 instrument** (new worktree `/Users/sushantgautam/Documents/RepliClaw-stg2-v36`, branch `wip/v36-600k`, from `4c972e9`): EXACTLY two constant changes + pinned tests + new prereg freeze —
- `MAX_TOKENS_PER_RUN` 300_000 → 600_000 (shared, both arms; A1 parity guard carries)
- `ROUND_TOKEN_CEILING` 12_000_000 → 24_000_000 (40×600K; the 12M ceiling would stop-3 preemptively at 20/32 runs with unbalanced arms — a design flaw the disambiguation must avoid)
- Prereg: `docs/next_stage/design/v36_prereg_freeze.md` — falsifiable H-budget vs H-burn hypotheses, adjudication rule carried from V3.5 rule-3, expected interpretations (primary = case-level paired hit; n=8 feasibility, NOT a demonstrated-advantage claim), non-authorizations.
- Verified at commit `221b81b`: 474 passed / 20 skipped / 3 xfailed; ruff + mypy clean; offline fake smoke 4/4 completed with per-run envelope 600K; case data identical (symlinked gitignored dirs, round-7 `case_sha256` values recorded in freeze).

**Fleet state (2026-10-11 ~11:15):**
- R7-STATS (general-purpose, background): round-7 case-level paired analysis + bootstrap CIs + minimum-n computation → deliverable `docs/next_stage/science/round7_statistical_analysis.md` (this worktree, new file).
- R8-PROV (general-purpose, background): round-8 provenance manifest (v35-vs-v36 blob hashes, round-7 integrity re-verification, stop-3 ceiling analysis) → `docs/next_stage/design/round8_provenance_manifest.json` (v36 worktree, new file).
- V36-CODE-JUDGE + V36-SCIENCE-JUDGE (fresh pre-run judges on `221b81b`): launched; launch is BLOCKED until both return PASS or all REQUIRED items are applied (prereg/documentation fixes only — the instrument is frozen at judge time).

**Launch protocol (gated, in order):** judges' REQUIRED items applied → freeze re-stamped with verdicts → commit → launch `pilot_parallel.py run --round 8 --out .artifacts/rcaeval/pilot/run_v36 --concurrency 6 --label v36-round8` in the v36 worktree (32 runs, 8 cases × 2 seeds × 2 arms) → STOP/adjudication per V3.6 freeze → outcome judges → campaign report §2f/§4e + dev state I4.27.

**Standing finding: UNCHANGED** (round 8 can refine/strengthen it; cannot be pre-flipped). `main` untouched; dev LOCAL-ONLY (never push).

## I4.26b (2026-10-11, ~11:45) — ROUND 8 LAUNCHED (V3.6, 600K envelope)

**Launch record:**
- Frozen HEAD: v36 worktree `cff7d748` (branch `wip/v36-600k`); instrument
  constants: `MAX_TOKENS_PER_RUN = 600_000`, `ROUND_TOKEN_CEILING = 24_000_000`;
  wall cap 900s; concurrency 6; 32 planned runs (8 cases × 2 seeds × 2 arms);
  label `v36-round8`; model SimulaChat default (Qwen3.8-27B, model id
  "default") — MODEL-SUBSTITUTION label applies.
- Both fresh pre-run judges returned CONDITIONAL-PASS; ALL REQUIRED items
  applied to the freeze before launch (doc-only; instrument diff unchanged
  from `221b81b` except one non-behavioral comment). Judge cycle committed at
  `cff7d748`.
- Gate at frozen HEAD: 483 passed / 11 skipped / 3 xfailed; ruff + mypy clean;
  offline fake smoke 4/4 @600K.
- Process: PID 64862, `pilot_parallel.py run --round 8 --out
  .artifacts/rcaeval/pilot/run_v36 --concurrency 6 --label v36-round8` in the
  v36 worktree; provider env passed explicitly:
  `SIMULACHAT_BASE_URL=https://simulachat.sushant.pp.ua/api/v1` (the
  OpenAI-compatible Open WebUI endpoint, model "default" fronting Qwen3.8-27B —
  same provider/model as round 7; the `ai-gateway.sigma2.no` probe returned
  401 for the current token, the `sushant.pp.ua` endpoint authenticated and
  returned `model: Qwen3.8-27B` on the launch probe), key from
  `CUSTOM_SIMULACHAT_KEY` (env, not committed).
- parallel_meta.json verified at launch: git_rev `cff7d748`,
  `max_tokens_per_run: 600000`, concurrency 6.
- Expected runtime: D-E runs ~100–300s wall (round-7 analog), C-EQ ~25–30s;
  round total projected ~30–60 min at concurrency 6.
- R7-STATS deliverable integrated: `docs/next_stage/science/round7_statistical_analysis.md`
  (+ `round7_stats.py` + output): case-level D-E 4/8 vs C-EQ 6/8 (full-cohort,
  no-completion = non-hit), McNemar p=0.5 (n=2 discordant), bootstrap CIs,
  cost 4.08×/hit and 7.48×/case incl. sunk, minimum-n: n=30 for +25pp at
  power 0.8 (n=8 power ≈ 0.10).
- R8-PROV deliverable integrated: v36 `docs/next_stage/design/round8_provenance_manifest.json`
  (34 verifications; 32 pass, 2 expected-fail worktree-equality entries —
  corrected to point at the committed blobs).

**Next:** monitor to STOP/completion → adjudicate with
`/tmp/adjudicate_round8.py` (600K token-cap threshold) → 2 fresh OUTCOME
judges → campaign report §2f/§4e + rider → I4.27. Standing negative finding
remains until the round's machine-verified result says otherwise.
