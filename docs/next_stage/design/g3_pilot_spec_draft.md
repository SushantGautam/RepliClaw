# G3 PILOT SPEC (DRAFT) — Wave-2 bounded exploratory pilot, V3 track-O-R (RCAEval)

**Status: DRAFT-PENDING-HUMAN-APPROVAL.** Worker W2h (G3 pilot prep), 2026-10-10; W2l
pilot-spec fix round 2026-10-10 (J-SCI W2 findings S-W2-2/3/4/5/6/10 — each fix marked in
place with `~~superseded~~` and a finding-id citation).
This is a **draft for G3/G4 review**, not an approved protocol. Nothing here authorizes any
live or LLM call. Every number below is traceable to a file listed in §9 or to a computation
shown inline. Numbers that could not be traced are marked **MISSING-WITH-REASON**, never invented.

Sources read (all in `/Users/sushantgautam/Documents/RepliClaw-stg2-dev` unless prefixed):
- `docs/next_stage/reviews/SCIENCE_JUDGE_WAVE1_20261010.md` (§5 pilot constraints, C-SCI-10)
- `docs/next_stage/EXPERIMENT_PROTOCOL_V3_DRAFT.md` (arms, D-V3-008 amendment, S-sat rule)
- `docs/next_stage/design/ceq_arm_design.md` (BudgetEnvelope, caps, planner rounds)
- `docs/next_stage/science/monte_carlo_power_v3.md` (§3.2 pilot-σ variant note, §4 S-sat)
- `src/repliclaw/benchmarks/rcaeval/manifest.py` + `data/cases.parquet` (735 rows)
- `docs/next_stage/design/a2_live_action_set_manifest.md` (Track-I OFFLINE-FIXTURE-ONLY)
- `docs/next_stage/DECISIONS.md` (D-V3-010 SimulaChat authorization)
- `docs/next_stage/EXECUTION_STATE.md` (W2g smoke line, G3 launch prerequisites)
- `stg2-worktrees/w2-simula/.artifacts/agentrx/simula_tiny_smoke/state.json` (measured smoke tokens)

---

## 1. Pilot purpose & non-purposes

