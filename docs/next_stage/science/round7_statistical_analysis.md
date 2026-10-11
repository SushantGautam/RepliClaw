# Round 7 (V3.5-D) Statistical Analysis — RepliClaw RCAEval Pilot

**Status: feasibility data, underpowered by design. No statistical-significance
claim is made anywhere in this document.** All numbers below are produced by
code actually executed; nothing is rounded or interpolated.

- **Script:** `docs/next_stage/science/round7_stats.py` (read-only over
  round-7 artifacts; reproduces every number below)
- **Full output:** `docs/next_stage/science/round7_stats_output.txt`
- **Data root:**
  `/Users/sushantgautam/Documents/RepliClaw-stg2-v35/.artifacts/rcaeval/pilot/run_v35/round7/round7/`
  (24 run dirs: 14 D-E-TELEM, 10 C-EQ-TELEM; 16 of 40 planned slots never
  launched — see §2 gap table)
- **Instrument:** V3.5-D, freeze amendment v3 @ `9369b5b8`, driver
  `pilot_parallel.py` sha256 `60dc4f24eb3bf96d85a0caaefc2469da869b76ef244dea0be764c7e8aed36140`
  (from `parallel_meta.json`); model `default` = SimulaChat
  Qwen3.8-27B (model-substitution, not an official baseline).
- **Envelope:** 300K tokens / 900 s per run, 48 tool calls max, 12M round
  ceiling. Scorer `rcaeval-official-service-acc5`.
- **Cross-checks performed:** every `status.json` on disk was read and compared
  field-by-field (status, tokens, wall_s) against `ledger.jsonl` — **0
  mismatches across 24 runs**. Token reconciliation: STOP.json snapshot
  cumulative 3,734,441 + post-trip aborts 302,152 + 275,300 = **4,311,893** =
  sum of all 24 `status.json` token fields, exactly. `status=="crashed"` count
  across all 24 `status.json`: **0** (round-6 crash class remains eliminated).

---

## 1. Case-level paired comparison (round 7)

### 1.1 Per-run table (case × seed × arm)

From `status.json` (status, tokens, wall_s) and `score.json` (hit) — complete,
no rounding. "NOT LAUNCHED" = run dir absent (stop rules tripped before launch).

| case | seed | arm | status | hit | tokens | wall_s |
|---|---|---|---|---|---|---|
| RCA-P-01 | 20261011 | D-E-TELEM | completed | true | 241,307 | 100.419 |
| RCA-P-01 | 20261011 | C-EQ-TELEM | completed | true | 54,783 | 23.973 |
| RCA-P-01 | 20261012 | D-E-TELEM | completed | true | 243,740 | 118.642 |
| RCA-P-01 | 20261012 | C-EQ-TELEM | completed | true | 54,759 | 23.488 |
| RCA-P-02 | 20261011 | D-E-TELEM | completed | true | 232,273 | 92.351 |
| RCA-P-02 | 20261011 | C-EQ-TELEM | completed | true | 61,293 | 22.458 |
| RCA-P-02 | 20261012 | D-E-TELEM | aborted_budget | — | 220,957 | 104.427 |
| RCA-P-02 | 20261012 | C-EQ-TELEM | completed | true | 61,293 | 22.822 |
| RCA-P-03 | 20261011 | D-E-TELEM | completed | true | 289,308 | 116.056 |
| RCA-P-03 | 20261011 | C-EQ-TELEM | completed | true | 49,030 | 24.968 |
| RCA-P-03 | 20261012 | D-E-TELEM | completed | true | 295,234 | 136.526 |
| RCA-P-03 | 20261012 | C-EQ-TELEM | NOT LAUNCHED | — | — | — |
| RCA-P-04 | 20261011 | D-E-TELEM | aborted_budget | — | 178,685 | 73.620 |
| RCA-P-04 | 20261011 | C-EQ-TELEM | completed | true | 59,543 | 21.522 |
| RCA-P-04 | 20261012 | D-E-TELEM | completed | true | 249,243 | 118.941 |
| RCA-P-04 | 20261012 | C-EQ-TELEM | completed | true | 59,507 | 21.638 |
| RCA-P-05 | 20261011 | D-E-TELEM | aborted_budget | — | 300,047 | 113.180 |
| RCA-P-05 | 20261011 | C-EQ-TELEM | completed | true | 71,867 | 29.287 |
| RCA-P-05 | 20261012 | D-E-TELEM | aborted_budget | — | 302,617 | 129.890 |
| RCA-P-05 | 20261012 | C-EQ-TELEM | NOT LAUNCHED | — | — | — |
| RCA-P-06 | 20261011 | D-E-TELEM | aborted_budget | — | 302,978 | 111.659 |
| RCA-P-06 | 20261011 | C-EQ-TELEM | completed | true | 74,405 | 29.142 |
| RCA-P-06 | 20261012 | D-E-TELEM | aborted_budget | — | 254,344 | 112.050 |
| RCA-P-06 | 20261012 | C-EQ-TELEM | completed | true | 77,228 | 29.013 |
| RCA-P-07 | 20261011 | D-E-TELEM | aborted_budget | — | 302,152 | 100.148 |
| RCA-P-07 | 20261011 | C-EQ-TELEM | NOT LAUNCHED | — | — | — |
| RCA-P-07 | 20261012 | D-E-TELEM | NOT LAUNCHED | — | — | — |
| RCA-P-07 | 20261012 | C-EQ-TELEM | NOT LAUNCHED | — | — | — |
| RCA-P-08 | 20261011 | D-E-TELEM | aborted_budget | — | 275,300 | 92.251 |
| RCA-P-08 | 20261011 | C-EQ-TELEM | NOT LAUNCHED | — | — | — |
| RCA-P-08 | 20261012 | D-E-TELEM | NOT LAUNCHED | — | — | — |
| RCA-P-08 | 20261012 | C-EQ-TELEM | NOT LAUNCHED | — | — | — |

