# V3 PREREGISTRATION — FINAL FREEZE (DRAFT — NOT FROZEN)

**Status: DRAFT, prepared for orchestrator/human stamp. Nothing in this
document is frozen until the stamp clause (§5) is executed.**
Prepared by: statistics-and-protocol worker (T0+6). All frozen wording below is
QUOTED VERBATIM from the cited frozen/amended sources — no frozen text is
rewritten here. All hashes were computed on 2026-10-11 by this worker and
matched against the values the frozen docs claim (see §3/§4).

Sources of operative freeze wording (doc shas in §4):
- S1 = `docs/next_stage/design/g3_pilot_spec_draft.md`
- S2 = `docs/next_stage/EXPERIMENT_PROTOCOL_V3_DRAFT.md`
- S3 = `docs/next_stage/science/statistical_protocol_v3.md`
- S4 = `docs/next_stage/science/monte_carlo_power_v3.md`
- S5 = `docs/next_stage/amendments_AMEND_V3_FREEZE_20261010.md`
- S6 = `docs/next_stage/DECISIONS.md` (amendments through D-V3-015)

---

## 1. Operative freeze wording (assembled, verbatim)

### 1.1 Two-column freeze table — S1 §6 (verbatim, full table)

> **Two-column freeze table. "Before" = must be in the frozen pilot prereg at T0 (launch);
> "After" = may be updated after the pilot, and this update *is* the legitimate purpose of the
> pilot.**
>
> | FROZEN BEFORE the pilot (T0) | May be UPDATED AFTER the pilot |
> |------------------------------|-------------------------------|
> | Pilot case list (10 ids, §2 table) + sha256 of the id list + sha256 of the downloaded case data files (per S7 download-manifest pattern) | **σ̂_D** (pilot-estimated between-case variance of the paired difference) and effective per-case σ |
> | Exclusion rule text (rules 1–3, §2) verbatim | **s** (per-arm saturation fractions; disclosed in every report) |
> | Arm set = {D-E, C-EQ} + BARO-feasibility scope (`~~8~~` 4 RE2-OB delay cases, feasibility label; 4-vs-8 defect closed at I4) | Recomputed MC power (pilot-σ variant cell set, the 10-line extension, run **before** final prereg freeze) |
> | Model id + endpoint label: SimulaChat default (Qwen3.8-27B), endpoint label `simulachat` (no credentials), temperature 0.2, MODEL-SUBSTITUTION label rule for external comparisons | **Δ_min confirmed at 0.15 (A1 candidate), or LOWERED with written justification + `rule_a1` re-run at the chosen value — never RAISED post-pilot** (raising converts POSITIVE_SUBTHRESHOLD→NOT_ESTABLISHED; lowering manufactures MEANINGFUL_POSITIVE). `~~(0.10 vs 0.15, C-SCI-9)~~` harmonized per J-SCI W2 **S-W2-5**: the A1 candidate 0.15 is the single candidate; 0.10 (D-V3-007) is superseded-candidate-for-the-record only. This is the confirmation/lowering-only path — it does not contradict the protocol A1 amendment ("fixed at freeze as Δ_min = 0.15"), which fixes the *starting* value; lowering with written justification is the only permitted post-pilot movement. The `rule_a1`@0.15 MC re-run is scheduled **before G4** (a separate worker is executing it now; cite as **pending-with-track**), so the freeze cites the exact variant. J-SCI + statistician sign-off required. |
> | Envelopes: 60,000 tokens / 900 s / 4 agents / ≤4 planner rounds / 1 consultation per investigator per case / C-EQ prompt-volume canary band frozen value = **[0.6, 1.25]** (the value, not a pointer — `~~pending S3 reconciliation~~` per S-W2-6; source: FROZEN-CONSTANTS appendix `PROMPT_VOLUME_FLOOR=0.6 / CEIL=1.25`; the 0.8-docstring-vs-0.6-code mismatch is disclosed as amendments conflict #3) | Heldout k (2/3/4) within the N=24 budget, per `monte_carlo_power_v3.md` §3.2 refinement 1 |
> | Seeds {20261011, 20261012} | The S-sat *outcome* (trip or not) — the rule itself (0.25) is frozen, never tunable |
> | Stop rules 1–4 verbatim, incl. crash threshold 25%, per-round token ceiling 2,880,000 (reset per round per §5.1; campaign worst-case 8,640,000), and the S-W2-1 model-capability floor gate (<2/20 run-level OR ≥9/10 per-case all-seeds=0 → MODEL-CAPABILITY-SCREEN-FAILED; the ladder does NOT run on a floor trip); **plus the §5.1 difficulty ladder table + the MAX-2-re-pilots / INCONCLUSIVE-STRATIFICATION cap, verbatim (S-W2-10)** | MDE re-scope (0.15 → 0.20) if the pilot-σ power shows 0.15 unattainable (this is a pre-declared consequence, not a tuning from outcome patterns — it executes a pre-registered branch) |
> | Estimator definitions: σ̂_D computed on paired per-case differences, k=2, cluster=case; s defined as all-seeds-success fraction; ITT (failed runs = non-success) | The re-pilot case list *only if* S-sat trips: next rung of the §5.1 pre-registered difficulty ladder (MAX 2 re-pilots; `~~"re-stratified re-pilot"~~` — S-W2-10); the 42 remain frozen either way |
> | **"No confirmatory reuse" clause verbatim:** pilot results cannot be reused as heldout evidence; no effect estimate / power claim / superiority statement is reported from the pilot; any parameter change not in the After-column requires a versioned amendment motivated by a pre-registered defect | (nothing else. Any additional "After" permission must itself be a versioned amendment) |

**Also frozen before T0 (carry-over conditions)** — S1 §6 (verbatim):
> - C-SCI-1 scorer-only gate (S1): required at T0 (unchanged).
> - C-SCI-2 L5 pin: **DONE** — `src/repliclaw/benchmarks/common/power_pin.py` +
>   `tests/benchmarks/test_l5_pin.py` in repo (W2c merged; shas `e14d28ad…` / `929d6fe9…`
>   re-verified by J-SCI W2).
> - C-SCI-3 canary band: **frozen value = [0.6, 1.25]** (the value is recorded, not a pointer
>   to a reconciliation event) — FROZEN-CONSTANTS appendix; amendments conflict #3
>   (0.8-docstring vs 0.6-code) is the disclosed 0.8 note and the one reconciliation item to
>   close before launch. `~~"G4-blocker, band pending"~~` framing removed.
> - J-CODE W2 verdict: **exists** — `reviews/CODE_JUDGE_WAVE2_20261010.md`,
>   **APPROVE-WITH-CONDITIONS**; conditions closed except **F-W2-12** (deferred to the G4 doc
>   pass). `~~"verdict clear"~~` updated to "verdict issued, conditions tracked".

### 1.2 Pilot case set — S1 §2 (operative rows, verbatim)

> **Dataset:** `data/cases.parquet` (735 rows; sha256 pinned in
> `manifest.py` `CASES_PARQUET_SHA256 = c49a288920dbba2e8e724679a14636d5c7eb2b45426bba14007ef79a6c0ab1bb`).

> | # | case id | suite | system | fault | service | rep |
> |---|---------|-------|--------|-------|---------|-----|
> | 1 | re1ob_adservice_cpu_1 | RE1 | ob | cpu | adservice | 1 |
> | 2 | re1ob_cartservice_cpu_1 | RE1 | ob | cpu | cartservice | 1 |
> | 3 | re1ob_adservice_delay_1 | RE1 | ob | delay | adservice | 1 |
> | 4 | re1ob_cartservice_delay_1 | RE1 | ob | delay | cartservice | 1 |
> | 5 | re2ob_checkoutservice_delay_1 | RE2 | ob | delay | checkoutservice | 1 |
> | 6 | re2ob_currencyservice_delay_1 | RE2 | ob | delay | currencyservice | 1 |
> | 7 | re2ob_emailservice_delay_1 | RE2 | ob | delay | emailservice | 1 |
> | 8 | re2ob_productcatalogservice_delay_1 | RE2 | ob | delay | productcatalogservice | 1 |
> | 9 | re3ob_cartservice_f1_1 | RE3 | ob | f1 | cartservice | 1 |
> | 10 | re3ob_adservice_f3_1 | RE3 | ob | f3 | adservice | 1 |
>
> All 10 verified disjoint from the 42 ids **and** from all 42 tuples (computed; §9).
> sha256 over the 10 sorted case ids, newline-joined:
> `955a462175200909577c8c71db64e3fc8f879c83f1a9028e307926c471503a02`

**Verification (this worker, 2026-10-11):** the id-list digest
`955a462175200909577c8c71db64e3fc8f879c83f1a9028e307926c471503a02` was
reproduced EXACTLY from the 10 §2 ids using the canonicalization
"10 ids, sorted lexicographically, `"\n"`.join`, **no trailing
newline**". No mismatch. (An initial recheck under a trailing-newline
canonicalization did not match; the no-trailing-newline reading is the
one that reproduces the frozen digest and is recorded here as the
operative canonicalization.)