**Purpose (exactly three, nothing else):**
1. Estimate **σ̂_D** — the real between-case variance of the per-case paired difference
   D-E minus C-EQ (and the resulting effective per-case-difference σ), to feed the
   **pilot-σ variant cell set** of the frozen MC grid (`monte_carlo_power_v3.md` §3.2 item 3:
   "recomputed with pilot σ̂_D via this MC script … a pilot-σ variant cell set is a 10-line
   extension, to be run post-pilot, before prereg freeze").
2. Measure **per-arm saturation s** (fraction of pilot cases on which an arm succeeds on
   all k seeds) to evaluate the mandatory **S-sat stop rule** (`monte_carlo_power_v3.md` §4;
   D-V3-008 in `EXPERIMENT_PROTOCOL_V3_DRAFT.md`).
3. **Per-arm feasibility**: do the arms complete, crash, time out, or breach the envelope on
   real telemetry at the frozen per-case caps? (J-SCI §5 item 6: the official baseline BARO,
   if run, is a *feasibility check only* — the harness reproduces an official metric in-range.)

**Non-purposes (hard constraints, per J-SCI W1 §5 + C-SCI-10):**
- **NOT confirmatory.** No D-E-vs-C-EQ effect estimate, no power claim, no superiority
  statement may be reported from this pilot. The verdict vocabulary (MEANINGFUL_POSITIVE
  etc.) is explicitly out of scope.
- **NO confirmatory tuning.** Do not tune prompts, arms, scorers, MDE, Δ_min, the S-sat
  threshold, budgets, or stratification from pilot outcome patterns. The only legitimate
  post-pilot changes are: σ̂_D, s, the recomputed power, and the **final** Δ_min value —
  and any other change must be a versioned prereg amendment motivated by a *pre-registered
  defect* (e.g., harness bug), never by "the pilot suggests…".
- **No confirmatory reuse.** Pilot results **cannot be reused as heldout evidence** in any
  form. The 42-case heldout candidate must remain untouched by any pilot-driven tuning.
- No "p < .05" claims, no p-values at all (`EXPERIMENT_PROTOCOL_V3_DRAFT.md` §Scientific
  design: "No 'p < .05' claims from pilot").
- Label discipline: pilot must not read `root_cause.txt`/`fault_description` beyond the
  scorer (same S1 gating as heldout; `manifest.py` `heldout_ground_truth` is the only
  resolve path, via `ScorerContext`).

## 2. Case selection

**Dataset:** `data/cases.parquet` (735 rows; sha256 pinned in
`manifest.py` `CASES_PARQUET_SHA256 = c49a288920dbba2e8e724679a14636d5c7eb2b45426bba14007ef79a6c0ab1bb`).

**Exclusion rule (precise, deterministic):**
1. **Heldout-id exclusion:** a pilot case must not be one of the 42 frozen heldout candidate
   ids. The 42 are exactly the output of `select_heldout_cases` on the pinned parquet
   (quota table in `manifest.py`: RE1-OB mem 5×2, RE2-OB cpu 5×2, RE2-OB mem 5×2, RE3-SS f1 3×2,
   RE3-SS f3 3×2; reps 1–2). The explicit 42 ids:

   RE1-OB mem: `re1ob_adservice_mem_1/_2`, `re1ob_cartservice_mem_1/_2`,
   `re1ob_checkoutservice_mem_1/_2`, `re1ob_currencyservice_mem_1/_2`, `re1ob_productcatalogservice_mem_1/_2`
   RE2-OB cpu: `re2ob_checkoutservice_cpu_1/_2`, `re2ob_currencyservice_cpu_1/_2`,
   `re2ob_emailservice_cpu_1/_2`, `re2ob_productcatalogservice_cpu_1/_2`, `re2ob_recommendationservice_cpu_1/_2`
   RE2-OB mem: `re2ob_checkoutservice_mem_1/_2`, `re2ob_currencyservice_mem_1/_2`,
   `re2ob_emailservice_mem_1/_2`, `re2ob_productcatalogservice_mem_1/_2`, `re2ob_recommendationservice_mem_1/_2`
   RE3-SS f1: `re3ss_carts_f1_1/_2`, `re3ss_front-end_f1_1/_2`, `re3ss_orders_f1_1/_2`
   RE3-SS f3: `re3ss_carts_f3_1/_2`, `re3ss_front-end_f3_1/_2`, `re3ss_orders_f3_1/_2`

   (42 total, re-derived by this worker from the quota table on the real parquet; J-SCI W1
   A6 independently replicated the same 42.)
2. **Tuple exclusion (the operative anti-leak rule):** a pilot case must not share the
   **(system, fault_type, root_cause_service)** tuple with any of the 42. Rationale: within an
   RCAEval dataset a `(system, fault, service)` stratum is the same incident scenario replayed
   across repetitions; the 42 use reps 1–2, so only reps 3+ of those tuples differ
   (measured: reps 3–6 = 192+192+82+76+1 = 351 rows, reps 1–2 = 384). Tuple-exclusion is
   the rule that guarantees the
   pilot cannot share a ground-truth scenario (and its telemetry generation parameters) with
   the frozen heldout.
3. **Smoke-id exclusion:** also exclude the 10 BARO smoke case ids — verified to be exactly
   the RE2-OB cpu heldout subset (`*_cpu_1/_2` × 5 services), already excluded by rule 1.
   (J-SCI W1 A6: "0 overlap with the 10 smoke ids".)

**Eligible pool after exclusion:** 735 − 42 (heldout ids) = 693 rows; then remove every row
whose `(system, fault, root_cause_service)` is one of the 42 heldout tuples (18 distinct
tuples; 693 − 48 = 645). **Eligible = 645 rows / 645 distinct case ids**
(computed inline by this worker on the pinned parquet; shown at the §9 computation log).

**Additional feasibility filter (documented, not a hidden rule):** the scoreable pool is
reps 1–2 of the 645 — a **deterministic ordering convention and data-availability
conservatism** (the same reps-1–2 convention `manifest.py` uses for the heldout), **a
choice, not a ground-truth-availability constraint** — yielding
**168 distinct eligible (suite, system, fault, service) strata**, reps 1–2.
**Factual disclosure:** the scorer's ground-truth label is the index column
`root_cause_service` in `cases.parquet` (populated in **all 735 rows**, 0 nulls; the only
resolve path is `manifest.py` `heldout_ground_truth` via `ScorerContext`); the 8
`root_cause.txt` prose files (re3ss_carts f1/f3 and re3ss_front-end f1/f2, reps 1–2) are
a layout quirk of RE3-SS and are **NOT** the scoring label; reps 3–6 index rows carry
full telemetry metadata (n_metrics > 0 in all 351) and could be scored if a future
amendment ever widened the pool — no number in this spec depends on that.

**Proposed pilot set (n = 10, one case per stratum, lowest repetition, case-name tiebreak —
same deterministic ordering as `manifest.py::_select_stratum`):**

| # | case id | suite | system | fault | service | rep |
|---|---------|-------|--------|-------|---------|-----|
| 1 | re1ob_adservice_cpu_1 | RE1 | ob | cpu | adservice | 1 |
| 2 | re1ob_cartservice_cpu_1 | RE1 | ob | cpu | cartservice | 1 |
| 3 | re1ob_adservice_delay_1 | RE1 | ob | delay | adservice | 1 |
| 4 | re1ob_cartservice_delay_1 | RE1 | ob | delay | cartservice | 1 |
| 5 | re2ob_checkoutservice_delay_1 | RE2 | ob | delay | checkoutservice | 1 |
| 6 | re2ob_currencyservice_delay_1 | RE2 | ob | delay | currencyservice | 1 |
| 7 | re2ob_emailservice_delay_1 | RE2 | ob | delay | emailservice | 1 |
| 8 | re2ob_productcatalogservice_delay_1 | RE2 | ob | delay | productcatalogservice | 1 |
| 9 | re3ob_cartservice_f1_1 | RE3 | ob | f1 | cartservice | 1 |
| 10 | re3ob_adservice_f3_1 | RE3 | ob | f3 | adservice | 1 |

All 10 verified disjoint from the 42 ids **and** from all 42 tuples (computed; §9).
sha256 over the 10 sorted case ids, newline-joined:
`955a462175200909577c8c71db64e3fc8f879c83f1a9028e307926c471503a02`
(placeholder only — the frozen pre-reg hash must also cover the case *data* files per the
W1 download-manifest pattern, S7; that download has not happened yet for pilot cases →
**MISSING-WITH-REASON: pilot case telemetry not yet downloaded**).

**Honest caveats to disclose in the prereg (do not hide):**
- Pilot set is **OB-only** (Online Boutique). RE3-OB eligible strata are code-level faults;
  RE1/RE2-SS and all TT strata are eligible (645 rows include them) but were not taken to
  keep n=10 and downloads bounded. This weakens the "representative" claim; the disclosure
  cost is a limitation line in the prereg ("pilot variance estimate is OB-stratified").
- All pilot cases are **rep 1** (lowest available per stratum under the filter) — the same
  reps-1–2 bias J-SCI S4 flagged for the heldout, disclosed not fixed.
- **Fallback if n < 10 scoreable cases** (e.g., download failure or scorer failure on a case):
  do **not** substitute cases after seeing outcomes; pre-declare that any *infeasible*
  (un-downloadable/harness-crashing) case is dropped before any arm runs, with the drop
  recorded in the pilot report, and that the minimum viable pilot is **n = 8** (below that,
  σ̂_D is too coarse for the 10-line pilot-σ recompute to be meaningful, and S-sat at n=8 has
  granularity 12.5% so the ≥25% rule has only two trip points). **Disclosure cost:** the
  prereg must state the drop list and that σ̂_D/s are conditional on the surviving set.
  **Fallback if no eligible non-heldout case at all** (cannot happen: 645 rows eligible):
  N/A.

## 3. Arms & model

**Pilot arms: D-E and C-EQ only.** Justification: the pilot's estimands are σ̂_D of the
*paired difference* and per-arm saturation — both are defined on the primary contrast pair
(D-E, C-EQ). The MC pilot-σ variant re-computes exactly the D-E vs C-EQ grid
(`monte_carlo_power_v3.md` §1.1 steps 1–2). Running more arms adds token spend without
entering either estimand.

**Deferred arms and why:**
- **D-N, D-R, S-I, C-NE:** deferred from the pilot. Their differences from D-E/C-EQ are
  mechanism-factor questions (H2/H3), not variance/saturation of the primary estimand.
  If the pilot reveals a feasibility problem (crash/timeout pattern), a *bounded*
  single-case probe of the cheapest deferred arm may be added as a versioned amendment
  motivated by the pre-registered defect — not by outcome patterns.
- **BARO (official baseline):** run on the RE2-OB delay pilot cases `~~8~~` **4** (spec
  defect found at T0, I4: the frozen §2 pilot set contains exactly 4 RE2-OB delay cases,
  rows 5–8; "8" was a carry-over miscount — executed on all 4, artifact
  `docs/next_stage/data/baro_pilot_feasibility.json`, Avg@5-DELAY 0.60 in range) **only as a
  feasibility check** (J-SCI §5 item 6) that the harness reproduces the official Avg@5-CPU
  metric in-range, mirroring the W1 RE2 smoke (0.66 Avg@5-CPU). Its outputs are
  MODEL-SUBSTITUTION-labeled where LLM-involved and are **never** a comparison target.

**Model:** **SimulaChat default = Qwen3.8-27B**, arm-identical, per D-V3-010
(`DECISIONS.md` 2026-10-10T09:20+02:00): "SimulaChat default is the authorized LIVE run
model. It is arm-identical (matched-tools requires identical model across arms…)". Free tier.
Endpoint: `https://ai-gateway.sigma2.no` path `/api/v1` (W2g probe, EXECUTION_STATE I2;
live run metadata `runs/p08-live-20261009T122444Z/S5/run-001/run_metadata.json` records
`endpoint: https://ai-gateway.sigma2.no/v1`, `model: Qwen3.8-27B`, `temperature: 0.2`).
Credentials only via env (`SIMULACHAT_BASE_URL` / `SIMULACHAT_API_KEY` / `SIMULACHAT_MODEL`);
none in code or docs (D-V3-010 execution constraint).

**Model-substitution labeling (mandatory, J-SCI rule via D-V3-010):** any number in the pilot
report that is compared to, or sits next to, an *external* baseline (BARO frontier-model
official results, AgentRx released baseline) must carry the label
`MODEL-SUBSTITUTION (SimulaChat default, Qwen3.8-27B) — NOT the official released baseline`.
The D-E-vs-C-EQ internal contrast is *not* a model-substitution comparison (same model,
arm-identical); the label applies to external comparisons only.

**Seeds:** k = 2 seeds per case (protocol §Scientific design candidate pilot: "6–10
independent cases with 2 seeds each"). Seeds: 20261011, 20261012 (proposed; must be frozen
in the prereg). Note: k=2 is the main-grid k in `monte_carlo_power_v3.md`; the heldout may
use k=4, but the pilot estimates σ̂_D at k=2 — the 10-line pilot-σ extension must carry the
k-dependence (already in the grid: k ∈ {2,3,4}).

## 4. Budget & cost estimate

**Per-case arm envelope (frozen, shared, from the C-EQ design and live metadata):**
`BudgetEnvelope(max_tokens=60_000, max_wall_s=900, max_agents=4)` — `ceq_arm_design.md`
§2 ("P08 envelope: 60,000 tokens / 900 s / 4 agents — identical BudgetEnvelope, so
envelope_sha256 parity holds") and byte-confirmed in
`runs/p08-live-20261009T122444Z/S5/run-001/run_metadata.json` (`max_tokens: 60000,
max_wall_s: 900.0, max_agents: 4`). Planner rounds: max 4 (`ceq_arm_design.md` §3, "proposed 4");
consultation cap 1/investigator/case; C-EQ prompt-volume canary band **frozen value
[0.6, 1.25]** of D-E volume (frozen value as of a716a85, per J-SCI W2 **S-W2-6** —
FROZEN-CONSTANTS appendix; the 0.8-docstring note is amendments conflict #3; see §6).
`~~(S3 reconciliation pending)~~`

**Per-case token cost model (real measured anchors, shown):**
- Hard ceiling per arm per case: **60,000 tokens** (envelope; `test_v3_ceq_budget.py` pins
  overflow abort at this cap — the envelope is enforced, spend ≤ 60,000).
- Live measured (P08 eess run, Qwen3.8-27B, same endpoint): one completed eess arm run took
  **97.84 s wall** (S5 run-001 metadata). **MISSING-WITH-REASON:** P08 `run_metadata.json`
  does not store a token total field; the per-case live token spend for a V3 D-E/C-EQ run is
  not yet measured (V3 offline tests use fake clients with synthetic volumes, e.g.
  `per_call=(40, 12)` in `test_v3_ceq_budget.py` — not a measurement).
- Best available per-trajectory LLM measurement (W2g SimulaChat smoke, Qwen3.8-27B, same
  endpoint, `stg2-worktrees/w2-simula/.artifacts/agentrx/simula_tiny_smoke/state.json`):
  2 trajectories, 2 completions, **prompt 20,865 + completion 595 = 21,460 tokens**
  → ~10.7K prompt + ~0.3K completion per trajectory — this is the W2g smoke figure quoted
  in the task; it is an AgentRx single-judge volume, **an order-of-magnitude anchor only**
  (a full D-E/C-EQ case uses up to 4 agents × ≤4 planner rounds × several calls each, so the
  envelope, not this anchor, is the planning number).
- Wall anchor: 97.8 s per completed live arm run (above). With ≤4 sequential agent/round
  calls per arm round and ≤4 rounds, a completed case is expected to sit well under 900 s;
  the 900 s cap is the planning ceiling. **Per-case wall planning value: ≤ 900 s** (cap; no
  better measured estimate exists for V3 arms — **MISSING-WITH-REASON:** no V3 live run
  has happened yet, and this spec forbids live runs).

**Cost table (planning, envelope ceilings, n = 10 cases × k = 2 seeds):**

| Unit | Tokens/case | ×seeds | ×cases | Arm subtotal (tokens) | Wall/case (cap) |
|------|------------:|-------:|-------:|----------------------:|----------------:|
| D-E | 60,000 | 2 | 10 | **1,200,000** | 900 s |
| C-EQ | 60,000 | 2 | 10 | **1,200,000** | 900 s |
| BARO feasibility (RE2-OB delay, 8 cases, 1 pass, official-pipeline LLM use) | 60,000 (same envelope cap for LLM-involved calls) | 1 | 8 | **480,000** | 900 s |
| **TOTAL PILOT CEILING (tokens)** | | | | **2,880,000** | |

**TOTAL PILOT TOKEN CEILING: 2,880,000 tokens.** SimulaChat is the authorized **free tier**
(D-V3-010), so expected monetary cost = $0; the token ceiling is the spend/rate-limit cap and
is enforced as a hard stop (§5 rule 3). **Wall-time ceiling (sequential): (10×2 + 10×2 + 8) =
44 runs × 900 s = 43,200 s = 12.0 h; with 2-way case parallelism ≈ 6.0 h**
(`~~(44,100 s ≈ 12.25 h; ≈ 6.1 h)~~` — arithmetic corrected per J-SCI W2 **S-W2-2**:
44 runs, not 48; the token ceiling 2,880,000 was already correct). (Parallelism plan: run two
cases concurrently in isolated workspaces per protocol isolation rules; concurrency is
recorded per run, per ceq design R9). If a rate-limit wall appears, the pilot pauses —
pausing is not a stop rule.

## 5. Stop rules (exact metric + checker)

All stop checks run after each **case+seed+arm** completes; the checker is the **integrator
(human-supervised)**, who reads the per-run `run_metadata.json` and the pilot ledger
(arm, case, seed, status, tokens, wall). No automated "self-check" claim: the human
integrator performs each check before the next case is dispatched.

1. **S-sat (mandatory).** Metric: `sat_A` = (cases where arm A succeeded on **all k=2
   seeds**) / n_pilot, evaluated per arm after each case completes. **Stop iff
   `sat_D-E ≥ 0.25` OR `sat_C-EQ ≥ 0.25`** (with n=10: 3 of 10 cases saturated for either
   arm). Action: STOP pilot, execute the **pre-registered difficulty ladder** (§5.1, added
   per J-SCI W2 **S-W2-10**) and re-pilot on the next ladder rung before any heldout —
   max 2 re-pilots total. Source: D-V3-008 + `monte_carlo_power_v3.md` §4 (one-arm s=0.25
   already gives ~30–40% false-fire at Δ=0, N=12–24). Also record the two-arm dead-contrast
   figure (cases where **both** arms saturate) in every report — it is a disclosure, not a
   separate stop at pilot scale.
   **(a) Required pilot-report disclosure (S-W2-4):** the pilot report must print, **per arm
   with the observed s**: `s = k/10` together with the binomial trip probability at the
   observed s (trip defined as s ≥ 3/10 = 0.25; binomial n=10, p = observed s — e.g., at
   observed s = 0.20, P(trip) = P(Bin(10, 0.20) ≥ 3) = 0.32). These figures are also
   tabulated in the traceability log (§9).
   **(b) Coarse-screen status (S-W2-4, verbatim to carry into the prereg):** "pilot S-sat
   is a coarse screen; the heldout running canary (first 25% of heldout = 6 cases,
   granularity 1/6) is the operative check. The 0.25 threshold is NOT lowered for the
   pilot (threshold parity; at n=10 a finer threshold adds no information)."
2. **Per-arm crash rate.** Metric: crash_A = (case+seed+arm runs with `status` ∉
   {completed} and no partial diagnostic — i.e., harness error, abort, or timeout at the 900 s
   cap — for arm A) / (10 × 2 = 20 runs). **Stop iff crash_A > 25% (i.e., ≥ 6 of 20 runs)
   for either arm.** Rationale for X=25%: above this, the per-arm success estimates the pilot
   feeds are no longer ITT-meaningful and feasibility is the wrong answer; consistent with
   the S-sat granularity choice. A budget-overflow abort (`aborted_budget`) counts as a crash
   here — it means the 60,000 cap is structurally too small for the case class, which is a
   feasibility signal, not a science result.
3. **Budget envelope breach.** Metric: cumulative pilot-round tokens (all arms, from ledger;
   cumulative WITHIN the current pilot round only — the ceiling resets per round per §5.1)
   vs the **2,880,000 per-round ceiling**; and any single run exceeding `max_tokens=60,000` or
   `max_wall_s=900` (the harness itself aborts those — a breach is a harness defect, not an
   expected state). **Stop iff cumulative > 2,880,000 or any single-run envelope breach is
   observed.** Action on stop-3-cumulative: freeze the pilot at the cases completed, analyze
   with n_actual, disclose the truncation.
4. **Model-capability floor gate (mandatory — J-SCI W2 S-W2-1; verbatim-consistent with
   the protocol's floor gate).** Metric, at pilot scale (10 cases × k=2 seeds = 20 runs
   per arm): run-level successes per arm and per-case all-seeds success. **TRIP if EITHER
   arm has < 2/20 run-level successes OR per-case all-seeds success = 0 on ≥ 9/10 pilot
   cases.** Action on trip: STOP — classify the campaign state **MODEL-CAPABILITY-SCREEN-FAILED**;
   do NOT launch the heldout on that model; report the negative result with the saturation
   evidence (per-arm run-level success, per-case all-seeds success table, floor-gate
   numbers). This is a model-capability screen, not a stratification problem: the §5.1
   ladder does NOT run on a floor trip (re-stratification cannot remedy floor saturation).
   Frozen contingency (protocol, verbatim): re-scope to the above-floor case subset, or
   request a human decision on a stronger model; never silently switch models mid-heldout.
   Stop rules 1 and 4 are **both mandatory**; a pilot is admissible for heldout launch only
   if neither tripped.

Each stop produces a versioned pilot report with the ledger snapshot (this is evidence for
the prereg amendment trail, not a result).

### 5.1 Pre-registered difficulty ladder + capped re-pilots (added per J-SCI W2 **S-W2-10**)

The unbounded "re-stratify (harder fault families / other systems), re-pilot" loop is
**superseded** (`~~re-stratify + re-pilot, no cap~~`). On an S-sat trip, re-stratification
is NOT a free choice after seeing saturation — it executes this frozen ladder, a pre-declared
order of the eligible pool by difficulty proxy (BARO-smoke evidence + suite strata; the
quota table in `manifest.py` fixes the suite/system/fault strata). A trip therefore runs a
**frozen branch**, not an outcome-informed selection (the selection is made before any pilot
outcome beyond the trip metric itself is seen).

**Ladder (easiest → hardest rung), each rung = the 10-case set built by the §2 ordering
rule (one case per (system, fault, service) stratum, lowest repetition, case-name tiebreak),
with per-rung pool size on the pinned parquet (735 rows, sha `c49a2889…`), after the §2
exclusion rules:**

| Rung | Definition (suite, system, fault) | Eligible reps-1–2 rows (computed, §9) |
|------|-----------------------------------|---------------------------------------:|
| (run 0) | the §2 pilot set (10 ids, sha `955a4621…`) | 10 |
| L1 | RE1-OB mem | **0 — EMPTY** (25 raw rows, all reps 1–2 excluded by §2 rule 2: heldout tuple) |
| L2 | RE2-OB cpu | **0 — EMPTY** (15 raw rows; reps 1–2 = the 10 BARO-smoke ids, excluded by §2 rules 1/3) |
| L3 | RE2-OB mem / RE3-SS f1 / RE3-SS f3 | **0 — EMPTY** (35 raw rows: 15+10+10; RE2-OB mem reps 1–2 and all RE3-SS f1/f3 reps 1–4 are heldout tuples; no reps 1–2 remain) |
| L4 | next non-empty OB bucket: RE1-OB cpu (4) + RE1-OB delay (10) + RE2-OB disk (10) + RE2-OB loss (10) + RE2-OB socket (10) — filled by §2 ordering until 10 cases | 44 (→ 10 picks) |
| L5 | next non-empty OB bucket: RE1-OB disk (10) + RE1-OB loss (10) + RE3-OB f1 (6) + RE3-OB f3 (4) | 30 (→ 10 picks) |
| L6 | RE1/RE2-SS resource buckets (cpu/mem/delay/disk/loss/socket, 5 strata each) | 110 (→ 10 picks) |
| L7 | RE3-SS f2/f4 + RE3-TT f1–f4 (code-level faults) | 22 (→ 10 picks) |
| L8 | RE1/RE2-TT resource buckets (cpu/mem/…) | 110 (→ 10 picks) |

Computed 2026-10-10 on the pinned parquet by W2l (shown at §9). **MISSING-WITH-REASON
(record, does not block):** the rung *names* L1–L3 were specified by the W2 fix directive
(easiest→hardest by BARO smoke + strata), but all three are **empty on the reps-1–2
scoreable pool** — the frozen heldout tuple-exclusion (§2 rule 2) removes exactly those
strata, which is itself the anti-leak rule working as designed. L4–L8 are the actual
non-empty rungs, ordered easiest→hardest (BARO-validated RE1/RE2-OB resource faults first,
code-level RE3 and non-OB systems later). The human must approve L1–L3 being empty and
L4–L8 taking over at T0 (this changes no number in §4: each re-pilot reuses the same
envelope ceilings — 10 cases × 2 seeds × 2 arms × 60,000 + optional 8-case BARO feasibility
pass → same 2,880,000 per-pilot-round ceiling). **Resolved (was MISSING-WITH-REASON, closed
at I3, 2026-10-10):** stop rule 3's 2,880,000 ceiling is **per-pilot-round**, NOT
campaign-cumulative across re-pilots — each of the MAX 2 re-pilots re-derives an identical
fresh 2,880,000 envelope from the same §4 arithmetic (identical n, k, arms, per-run
60,000 cap). Consequence for campaign accounting: worst-case total = 3 rounds × 2,880,000
= **8,640,000 tokens** (still $0 on the authorized free tier; the per-round stop keeps any
single round auditable against one frozen envelope). The T0 prereg wording states this
one sentence; it changes no number in §4.

**Cap (pre-registered, no discretion):** **MAX 2 re-pilots total**, each on the **NEXT
ladder rung** only (re-pilot 1 → first non-empty rung after the run that tripped; re-pilot
2 → the rung after that). Ladder rung choice is pre-declared in this table before any
pilot outcome beyond the trip metric (s) is seen; a trip merely *selects* the next frozen
rung. A **third** trip (after both re-pilots) aborts the campaign to
**INCONCLUSIVE-STRATIFICATION** and goes to the **human** for re-scope/stop — it is *not*
another re-stratification, and it is *not* a heldout-launch gate (the heldout does not
launch while the verdict is INCONCLUSIVE-STRATIFICATION). The 42 heldout remain frozen
throughout (already stated §2/§6).

## 6. Pre-registration requirements

**Two-column freeze table. "Before" = must be in the frozen pilot prereg at T0 (launch);
"After" = may be updated after the pilot, and this update *is* the legitimate purpose of the
pilot.**

| FROZEN BEFORE the pilot (T0) | May be UPDATED AFTER the pilot |
|------------------------------|-------------------------------|
| Pilot case list (10 ids, §2 table) + sha256 of the id list + sha256 of the downloaded case data files (per S7 download-manifest pattern) | **σ̂_D** (pilot-estimated between-case variance of the paired difference) and effective per-case σ |
| Exclusion rule text (rules 1–3, §2) verbatim | **s** (per-arm saturation fractions; disclosed in every report) |
| Arm set = {D-E, C-EQ} + BARO-feasibility scope (`~~8~~` 4 RE2-OB delay cases, feasibility label; 4-vs-8 defect closed at I4) | Recomputed MC power (pilot-σ variant cell set, the 10-line extension, run **before** final prereg freeze) |
| Model id + endpoint label: SimulaChat default (Qwen3.8-27B), endpoint label `simulachat` (no credentials), temperature 0.2, MODEL-SUBSTITUTION label rule for external comparisons | **Δ_min confirmed at 0.15 (A1 candidate), or LOWERED with written justification + `rule_a1` re-run at the chosen value — never RAISED post-pilot** (raising converts POSITIVE_SUBTHRESHOLD→NOT_ESTABLISHED; lowering manufactures MEANINGFUL_POSITIVE). `~~(0.10 vs 0.15, C-SCI-9)~~` harmonized per J-SCI W2 **S-W2-5**: the A1 candidate 0.15 is the single candidate; 0.10 (D-V3-007) is superseded-candidate-for-the-record only. This is the confirmation/lowering-only path — it does not contradict the protocol A1 amendment ("fixed at freeze as Δ_min = 0.15"), which fixes the *starting* value; lowering with written justification is the only permitted post-pilot movement. The `rule_a1`@0.15 MC re-run is scheduled **before G4** (a separate worker is executing it now; cite as **pending-with-track**), so the freeze cites the exact variant. J-SCI + statistician sign-off required. |
| Envelopes: 60,000 tokens / 900 s / 4 agents / ≤4 planner rounds / 1 consultation per investigator per case / C-EQ prompt-volume canary band frozen value = **[0.6, 1.25]** (the value, not a pointer — `~~pending S3 reconciliation~~` per S-W2-6; source: FROZEN-CONSTANTS appendix `PROMPT_VOLUME_FLOOR=0.6 / CEIL=1.25`; the 0.8-docstring-vs-0.6-code mismatch is disclosed as amendments conflict #3) | Heldout k (2/3/4) within the N=24 budget, per `monte_carlo_power_v3.md` §3.2 refinement 1 |
| Seeds {20261011, 20261012} | The S-sat *outcome* (trip or not) — the rule itself (0.25) is frozen, never tunable |
| Stop rules 1–4 verbatim, incl. crash threshold 25%, per-round token ceiling 2,880,000 (reset per round per §5.1; campaign worst-case 8,640,000), and the S-W2-1 model-capability floor gate (<2/20 run-level OR ≥9/10 per-case all-seeds=0 → MODEL-CAPABILITY-SCREEN-FAILED; the ladder does NOT run on a floor trip); **plus the §5.1 difficulty ladder table + the MAX-2-re-pilots / INCONCLUSIVE-STRATIFICATION cap, verbatim (S-W2-10)** | MDE re-scope (0.15 → 0.20) if the pilot-σ power shows 0.15 unattainable (this is a pre-declared consequence, not a tuning from outcome patterns — it executes a pre-registered branch) |
| Estimator definitions: σ̂_D computed on paired per-case differences, k=2, cluster=case; s defined as all-seeds-success fraction; ITT (failed runs = non-success) | The re-pilot case list *only if* S-sat trips: next rung of the §5.1 pre-registered difficulty ladder (MAX 2 re-pilots; `~~"re-stratified re-pilot"~~` — S-W2-10); the 42 remain frozen either way |
| **"No confirmatory reuse" clause verbatim:** pilot results cannot be reused as heldout evidence; no effect estimate / power claim / superiority statement is reported from the pilot; any parameter change not in the After-column requires a versioned amendment motivated by a pre-registered defect | (nothing else. Any additional "After" permission must itself be a versioned amendment) |

**Also frozen before T0 (carry-over conditions — current state at T0, updated per J-SCI W2
**S-W2-6** as of dev @ a716a85):**
- C-SCI-1 scorer-only gate (S1): required at T0 (unchanged).
- C-SCI-2 L5 pin: **DONE** — `src/repliclaw/benchmarks/common/power_pin.py` +
  `tests/benchmarks/test_l5_pin.py` in repo (W2c merged; shas `e14d28ad…` / `929d6fe9…`
  re-verified by J-SCI W2).
- C-SCI-3 canary band: **frozen value = [0.6, 1.25]** (the value is recorded, not a pointer
  to a reconciliation event) — FROZEN-CONSTANTS appendix; amendments conflict #3
  (0.8-docstring vs 0.6-code) is the disclosed 0.8 note and the one reconciliation item to
  close before launch. `~~"G4-blocker, band pending"~~` framing removed.
- J-CODE W2 verdict: **exists** — `reviews/CODE_JUDGE_WAVE2_20261010.md`,
  **APPROVE-WITH-CONDITIONS**; conditions closed except **F-W2-12** (deferred to the G4 doc
  pass). `~~"verdict clear"~~` updated to "verdict issued, conditions tracked".

## 7. Approval gates (human must approve, before LAUNCH)

Checklist — **all five required**, recorded in `DECISIONS.md` as a single entry with timestamp:
1. **Scope:** n = 10 cases (the §2 table, ids + hashes), k = 2 seeds, arms {D-E, C-EQ} +
   BARO feasibility on 8 cases, OB-only + reps-1 caveats accepted.
2. **Token ceiling:** 2,880,000 per pilot round (1.2M D-E + 1.2M C-EQ + 0.48M BARO;
   resets per round per §5.1; campaign worst-case across MAX 3 rounds = 8,640,000),
   enforced as hard stop rule 3 (per-round cumulative).
3. **SimulaChat use for the pilot:** Qwen3.8-27B default, arm-identical, free tier,
   MODEL-SUBSTITUTION label on external comparisons; confirms D-V3-010 covers the V3
   arms (it does, per DECISIONS line 60, but explicit re-approval is required because
   EXECUTION_STATE lists "(c) G3 pilot authorization" as still-open human item).
4. **Track-I exclusion:** confirm the pilot runs **Track-I = OFFLINE-FIXTURE-ONLY**
   (`a2_live_action_set_manifest.md`; D-V3-007 amendment: no live AIOpsLab run, no G2 pass
   for Track-I before the live action-set manifest digest references exist) — i.e., the
   pilot uses **no** live AIOpsLab environment, only downloaded RCAEval telemetry + the
   harness.
5. **Launch authority:** explicit go for W2h/integrator to execute the pilot (this is the
   EXECUTION_STATE open item "(c) G3 pilot authorization"; (a) VM/budget and (b) heldout
   budget are *not* prerequisites for the pilot itself but must stay open and visible).

## 8. Timeline (T0 = human approval time; no calendar dates)

| Step | Content | Owner |
|------|---------|-------|
| T0 | Human approves §7 checklist (1–5); `DECISIONS.md` entry written | Human (Sushant) |
| T0+0 | Pilot prereg frozen: §6 Before-column committed as a timestamped doc + hashes (case-id hash now: `955a4621…` placeholder until data-file hashes exist) | Integrator |
| T0+1 | Download pilot case telemetry (10 cases × {metrics, logs, traces, inject_time, root_cause.txt}); per-file sha256 into a `download_manifest.json` (S7 pattern); verify against the frozen id list | Worker (read-only + download only) |
| T0+2 | Dry-run canaries on the 10 pilot cases with **fake** clients only (envelope parity, reset, scorer path, label gate) — no LLM | Worker + J-CODE scan |
| T0+3 | **Pilot run:** 20 D-E + 20 C-EQ case-seed runs + 8 BARO feasibility runs, ledger updated per run, stop checks 1–3 after each case | Integrator (human-checked) |
| T0+4 | Pilot report: σ̂_D, s (per arm, disclosed), feasibility notes, ledger snapshot, stop-rule outcomes. No effect claim. | Integrator |
| T0+5 | Pilot-σ MC variant cell set (10-line extension of `monte_carlo_power.py`, sha-pinned per C-SCI-2) recomputes power at σ̂_D for the candidate (N=24, k∈{2,3,4}, MDE 0.15/0.20) cells | Statistics worker |
| T0+6 | **Final prereg freeze:** heldout N/k/MDE/Δ_min + S-sat + all disclosures (S4: reps-1–2, TT-absent, 10/42 smoke pre-finalization; S5: adaptivity scope; this spec's OB-only pilot caveat). J-SCI + statistician sign-off. | J-SCI + human |
| T0+7 | Heldout launch (only if S-sat did not trip and no re-pilot is pending; if it tripped, execute the pre-registered difficulty ladder §5.1 — MAX 2 re-pilots, next rung each — before any heldout; a third trip aborts to INCONCLUSIVE-STRATIFICATION and goes to the human. The 42 never change) | Human approval again |

## 9. Traceability appendix (computation log)

All computations run by W2h on the pinned `data/cases.parquet` (735 rows; pyarrow≥25) with
the frozen quota table from `manifest.py`:
- Heldout re-derivation: 42 ids, exact quota match (matches J-SCI W1 A6 independent replication).
- Heldout tuples: 18 distinct (system, fault, service) tuples.
- 735 − 42 = 693; 693 − 48 (rows sharing a heldout tuple) = **645 eligible rows/cases**.
- `has_root_cause_file` (measured): reps 1: 4/192, reps 2: 4/192 (both RE3 carts f1/f3 SS
  — the 6 S1 files), reps 3–6: 0/**351** (`~~0/443~~` typo corrected per S-W2-3: reps
  3–6 = 192+192+82+76+1 = 351 rows) → scoreable pilot pool restricted to reps 1–2 by
  deterministic ordering convention + data-availability conservatism (a choice, not a
  ground-truth-availability constraint; scorer label = index column
  `root_cause_service`, populated in all 735 rows) → 168 eligible strata.
- The 10 pilot ids in §2: all disjoint from the 42 ids and from all 42 heldout tuples
  (verified programmatically); sha256(sorted ids, "\n"-joined) =
  `955a462175200909577c8c71db64e3fc8f879c83f1a9028e307926c471503a02`.
- Token ceiling arithmetic: 10 cases × 2 seeds × 2 arms × 60,000 = 2,400,000; + 8 × 60,000
  BARO = 480,000; total **2,880,000**.
- Wall arithmetic: (20 + 20 + 8) = **44 runs** × 900 s = **43,200 s = 12.0 h** sequential
  (`~~44,100 s~~` — the "44,100 / 48 runs" figure was itself a miscount; corrected per
  J-SCI W2 **S-W2-2**; 43,200/2 = 21,600 s = 6.0 h at 2-way parallel).
- S-W2-4 binomial trip-probability table (trip = s ≥ 3/10; P(Bin(10, p) ≥ 3) at observed
  case-saturation p): p = 0.00/0.10/0.20/0.30/0.40/0.50/0.60/0.70/0.80/0.90/1.00 →
  0.000 / 0.070 / 0.322 / 0.617 / 0.833 / 0.945 / 0.988 / 0.998 / 1.000 / 1.000 / 1.000
  (computed; matches J-SCI W2 S-W2-4's 0.18/0.32/0.47 at p = 0.15/0.20/0.25).
- S-W2-10 difficulty-ladder pool sizes (computed on the pinned parquet after the §2
  exclusion rules, reps 1–2 scoreable pool): RE1-OB mem 0 (25 raw), RE2-OB cpu 0
  (15 raw; reps 1–2 = the 10 BARO-smoke ids), RE2-OB mem 0 (15 raw) + RE3-SS f1 0
  (10 raw) + RE3-SS f3 0 (10 raw) — L1/L2/L3 all empty (35 raw rows total) because those
  strata are exactly the frozen heldout tuples (anti-leak rule 2); L4 = RE1-OB cpu 4 + RE1-OB delay 10 +
  RE2-OB disk 10 + RE2-OB loss 10 + RE2-OB socket 10 = 44 eligible; L5 = RE1-OB disk 10
  + RE1-OB loss 10 + RE3-OB f1 6 + RE3-OB f3 4 = 30; L6 = RE1/RE2-SS buckets = 110;
  L7 = RE3-SS f2 2 + f4 4 + RE3-TT f1 4 + f2 4 + f3 4 + f4 4 = 22; L8 = RE1/RE2-TT
  buckets = 110. Per-rung pick sets follow the §2 ordering rule; per-rung id-list sha256s
  to be generated at T0 of the applicable re-pilot (two-step freeze: rung definition now,
  id-list hash when the trip executes — same pattern as §2 data-file hashes).

**Known gaps (honest):** (i) per-case V3 live token/wall not yet measured — envelope is the
planning number; (ii) pilot case data-file hashes MISSING until T0+1 download; (iii)
SimulaChat rate limits unknown — pause, don't stop, on rate-limit waits; (iv) BARO LLM
volume is capped at the shared envelope but its official-pipeline token profile is
MISSING-WITH-REASON (official BARO LLM calls not yet run under SimulaChat for RCAEval).

*Draft by W2h, G3 pilot prep. DRAFT-PENDING-HUMAN-APPROVAL. No code changed, no live run,
no LLM call made by this worker; uncommitted in the stg2 worktree for integrator review.*