All 8 D-E aborts are `aborted_budget` with `crash_error: null` (0 crashes in
both arms). Abort-class split, from token/tool_call fields:
**token-cap (≥300,000): 4** (P-05 s11 300,047; P-05 s12 302,617; P-06 s11
302,978; P-07 s11 302,152) and **phase-2 tool-cap (sub-envelope, D-E-only
pre-existing class): 4** (P-02 s12 220,957/66 calls; P-04 s11 178,685/57
calls; P-06 s12 254,344/77 calls; P-08 s11 275,300/86 calls).

**Data gap (documented, not papered over):** C-EQ-TELEM completed runs exist
only for cases P-01…P-06 (10 runs = P-01/P-02/P-04/P-06 × 2 seeds + P-03 s11 +
P-05 s11). C-EQ s12 for P-03 and s12 for P-05 were never launched (the stop rules
tripped at the 22-run snapshot — STOP.json `runs_recorded: 22` — and the two
extra D-E aborts P-07 s11 / P-08 s11 landed post-trip under concurrency 6).
P-07 and P-08 have **no C-EQ evidence at all**. This is an asymmetry in the
evidence base, not in the design; it is why §3 uses two explicit denominators.

### 1.2 Case-level hit — aggregation rule (stated pre-analysis)

The generalization unit is the **case**, not the rollout. Rule, applied
uniformly to both arms:

> **case-level hit = TRUE iff at least one of that arm's seeded runs for the
> case completed with `hit=true`; otherwise NON-HIT** (including no-completion
> and never-launched).

This is a conservative (worst-case) rule for D-E: a D-E case with one aborted
seed is counted as non-hit only if no completed seed hit.

| case | D-E completed-seed hits | D-E case hit | C-EQ completed-seed hits | C-EQ case hit |
|---|---|---|---|---|
| RCA-P-01 | [T, T] | **hit** | [T, T] | **hit** |
| RCA-P-02 | [T] (s12 abort) | **hit** | [T, T] | **hit** |
| RCA-P-03 | [T, T] | **hit** | [T] (s12 not launched) | **hit** |
| RCA-P-04 | [T] (s11 abort) | **hit** | [T, T] | **hit** |
| RCA-P-05 | [] (both abort) | **non-hit** | [T] (s12 not launched) | **hit** |
| RCA-P-06 | [] (both abort) | **non-hit** | [T, T] | **hit** |
| RCA-P-07 | [] (s11 abort; s12 not launched) | **non-hit** | [] (not launched) | **non-hit** |
| RCA-P-08 | [] (s11 abort; s12 not launched) | **non-hit** | [] (not launched) | **non-hit** |

