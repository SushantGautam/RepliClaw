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