### 1.3 Exclusion rules 1–3 — S1 §2 (verbatim)

> 1. **Heldout-id exclusion:** a pilot case must not be one of the 42 frozen heldout candidate
>    ids. The 42 are exactly the output of `select_heldout_cases` on the pinned parquet
>    (quota table in `manifest.py`: RE1-OB mem 5×2, RE2-OB cpu 5×2, RE2-OB mem 5×2,
>    RE3-SS f1 3×2, RE3-SS f3 3×2; reps 1–2). The explicit 42 ids:
>
>    RE1-OB mem: `re1ob_adservice_mem_1/_2`, `re1ob_cartservice_mem_1/_2`,
>    `re1ob_checkoutservice_mem_1/_2`, `re1ob_currencyservice_mem_1/_2`, `re1ob_productcatalogservice_mem_1/_2`
>    RE2-OB cpu: `re2ob_checkoutservice_cpu_1/_2`, `re2ob_currencyservice_cpu_1/_2`,
>    `re2ob_emailservice_cpu_1/_2`, `re2ob_productcatalogservice_cpu_1/_2`, `re2ob_recommendationservice_cpu_1/_2`
>    RE2-OB mem: `re2ob_checkoutservice_mem_1/_2`, `re2ob_currencyservice_mem_1/_2`,
>    `re2ob_emailservice_mem_1/_2`, `re2ob_productcatalogservice_mem_1/_2`, `re2ob_recommendationservice_mem_1/_2`
>    RE3-SS f1: `re3ss_carts_f1_1/_2`, `re3ss_front-end_f1_1/_2`, `re3ss_orders_f1_1/_2`
>    RE3-SS f3: `re3ss_carts_f3_1/_2`, `re3ss_front-end_f3_1/_2`, `re3ss_orders_f3_1/_2`
>
>    (42 total, re-derived by this worker from the quota table on the pinned parquet; J-SCI W1
>    A6 independently replicated the same 42.)
> 2. **Tuple exclusion (the operative anti-leak rule):** a pilot case must not share the
>    **(system, fault_type, root_cause_service)** tuple with any of the 42. … Tuple-exclusion is
>    the rule that guarantees the pilot cannot share a ground-truth scenario (and its telemetry
>    generation parameters) with the frozen heldout.
> 3. **Smoke-id exclusion:** also exclude the 10 BARO smoke case ids — verified to be exactly
>    the RE2-OB cpu heldout subset (`*_cpu_1/_2` × 5 services), already excluded by rule 1.