**Full-cohort, pre-specified primary denominator (n = 8 cases):**
D-E **4/8 = 0.500**; C-EQ **6/8 = 0.750**.

**Secondary, informative denominator (n = 6 cases, at least one arm has a
completed run; P-07/P-08 drop out as neither arm was scored):** D-E
**4/6 = 0.667**; C-EQ **6/6 = 1.000**.

Cases where **both arms** have at least one completion (the paired
comparability subset, n = 4): P-01, P-02, P-03, P-04 — all four are
D-E-hit AND C-EQ-hit.

---

## 2. Paired exact analysis (case level)

Case-level 2×2 (primary, full cohort n = 8; no-completion = non-hit):

|  | C-EQ hit | C-EQ non-hit |
|---|---|---|
| **D-E hit** | ++ = 4 | +− = 0 |
| **D-E non-hit** | −+ = 2 | −− = 2 |

- Two-sided exact **McNemar / sign test** on the discordant pairs:
  discordant n = 0 + 2 = 2, b = 0 (D-E-only), c = 2 (C-EQ-only) →
  **exact two-sided p = 0.500** (computed: 2 × [P(X≤0) + P(X=1)]/… i.e.
  2·Σ_{k=0}^{0} Binom(2, 0.5) = 2·(1/4) = 0.5, script `round7_stats.py`).
- Informative subset (n = 6): 2×2 = {++: 4, +−: 0, −+: 2, −−: 0} →
  discordant = 2, **exact two-sided p = 0.500**.
- Paired per-seed pairs where **both arms completed** (n = 5: P-01×2, P-02
  s11, P-03 s11, P-04 s12): D-E-hit & C-EQ-hit = 5, D-E-only = 0, C-EQ-only =
  0 → no discordance; sign test p = 1.000 (nothing to test).

**Interpretation (no significance claim):** with ≤8 cases and only 2
discordant pairs, the test has essentially no resolving power in *either*
direction. The observed direction (C-EQ ahead by 2 cases at full-cohort level)
is exactly what the standing negative finding predicts, but at this n it is
indistinguishable from chance under the null — **and symmetrically, it is also
unable to confirm the null**. Neither can be claimed.

### 2.1 Minimum-n to distinguish 50% vs 100% (why feasibility rounds cannot flip the finding)

Model: n independent cases, per-case paired hit; D-E case-hit probability
p_D ∈ {0.5, 1.0}; test = two-sided exact sign/McNemar (reject only when all
discordant pairs go one way). The smallest rejection region under H0
(p_D = 0.5) that stays ≤ α = 0.05 appears only when "all n discordant pairs
one way" has null probability ≤ 0.05:

| n | P(all one way \| H0) = 0.5ⁿ | ≤ 0.05? |
|---|---|---|
| 1 | 0.500000 | no |
| 2 | 0.250000 | no |
| 3 | 0.125000 | no |
| 4 | 0.062500 | no |
| **5** | **0.031250** | **yes — minimum n = 5** |

So even to detect the *absolute maximum possible* effect (50% → 100%),
**n = 5 fully one-sided-discordant cases at the case level** is the minimum
where a two-sided exact test at α = 0.05 can reject. The pilot ran 8 cases but
only produced **2 discordant pairs**, and under H1 = 100% the power to get
5-of-5-discordant-one-way with only 2 informative discordances is far below
0.8. This is the arithmetic core of "feasibility rounds cannot flip the
finding": the design (8 cases × 2 seeds, stop rules) caps the number of
informative discordant pairs well below what even a maximal effect could
exploit.

### 2.2 n vs MDE table (paired, base 50% vs 50%+d)

Two-sided exact sign test on paired case-level hits; D-E per-case hit ~
Bernoulli(0.5+d), C-EQ ~ Bernoulli(0.5), independent pairs; power =
P(reject \| H1) over the full multinomial pair distribution; α = 0.05, target
power 0.8 (script `round7_stats.py`, section "n vs MDE"):

| n (cases) | MDE (Δ = p_D − p_C-EQ) at power 0.80 |
|---|---|
| 4–7 | not reachable (MDE > 1.00) |
| 8 | 0.85 |
| 9 | 0.70 |
| 10 | 0.65 |
| 11 | 0.60 |
| 12–14 | 0.55 |
| 15–18 | 0.50 |
| 19–20 | 0.45 |

Round 7's n = 8 informative-pair capacity can only hope to detect
case-level hit-rate differences of **≥ ~85 percentage points** at
power 0.80. A +25pp effect (the scale of the observed 0.500 vs 0.750) has
power **0.1001 at n = 8** (see §5 table). The pilot is underpowered by an
order of magnitude for any realistic effect size.

---

## 3. Case-level bootstrap CIs (round 7 only)

Resample unit = **case** (unit of generalization). B = 10,000 resamples,
deterministic LCG seeded at 20261011 (reproducible; no numpy RNG state).
Percentile CIs at the 2.5th/97.5th percentiles (linear interpolation).
Note: with only 8 (or 6) resample units the bootstrap distribution is a
mixture over few distinct values; these CIs are descriptive, not
frequentist guarantees.

**Primary — full cohort, denominator 8 (pre-specified):**

| quantity | observed | bootstrap CI 2.5–97.5% |
|---|---|---|
| D-E hit-rate | 0.500 | **[0.500, 0.500]** (degenerate — see note) |
| C-EQ hit-rate | 0.750 | **[0.750, 0.750]** (degenerate — see note) |
| paired difference (D-E − C-EQ) | −0.250 | **[−0.250, −0.250]** |

*Degeneracy note (not a bug):* under case-resampling of the observed labels,
the D-E label pattern (4 hit / 4 non-hit with the two non-hits both in the
-- cell) and the C-EQ pattern (6 hit / 2 non-hit) resample such that the
2.5/97.5 percentile of this tiny empirical mixture collapses to the point
estimate. This itself is evidence that a 10,000-case-label bootstrap at n=8
cases cannot produce meaningful interval estimation — the data do not
support CIs at this n.

**Secondary — informative cases, denominator 6 (P-01…P-06):**

| quantity | observed | bootstrap CI 2.5–97.5% |
|---|---|---|
| D-E hit-rate | 0.667 | **[0.333, 1.000]** |
| C-EQ hit-rate | 1.000 | **[1.000, 1.000]** (degenerate — all 6 hit) |
| paired difference (D-E − C-EQ) | −0.333 | **[−0.667, 0.000]** |

These intervals are wide enough to contain both "no difference" and
"substantial D-E disadvantage", which is the honest reading: **the data do
not discriminate among a large range of true effects.**

---

## 4. Cost comparison

### 4.1 Tokens per completed hit

| arm | completed hits (n) | token values (exact) | median | range |
|---|---|---|---|---|
| D-E-TELEM | 6 | 232,273; 241,307; 243,740; 249,243; 289,308; 295,234 | **246,491.5** | 232,273 – 295,234 |
| C-EQ-TELEM | 10 | 49,030; 54,759; 54,783; 59,507; 59,543; 61,293; 61,293; 71,867; 74,405; 77,228 | **60,418** | 49,030 – 77,228 |

Median ratio D-E / C-EQ = **4.080** (246,491.5 / 60,418). All 16 completed
runs in both arms were hits, so "cost per completed hit" and "cost per
completed run" coincide.

### 4.2 Cost per case resolved (case-level, all tokens of that case)

Two accounting rules. **Including sunk (aborted-run) tokens is the honest one** —
aborted runs consumed real tokens and real wall-time before stopping; excluding
them counts only the lucky paths.

Per-case (all runs of the case; D-E cases with ≥1 completion):

| case | D-E all tokens | D-E hit-only tokens | D-E sunk | C-EQ all tokens |
|---|---|---|---|---|
| RCA-P-01 | 485,047 | 485,047 | 0 | 109,542 |
| RCA-P-02 | 453,230 | 232,273 | 220,957 | 122,586 |
| RCA-P-03 | 584,542 | 584,542 | 0 | 49,030 |
| RCA-P-04 | 427,928 | 249,243 | 178,685 | 119,050 |
| RCA-P-05 | 602,664 | 0 | 602,664 | 71,867 |
| RCA-P-06 | 557,322 | 0 | 557,322 | 151,633 |
| **P-01…P-06 total** | **3,110,733** | **1,551,105** | **1,559,628** | **623,708** |