### 1.4 Stop rules 1–4 + §5.1 ladder — S1 §5/§5.1 (verbatim)

The four stop rules and the §5.1 difficulty ladder are frozen verbatim as
written in S1 §5 ("All stop checks run after each **case+seed+arm**
completes…") — rules 1 (S-sat, threshold 0.25, with (a) pilot-report
disclosure and (b) coarse-screen status "verbatim to carry into the
prereg"), 2 (per-arm crash rate, stop iff crash_A > 25%, ≥6 of 20 runs;
`aborted_budget` counts as a crash), 3 (budget envelope, 2,880,000
per-round ceiling; single-run 60,000 / 900 s), 4 (model-capability floor
gate; <2/20 run-level OR ≥9/10 per-case all-seeds=0 →
MODEL-CAPABILITY-SCREEN-FAILED; the ladder does NOT run on a floor
trip), and §5.1 (frozen ladder table, rungs L4–L8 non-empty; L1–L3
EMPTY by the anti-leak tuple-exclusion design; **MAX 2 re-pilots
total**; third trip → INCONCLUSIVE-STRATIFICATION → human) are adopted
here BY REFERENCE to the S1 text (doc sha §4), which is the source the
§6 freeze table itself freezes ("Stop rules 1–4 verbatim … plus the
§5.1 difficulty ladder table + the MAX-2-re-pilots /
INCONCLUSIVE-STRATIFICATION cap, verbatim (S-W2-10)"). Reproducing the
full ladder table here would duplicate frozen text; the freeze cites the
pinned S1 file and sha.

### 1.5 Decision rule — S3 §2.3 (verbatim)

> ### 2.3 Decision rule (frozen before heldout)
> - **MEANINGFUL_POSITIVE** iff the percentile 95% CI's **lower endpoint is
>   strictly > 0**.
> - Otherwise: **"not established"**. The word "negative" is **forbidden** in
>   the verdict for this contrast: a CI containing or below 0 at n cases is
>   absence of evidence for the predeclared alternative, not evidence of
>   harm or nullity (except where an explicit equivalence test was powered
>   and predeclared — none is, by default).
> - The point estimate and full CI are **always reported** regardless of
>   verdict, together with the per-case d_c values.

### 1.6 Minimum-effect floor A1 — S2 (verbatim, exact freeze wording)

> **Δ_min = 0.15 absolute per-case success difference.** Exact freeze wording (to be
> adopted verbatim at G4, subject to Science-Judge + statistician sign-off): *"A
> heldout is scored MEANINGFUL_POSITIVE iff the paired cluster-bootstrap 95% CI of the
> per-case difference (D-E minus C-EQ) lies entirely above zero AND the point
> estimate is at least Δ_min = 0.15 absolute per-case success difference. If the CI
> lies entirely above zero but the point estimate is below 0.15, the verdict is
> POSITIVE_SUBTHRESHOLD. If the upper CI endpoint is below −0.15, the verdict is
> HARM_SIGNAL and may be reported as a true harmful finding. Otherwise the verdict
> is NOT_ESTABLISHED."*
>
> (S2, §2 AMENDED 2026-10-10 block. The grid's `rule_a1` variant was simulated at
> Δ_min=0.10; if the frozen value 0.15 is held, the `rule_a1` variant must be
> re-run at 0.15 before freeze so the prereg cites the exact variant. — that
> re-run is `scripts/mc_rule015.py`, tracked pending-with-track per S1 §6.)

### 1.7 Inference algorithm frozen constants — S3 §2.2 (verbatim, operative lines)

> **Frozen constants:**
> - **B = 10,000** bootstrap replicates (matches P08 precedent; CI endpoint
>   MC error ≈ 0.001 at the 2.5th percentile, negligible vs. any plausible
>   effect scale).
> - **RNG: `numpy.random.default_rng(20261009)`** — numpy `Generator` with the
>   default PCG64 bit generator, fixed seed 20261009. Exact call pattern
>   frozen in the reference implementation (§8) so any rerun reproduces
>   bit-for-bit.
> - **Interval: percentile 95% CI** = empirical [2.5, 97.5] percentiles of
>   {θ*_1 … θ*_B}.

Reference implementation pin (S1 §6 C-SCI-2, verbatim in §1.1):
`src/repliclaw/benchmarks/common/cluster_bootstrap.py` sha256
`e14d28ad…` — **re-verified by this worker** (§3).

### 1.8 Power authority — S2 D-V3-008 + S4 (operative, verbatim core)

> S2 D-V3-008 power block (operative sentence): power authority is the
> Monte-Carlo simulation of the frozen one-sided percentile-bootstrap rule
> (254-cell grid, `science/monte_carlo_power_v3.md`), **SIMULATION-ONLY
> until re-run with pilot-estimated σ̂_D before prereg freeze** (T0+5).
> Recommended heldout design: N = 24 cases × k = 4 seeds/case, MDE = 0.20.

> S4 §3.2 item 3 (operative, verbatim core): … "with N=24, k=4, mid
> variance, the design has 84% power for Δ=0.20; the maximum Δ detectable
> at 80% power is ≈ 0.18", **recomputed with pilot σ̂_D** via this MC
> script (seed scheme + cells are reproducible; a pilot-σ variant cell set
> is a 10-line extension, to be run post-pilot, before prereg freeze).

S-sat guard (S4 §4): the one-arm s = 0.25 ceiling-saturation trip
probability at Δ=0 is the reason S-sat exists; saturation cells in the
grid are the S-sat gate's characterization, separate from power cells.

### 1.9 FROZEN-CONSTANTS — S2 appendix (operative values, verbatim core)

> S2 FROZEN-CONSTANTS appendix (table rows, operative values):
> - Bootstrap replicates B | **10,000** | `statistical_protocol_v3.md` §2.2 (L5); MC grid §1.1
> - Bootstrap RNG seed | **20261009** (`numpy.random.default_rng`)
> - Bootstrap RNG engine | **PCG64**
> - CI percentile | **95% (percentile method)**
> - C-EQ planner prompt static tail sha256 | `4df178e5124b8660033769aceb158c065151ebae2a8cacf20f209500821513dc`
> - C-EQ final-diagnosis prompt static head sha256 | `11150fa2b11206143ab1eee5b1d54efc28ae685e27f354ef733d3bb8984d0bcf`
> - C-EQ final-diagnosis prompt static tail sha256 | `45e7ab3c2111395d9522e14da6855e9cf0171f4a391ac176ffa246bd88c9aa85`
> - C-EQ prompt-volume canary band | **[0.6, 1.25]** (two-sided; floor 0.6 per code and
>   tests — … **[RECORDED-DECISION 2026-10-10 — conflict #3 RESOLVED: floor stays 0.6.]**)
> - L5 `cluster_bootstrap.py` sha256 | `e14d28add0ceb27bdef73daab268bf07041bd857d34ebd477e2793e0aa96258c`
> - L5 `monte_carlo_power.py` sha256 | `929d6fe99aed470080beb6df344e11b734e97e0ac44d9036bcc3abbd6844662a`
> - RCAEval `data/cases.parquet` sha256 | `c49a288920dbba2e8e724679a14636d5c7eb2b45426bba14007ef79a6c0ab1bb`
> - RCAEval `download_manifest.json` sha256 | `bffa99801535a029ec6bb5cbc65a2e99e4fe4747514ee7787254133b9e899812`
>   (pins 142 input files)

Stored-grid pin (S4 §5 "Scope, caveats, reproducibility", verbatim core):
> **Pinned results artifact (sha256, computed 2026-10-10, W2n):**
> `monte_carlo_power_v3_results.json` (scratch, 254 cells + meta) — sha256
> `22096e60c25ae6705c0ac6cb96fad4a43dad890d3ba70fe6cab9f5dcfadabe9a`;
> companion `monte_carlo_power_v3_results.md` (tables) — sha256
> `9f4dfe3dc7f73d8af04a0c161b3b4dfdf4a8f92044592f51afda95aa2e7d516e`. … any
> future re-run producing a different sha must be treated as a new artifact,
> not a silent replacement.

**Verification (this worker, 2026-10-11):** every pinned value above
recomputed and matched on the worktree/scratch copies (§3).

### 1.10 Amendments to carry into the freeze — S6 D-V3-013/014/015 (verbatim)

**D-V3-013** (2026-10-10T15:15+02:00, G4 human approval — human, via chat):
> Human decision, verbatim intent: "skip AIOpsLab! else approve all remaining!"
> - **(a) AIOpsLab: DECLINED.** … The V3 campaign scope is therefore Track-II (RCAEval) only.
> - **(b) APPROVED: heldout budget N=24 × k=4** (cost model per statistical_protocol_v3.md;
>   the heldout may be launched ONLY after the pilot completes without a stop-rule trip and
>   only after the G4 prereg freeze below).
> - **(c) APPROVED: G3 pilot launch** — per g3_pilot_spec_draft.md as amended through I3.2:
>   n=10 (frozen §2 set), k=2 seeds, arms {D-E, C-EQ} + BARO feasibility on 8 cases,
>   SimulaChat default Qwen3.8-27B (free tier, MODEL-SUBSTITUTION for external comparisons),
>   per-round token ceiling 2,880,000 (campaign worst-case 8,640,000, $0), wall plan ≤ 12.0
>   h/round, stop rules 1–4 verbatim (incl. S-W2-1 floor gate), §5.1 frozen difficulty ladder,
>   MAX 2 re-pilots.
> - **RATIFIED:** (i) 0.6 prompt-volume floor stays (amendments conflict #3 closed);
>   (ii) ladder rungs L1–L3 are empty by the anti-leak tuple-exclusion design and L4–L8
>   take over at T0; (iii) token ceiling scope = per-pilot-round.

**D-V3-014** (2026-10-11T17:05+02:00, G3 pilot outcome — orchestrator):
> Pilot #4 … stopped at case 3 with a GENUINE cohort-scale **stop-2_crash trip**:
> D-E-TELEM 6/20 = 0.30 > 0.25 …, C-EQ-TELEM 4/20 = 0.20 …; stop-1/3/4 not tripped;
> 663,214 / 2,880,000 round tokens. … verdict FEASIBILITY-FAILED (cause-mixed);
> NO effect estimate.
> **FROZEN-CONSEQUENCE (no orchestrator discretion):** per the frozen spec, a stop-2
> trip makes the pilot **NOT admissible for heldout launch** and stop-2 has NO §5.1
> ladder. T0+5/T0+6/T0+7 … are HELD. The frozen contingency is a **human decision**
> among: (a) stronger model for a re-pilot …, (b) versioned amendment …, or
> (c) record the negative/feasibility result … and stop.

**D-V3-015** (2026-10-10T20:45+02:00, stronger-model re-pilot authorized — human):
> Human decision, verbatim intent: "do stronger-model re-pilot and other things,
> i give you full permission. GO! Spin the fleet."
> Recorded as: **option (a) of the D-V3-014 frozen contingency — APPROVED**, with
> general permission for all remaining in-scope work ("other things").
> - **Re-pilot scope (frozen instrument unchanged):** same 10 cases, k=2 seeds, arms
>   {D-E-TELEM, C-EQ-TELEM}, 60K/run envelope, 900 s wall, 24-call tool budget, stop
>   rules 1–4 verbatim, fresh round 2 budget 2,880,000 tokens. Round 2 is the
>   frozen-spec re-pilot (counts against the "MAX 2 re-pilots" cap; exactly one
>   re-pilot is consumed). Round 2 is NOT confirmatory: … still no effect estimate.
> - **Model selection:** … candidate set from the SimulaChat catalog … Label for all
>   round-2 runs: MODEL-SUBSTITUTION (the chosen model id — NOT the official released
>   baseline), per D-V3-010 J-SCI rule.
> - **"Other things" (queued under this authorization):** T0+5 pilot-σ MC recompute
>   (both rounds), T0+6 final prereg freeze preparation (hashes + operative wording),
>   and heldout readiness **subject to** the frozen rule that the heldout launches only
>   if a pilot completes without a mandatory stop trip (stop-2/3/4) — i.e., the
>   round-2 outcome still gates T0+7. If round 2 trips stop-2 again, the frozen
>   contingency applies again (no third re-pilot: cap of 2 reached → human decision).
> - **Cost:** SimulaChat free tier per D-V3-010; no paid work authorized beyond what
>   the free tier provides.
> - **Spends no frozen scientific surface:** spec, roster, seeds, thresholds,
>   envelopes untouched; only the run-model label changes, which is exactly what the
>   frozen contingency prescribes.

**Model-amendment scope note (T0+6):** D-V3-015 changes only the
round-2 run-model label (the frozen contingency's prescribed change). The
Before-column "Model id + endpoint label" row is the T0 pilot-round
freeze (round 1, executed). This is NOT a rewrite of frozen text; the
amendment trail above is the operative record.

---

## 2. Heldout parameters (operative, per D-V3-013(b))

| Parameter | Value | Source |
|-----------|-------|--------|
| N (heldout cases) | **24** | D-V3-013(b); S4 §3.2 |
| k (seeds/case) | **4** | D-V3-013(b) |
| MDE (primary, post-pilot re-scope allowed) | **0.20** (Δ_min 0.15 frozen start; MDE 0.15→0.20 re-scope is a pre-declared After-column branch) | S1 §6; S2 D-V3-008 |
| Δ_min | **0.15** (lowerable with written justification + rule_a1 re-run; never raised) | S2 A1 block; S1 §6 |
| Inference | paired cluster bootstrap, B=10,000, seed 20261009 PCG64, percentile 95%, cluster=case, ITT | S3 §2.2/§2.3 |
| Decision rule | §1.5 + A1 floor §1.6 | S3; S2 |
| Power authority | MC grid only; pilot-σ recompute (T0+5) before freeze; SIMULATION-ONLY label | S2 D-V3-008; S4 |
| Heldout candidates | 42 frozen ids / 18 tuples (S1 §2 rule 1 table) | S1 §2 |
| Launch precondition | pilot completes without a mandatory stop trip (stop-2/3/4) AND G4 freeze | D-V3-013(b); D-V3-014/015 |
| S-sat guard | 0.25 threshold; heldout running canary = first 25% (6 cases, granularity 1/6) is the operative check (coarse-screen status, S1 §5 rule 1(b), verbatim) | S1 §5; S4 §4 |

**Heldout state at this draft:** NOT launched. Round 1 tripped stop-2
(D-V3-014) → heldout HELD; round 2 (D-V3-015) pending; its outcome still
gates T0+7.

---

## 3. Data-file hash table (computed + verified 2026-10-11 by this worker)

All sha256 computed with `shasum -a 256` on the worktree copy. "Claimed"
= the value the frozen docs pin. **ALL MATCH.**

| File | Computed sha256 | Claimed | Match |
|------|----------------|---------|:-----:|
| `data/cases.parquet` (pinned pilot/heldout cases index) | `c49a288920dbba2e8e724679a14636d5c7eb2b45426bba14007ef79a6c0ab1bb` | `c49a2889…ab1bb` (S1 §2; S2 FROZEN-CONSTANTS) | **MATCH** |
| `.artifacts/rcaeval/download_manifest.json` (S7 per-file manifest) | `bffa99801535a029ec6bb5cbc65a2e99e4fe4747514ee7787254133b9e899812` | `bffa9980…` (S2 FROZEN-CONSTANTS) | **MATCH** |
| `src/repliclaw/benchmarks/common/cluster_bootstrap.py` (L5 pin) | `e14d28add0ceb27bdef73daab268bf07041bd857d34ebd477e2793e0aa96258c` | `e14d28ad…` (S1 §6 C-SCI-2; S2) | **MATCH** |
| scratch `monte_carlo_power.py` (254-cell generator) | `929d6fe99aed470080beb6df344e11b734e97e0ac44d9036bcc3abbd6844662a` | `929d6fe9…` (S1 §6; S2) | **MATCH** |
| scratch `monte_carlo_power_v3_results.json` (254-cell stored grid) | `22096e60c25ae6705c0ac6cb96fad4a43dad890d3ba70fe6cab9f5dcfadabe9a` | `22096e60…abe9a` (S2) | **MATCH** |
| scratch `monte_carlo_power_v3_results.md` | `9f4dfe3dc7f73d8af04a0c161b3b4dfdf4a8f92044592f51afda95aa2e7d516e` | `9f4dfe3d…e7d516e` (S2) | **MATCH** |
| id list (10 sorted §2 ids, "\n".join, no trailing NL) | `955a462175200909577c8c71db64e3fc8f879c83f1a9028e307926c471503a02` | `955a4621…` (S1 §2) | **MATCH** |
| `docs/next_stage/data/download_manifest_pilot.json` (pilot telemetry manifest) | `fdc86dec5d395d023de127c3c6cd23986135aa9daf157d868a96c001b69111ea` | — (new, S7 pattern) | computed |
| `.artifacts/rcaeval/pilot/run/round1/pilot_report_round1.json` | `8c18cf0795c81ccfbd3edfd62a9c40f6226f22c8c4bb830ee92355b17e69fa94` | — (round-1 report) | computed |
| `.artifacts/rcaeval/pilot/run/round1/pilot_report_round1.md` | `783883e5c50cbcd5fc3f79f2e31199edcdd07c6816acd5e8a56968cc272fb819` | — (round-1 report) | computed |
| `docs/next_stage/data/t05_pilot_sigma_mc_round1.json` (T0+5 artifact, this worker) | `a130d674a0c4a3f8df55a99734d9905e9500418035c1853b0693c94ab1a3d7f3` | — (new, round-1 disclosure) | computed |

| `.artifacts/rcaeval/pilot/run/round2/pilot_report_round2.json` | `6769ad47def86ec9b4695dc3df4478903c4dba91aee488a3713300133f0e1939` | — (round-2 report; W3i variant caveat in EXECUTION_STATE I4.8) | computed |
| `.artifacts/rcaeval/pilot/run/round2/pilot_report_round2.md` | `8537c3845dd2e8948aaf3ac72767871a9b3db35eb26e5d2cd84f384afc87851c` | — (round-2 report) | computed |
| `docs/next_stage/data/t05_pilot_sigma_mc_round2.json` (T0+5 artifact, round 2) | `9c466c301cc6cb8f2d604c605f2fc42180bfff2c3575bf3dd08b1390a6e1e5d3` | — (new; round-2 INSUFFICIENT-ESTIMATE artifact, spec §2 fallback) | computed |
| `docs/next_stage/data/w3i_caching_investigation_20261011.json` (W3i BLOCKER-closure evidence) | `65dc166a6834ac0da670fff015d6afa4244555f7c3f50b50dcfd21352add867b` | — (new disclosure) | computed |

Round-2 telemetry manifest: **not yet generated** (the §7 download-manifest
pattern is regenerated at the T0 launch for the actual heldout telemetry; the
round-2 pilot telemetry lives under the gitignored `.artifacts/` tree, as for
round 1). Per the §1.1 After-column, σ̂_D / s are per-round disclosures.

---

## 4. Doc-sha table (frozen design docs currently operative)

Computed 2026-10-11 by this worker (`shasum -a 256`); these pin the
current operative text at the moment of this draft for the freeze
amendment trail.

| Doc | sha256 | Role |
|-----|--------|------|
| `docs/next_stage/design/g3_pilot_spec_draft.md` | `d94ede4adb7f8304a895532f5475184b5ad91a505aa6057fe60b5b0041eede1e` | S1 — pilot spec (freeze table §6, stops §5, ladder §5.1) |
| `docs/next_stage/EXPERIMENT_PROTOCOL_V3_DRAFT.md` | `d514a218c114dbd580c686f92970a44000f94ecba832c078ffe16642206df4db` | S2 — protocol + A1 + FROZEN-CONSTANTS |
| `docs/next_stage/science/statistical_protocol_v3.md` | `4818fdd101b9ca7daa4256e0b844605306ae5522e348aeb2abc3b0a4893a91db` | S3 — inference + decision rule + power |
| `docs/next_stage/science/monte_carlo_power_v3.md` | `39427b3cf5b8bf531066b3aba3fa9b302e0ad7eb400d2daf2311baa8cc65056a` | S4 — MC power authority |
| `docs/next_stage/amendments_AMEND_V3_FREEZE_20261010.md` | `f111ad60b16cbb099e04386ba2d5cdac67f6ea883a763b47fc92d1e30a4c4d48` | S5 — amendment log |
| `docs/next_stage/DECISIONS.md` | `abb6cefe4b4ab9d8c3c147edc6c376da12737ed423286db9fc32cc0a942ee832` (worktree state incl. D-V3-013/014/015; re-hash at stamp — this file may still receive the round-2 decision entry) | S6 — amendment decisions |
| `docs/next_stage/design/ceq_arm_design.md` | `e2b9fba64609cf52fa6a2d91da72c2495353dffd85cd766aa68088c5756451ca` | C-EQ arm design |
| `docs/next_stage/design/v3_telemetry_arm_addendum.md` | `0502b695b4a45c0938f2939944b1f953978225cfd6bc4e9f301c55b8b177dce2` | telemetry arm addendum |
| `docs/next_stage/design/a2_live_action_set_manifest.md` | `532e920e5b531389033823b1365246c9b90db5de0e3e82434844a681af58e3ef` | Track-I manifest (design-only) |
| `docs/next_stage/data/download_manifest_pilot.json` | `fdc86dec5d395d023de127c3c6cd23986135aa9daf157d868a96c001b69111ea` | pilot telemetry manifest |
| `docs/next_stage/data/baro_pilot_feasibility.json` | `e4d03211fe7273b5f4343b4e6686f83c5973ff001943e16e833343d2744b07aa` | BARO feasibility |
| `src/repliclaw/benchmarks/common/power_pin.py` | `5b2cd4be489e47924feb26178aad348859b45c5f966e2e56c20527cc5cdeeadb` | L5 pin harness |

---

## 5. Freeze effect clause

**This preregistration takes effect ONLY upon orchestrator/human stamp.**
The stamp consists of: (1) the orchestrator (with human approval) setting
`Status:` to FROZEN in the header above; (2) recording a **UTC
freeze date** and a **version** (e.g. `v1.0`); (3) recording the sha256
of this file at stamp time. Until that stamp is present, nothing in this
document is frozen and no heldout may be launched on its authority. The
round-2 pilot-σ input (T0+5) and round-2 report must be in place before
the stamp (per §1.1 After-column: "Recomputed MC power (pilot-σ variant
cell set …) run **before** final prereg freeze").

**Version: (blank — set at stamp). Freeze date UTC: (blank — set at
stamp). Stamp sha256: (blank — set at stamp).**

---

## 6. Post-freeze amendment clause

Any amendment after the freeze is effective ONLY as a **new version**
with a **new UTC timestamp + new version + human approval**, recorded in
`DECISIONS.md` as a versioned entry, and it must: (a) be motivated by a
pre-registered defect (per the §1.1 Before-column "No confirmatory
reuse" clause); (b) NOT raise Δ_min; (c) NOT touch the 42 heldout ids /
18 tuples, the seed set, the stop rules, the envelopes, the L5 pin, or
the decision rule except via the explicit After-column paths already
quoted above; (d) trigger a re-freeze (new version) before any heldout
launch. A parameter change not in the After-column requires a versioned
amendment motivated by a pre-registered defect. Any additional "After"
permission must itself be a versioned amendment.