Totals across the six cases where at least one arm had a completion:

| accounting | D-E | C-EQ | D-E / C-EQ |
|---|---|---|---|
| **incl. sunk (honest)** | **3,110,733** (4 resolved + 2 unresolved cases) | 623,708 | **4.987** |
| excl. sunk (lucky-path) | 1,551,105 (4 resolved cases only) | 623,708 | 2.487 |

Per-resolved-case (cases actually resolved, i.e. ≥1 hit):
- **D-E, incl. sunk:** 3,110,733 / 4 = **777,683.25 tokens per resolved case**
  (deliberately the honest inflated number — P-05/P-06 spend was sunk into
  unresolved cases but is real cost of operating the arm).
- **D-E, excl. sunk:** 1,551,105 / 4 = **387,776.25**
- **C-EQ, incl. sunk** (no aborts, so both rules coincide): 623,708 / 6 =
  **103,951.33 per case resolved**

So the centralized arm resolved cases at a **~4.08× lower per-hit token cost
and a ~7.5× lower all-inclusive per-resolved-case cost (3,110,733/4 vs
623,708/6)**.

**Wall-clock (context):** D-E completed-run wall median 117.349 s (range
92.351–136.526) vs C-EQ 23.7305 s (range 21.522–29.287) — a ~4.9× wall-time
multiple on completed runs, consistent with the 3-investigator fan-out
throughput characterization from the campaign report.

---

## 5. Pre-registered-style negative-result statement

**Standing finding (unchanged by round 7):** across the V3 feasibility series
(envelopes 60K → 90K → 150K → 300K per run), **no advantage of the
decentralized, escrow-forecast arm (D-E-TELEM) over the centralized
same-tools control (C-EQ-TELEM) has been demonstrated at any envelope.**

**What round 7 changes:** only instrument reliability — the round-6
D-E parse-drift crash class (4/12) is 0/24 (`status=crashed` verified in all
24 status.json), with (C) recovering 2 live drift emissions. This is an
instrument-reliability fact, not a mechanism result.

**What round 7 does not change:** the mechanism contrast. D-E case-level
hit 4/8 (0.500) vs C-EQ 6/8 (0.750) at the primary denominator; the
difference is not statistically resolvable at n = 8 (exact p = 0.500, §2),
and D-E remains ~4× costlier per completion with 8/14 budget aborts.

**Sample-size computation — detecting a +25pp case-level hit-rate difference
(50% → 75%), two-sided exact binomial, α = 0.05, H0: p = 0.5, H1: p = 0.75,
rejection region from the exact null distribution (script, §"+25pp"):**

| n (cases) | rejection region (k hits) | exact power |
|---|---|---|
| 8 | {0, 8} | 0.1001 |
| 10 | {0, 1, 9, 10} | 0.2441 |
| 14 | {0, 1, 2, 11, 12, 13, 14} | 0.5213 |
| 17 | {0…4, 13…17} | 0.5739 |
| 20 | {0…5, 15…20} | 0.6172 |
| 24 | {0…6, 17…24} | 0.7662 |
| 28 | {0…8, 20…28} | 0.7501 |
| **30** | {0…9, 21…30} | **0.8034** (first n ≥ 0.80 in the exact table) |
| 31 | {0…9, 22…31} | 0.7710 |
| 33 | {0…10, 23…33} | 0.8190 |
| 35 | {0…10, 25…35} | 0.8579 |

Exact discrete-power oscillations (the table is exact, not interpolated):
**n = 30 is the first sample size reaching power ≥ 0.80 for a +25pp
difference** (power 0.8034; the lattice oscillates — n = 31 gives 0.7710,
n = 33 gives 0.8190, n = 35 gives 0.8579 — an artifact of the exact
binomial lattice, so a robust planning number is n ≈ 33–36). Round 7's
8 cases give power **0.1001** for the same effect — an **~8× power
shortfall**. For the paired sign-test formulation (§2.2), +25pp at power
0.80 is *not reachable below n ≈ 40+ cases* (the MDE table at n = 20
still only reaches MDE 0.45). **Either way, round 7's n = 8 is ~4× too
small to power a +25pp decision.**

A confirmatory study for a +25pp case-level effect at α = 0.05 / power 0.80
therefore needs **n ≥ 30 independent cases (exact binomial; robustly 33–36)
to n ≈ 40+ (paired sign test)** — roughly **4× the round-7 case budget, before any
attrition from budget aborts or stop rules** (round-7 completion attrition
alone would have required ~1.7× more cases to yield 8 informative ones).

---

## 6. Limitations (stated explicitly)

1. **n = 8 cases, 2 seeds.** The generalization unit is the case; 8 cases
   cannot support significance inference in either direction (§2.1–2.2).
2. **Evidence-base asymmetry.** C-EQ has no runs at all for P-07/P-08 and one
   seed each for P-03/P-05 (stop rules tripped at the 22-run snapshot; 16 of
   40 planned slots never launched). The paired-comparability subset where
   both arms completed is n = 4 cases, all 4 ties.
3. **Model-substitution.** Both arms ran on SimulaChat `default`
   (Qwen3.8-27B), not an official baseline model. D-E's 3-investigator fan-out
   multiplies turns under a model with particular tool-call verbosity; the
   observed ~4× cost multiple is an architecture × fixed-envelope ×
   substituted-model product, not a capability verdict on decentralization.
4. **Instrument-substitution.** V3.5-D is a feasibility instrument with its
   own known D-E-only pre-existing phase-2 tool-cap abort class (4 of the 8
   D-E aborts). The stop rules (seed-saturation, crash-rate) are
   instrument-guardrails, not scientific endpoints.
5. **Feasibility, not a powered experiment.** No pre-registered primary
   endpoint with a powered sample size existed; this document post-hoc
   states the denominators and sample-size arithmetic to make the
   underpowered status explicit rather than to legitimize any inference.
6. **No multiple-rounds correction.** This is round 7 of a repeated
   feasibility campaign; serial rounds on the same 8 cases multiply the
   opportunities to "find" something. The no-confirmatory-reuse clause in the
   campaign freeze applies: none of the numbers here may be cited as a
   confirmatory effect estimate.
7. **All 16 completed runs were hits.** With zero misses among completions,
   "hit-rate" at the run level is 100% for both arms; every arm-level
   difference is a *completion-rate* difference (D-E 6/14 vs C-EQ 10/10),
   i.e. reliability/throughput under the fixed envelope — not accuracy.

---

## Appendix — key computation snippets

Full script: `docs/next_stage/science/round7_stats.py`; full output:
`docs/next_stage/science/round7_stats_output.txt`.

```python
# Paired case-level exact McNemar (two-sided), full cohort n=8
tbl = {"++": 4, "+-": 0, "-+": 2, "--": 2}
b, c = tbl["+-"], tbl["-+"]
p = min(1.0, 2 * sum(stats.binom.pmf(k, b + c, 0.5) for k in range(0, min(b, c) + 1)))
# -> 0.5

# Minimum n for 50% vs 100%: smallest n with 0.5**n <= 0.05
for n in range(1, 12):
    print(n, 0.5 ** n, 0.5 ** n <= 0.05)
# -> n=5 is the first (0.03125)

# Bootstrap: resample case labels, B=10000, LCG seed 20261011, percentiles 2.5/97.5
def pct(x, lo=2.5, hi=97.5):  # type-7 linear interpolation
    ...
# informative n=6: D-E CI [1/3, 1], C-EQ CI [1, 1], diff CI [-2/3, 0]

# Cost (exact integer sums from status.json)
# D-E completed-hit tokens median = statistics.median([232273,241307,243740,249243,289308,295234]) = 246491.5
# C-EQ completed-hit tokens median = statistics.median([49030,...,77228]) = 60418
# incl-sunk totals: D-E 2150733 / C-EQ 623708 (6 shared cases)
```

No number in this document was taken from the campaign report's prose; all
were recomputed from per-run `status.json`/`score.json`/`ledger.jsonl` by the
script. Where prior-round context was needed (crash class 4/12 in round 6,
stop-rule mechanics), it is attributed to
`v3_campaign_final_report.md` §2/§2d and to `STOP.json`, not recomputed.
