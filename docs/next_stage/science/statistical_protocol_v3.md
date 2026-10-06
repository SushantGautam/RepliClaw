# Statistical Protocol V3 — RepliClaw Stage 2

**Status: DRAFT — NOT PREREGISTERED. NOT signed off. No experiment may be
authorized against this document until it is frozen (v3.0), timestamped, and
dual-signed per §9. Version: v3-draft-0 (2026-10-09, L5 statistics & protocol
team). Supersedes: nothing — P08 prereg v1.2 and its results remain immutable
and historically valid; this document defines NEW estimands only.**

Companion: `docs/next_stage/EXPERIMENT_PROTOCOL_V3_DRAFT.md` (arms, tracks,
governance). This document owns only the statistical decisions.

---

## 1. Unit of inference and primary estimand

**Unit of inference: the independent failure case.** A *case* is one
independently authored fault/scenario (its own environment state, labels,
evaluator input) with no shared content or derived mutations of another
scenario in the same campaign. A *rollout* (case × arm × seed) is **not** a
unit of inference; seeds are **nested in cases**. All CIs, p-values, power
calculations, and the claim of generalization refer to cases, never to
rollouts. (P08's [0.60, 0.95] CI over 20 rollouts of one case is a
within-case CI; it is retained as single-case evidence of the
counterfactual-intervention mechanism and must never be cited as
generalization evidence.)

**Arms (track I):** D-E (decentralized + escrow), C-EQ (intervention-matched
adaptive centralized manager, honest strong baseline). Secondaries: D-N, D-R,
C-NE, S-I (§3).

**Per-case arm outcome.** For case c with seeds s = 1..k_c, define the
per-case arm success rate

    p_c(a) = (1/k_c) · Σ_s 1[ rollout(c, a, s) is a success ]

where *success* is the track's primary binary correctness criterion (e.g.,
exact root-cause class per the benchmark's official evaluator).

**Primary estimand (case-paired, ITT):**

    θ_primary = E_c [ p_c(D-E) − p_c(C-EQ) ]

with **equal case weighting** (each case contributes 1/n regardless of seed
count or spend) and **intention-to-treat** scoring: any rollout that failed,
timed out, aborted, or abstained from a diagnosis counts as **non-success
(0)** in both the numerator and denominator of p_c. No run is dropped from
the primary estimate. The estimand answers: "for a randomly drawn case from
this case population, does D-E succeed more often than C-EQ?"

## 2. Inference: cluster (case-level) paired bootstrap

### 2.1 Why not run-level bootstrap
The k seeds (or 20 rollouts, as in P08) of one case are exchangeable
replications of **one** experimental unit, not independent observations.
A run-level bootstrap (resampling rollouts independently) treats nested
seeds as independent, so the CI shrinks by roughly √(seeds per case) for
every added seed and — as P08 demonstrated — can read [0.60, 0.95] while
the generalizable evidence base is a single case. Run-level resampling also
ignores the between-case variance that dominates the true standard error of
θ_primary. Only resampling **cases with all their seeds attached** targets
the correct sampling unit and yields an honest generalization CI.

### 2.2 Algorithm (exact, to be frozen)
Given per-case differences d_c = p_c(D-E) − p_c(C-EQ), c = 1..n:

1. Compute d_c for every case (seeds already pooled into p_c).
2. Resample **case indices** with replacement: draw (c_1, …, c_n) i.i.d.
   uniformly from {1..n}. The case's entire seed block moves as one unit
   (equivalently — and as in the reference implementation — resample on the
   d_c vector, which is algebraically identical).
3. Statistic: θ*_b = (1/n) Σ_c 1[c ∈ S_b] · d_c (equal case weighting).
4. Repeat.

**Frozen constants:**
- **B = 10,000** bootstrap replicates (matches P08 precedent; CI endpoint
  MC error ≈ 0.001 at the 2.5th percentile, negligible vs. any plausible
  effect scale).
- **RNG: `numpy.random.default_rng(20261009)`** — numpy `Generator` with the
  default PCG64 bit generator, fixed seed 20261009. Exact call pattern
  frozen in the reference implementation (§8) so any rerun reproduces
  bit-for-bit.
- **Interval: percentile 95% CI** = empirical [2.5, 97.5] percentiles of
  {θ*_1 … θ*_B}.

**Percentile vs. BCa — decision: percentile.** Justification:
(a) n will be small (tens of cases), where BCa's bias-correction term `a`
is estimated from a jackknife on the same tiny sample and is itself
high-variance, often producing unstable intervals; (b) at our effect scale
(case success differences in [−1, 1]) the skew of the bootstrap
distribution is mild; (c) the decision rule is one-sided (§2.3) — the only
CI property consumed is whether the *lower* endpoint is > 0, and the
percentile lower endpoint is conservative (wider) relative to BCa for
mildly skewed statistics; (d) auditability: percentile intervals are a
two-line function of the resample stream, trivial for a judge to recompute.
Sensitivity: the frozen analysis will additionally report the BCa lower
endpoint as descriptive (same RNG, B); if the two disagree on the decision,
the **percentile** result stands (frozen in advance) and the discrepancy
is disclosed.

### 2.3 Decision rule (frozen before heldout)
- **MEANINGFUL_POSITIVE** iff the percentile 95% CI's **lower endpoint is
  strictly > 0**.
- Otherwise: **"not established"**. The word "negative" is **forbidden** in
  the verdict for this contrast: a CI containing or below 0 at n cases is
  absence of evidence for the predeclared alternative, not evidence of
  harm or nullity (except where an explicit equivalence test was powered
  and predeclared — none is, by default).
- The point estimate and full CI are **always reported** regardless of
  verdict, together with the per-case d_c values.

## 3. Multiplicity

- **Primary:** θ_primary (D-E vs C-EQ) is **unadjusted**. It is the single
  predeclared primary contrast; the §2.3 decision rule applies to it alone.
  No multiplicity penalty — one primary, one rule.
- **Secondary contrasts** (D-E vs D-N, D-E vs D-R, C-EQ vs C-NE, D-E vs
  S-I, plus C-NE vs D-N if included): treated as **confirmatory-mechanism,
  multiplicity-adjusted** — each tested with the identical cluster
  bootstrap but at the Bonferroni-adjusted level: for m predeclared
  secondaries, CI level = 1 − 0.05/m (e.g. m = 5 → **99.0%**).
  "Meaningful positive (adjusted)" iff that CI's lower endpoint > 0.
  Rationale: Bonferroni is distribution-free (composes with the bootstrap
  CI), transparent, and FWER ≤ 0.05; it is conservative at n in the tens,
  which is acceptable because secondaries are mechanistic diagnostics, not
  the headline claim. The family size m is frozen at preregistration;
  adding a contrast later requires a versioned amendment (§5.3) and restarts
  the adjusted family.
- **Everything else** (per-arm cost/spend, M2/M11-style process metrics,
  no-intervention arm, C-OracleSelection, cross-track results):
  **descriptive only**, labeled `DESCRIPTIVE` in all outputs, never
  decision-gating.

**Mandatory counterevidence carry-over (P08 negative finding preserved):**
in P08, no-escrow (A1) and random-selection (A3) arms that ran the *same*
counterfactual interventions also scored M1 = 1.000, identical to S5. This
is a **negative finding about escrow and selection strategy** — the effect
was attributable to the intervention mechanism, not to decentralization or
escrow. In V3, whenever D-N or D-R replicates D-E's case-level success, the
report must state this attribution limit explicitly before any D-E claim
(counterevidence-first, §5.5).

## 4. Power and sample size

### 4.1 Pilot (variance estimation, not confirmation)
- **Design:** n_pilot = 6–10 independent cases × k = 2 seeds × arms {D-E,
  C-EQ, and secondaries included in the pilot track}. Pilot cases are
  **segregated and never reused** in the heldout set.
- **Purpose:** estimate (i) within-case rollout variance
  σ²_within (per arm; for a binary outcome ≈ p̂(1−p̂)/k) and (ii) the
  **between-case variance of the paired difference**
  σ²_D = Var_c(d_c) — the only quantity the cluster bootstrap's SE
  depends on: SE(θ̂) ≈ σ_D/√n.
- **No effect-size or p-value claims** may be drawn from the pilot; its
  output is the variance estimate feeding §4.2 plus a go/no-go on
  feasibility/ceiling (§4.3).

### 4.2 Case-count formula
For 80% power at two-sided α = 0.05, normal approximation to the
case-mean test (θ̂ is an average of n exchangeable d_c, so this is better
behaved than a run-level proportion test):

    N = (z_{1−α/2} + z_{0.80})² · σ²_D / MDE²
      = (1.96 + 0.842)² · σ²_D / MDE²
      ≈ 7.85 · σ²_D / MDE²

Round up to the next integer, then set final N = max(formula result,
feasibility floor from the V3 protocol, planning target ≥ 24 cases / ≥ 3
fault families / ≥ 2 systems) and lock it via the prereg after the pilot.

**Assumptions (state in prereg):** (a) d_c is approximately exchangeable
across cases (case execution order counterbalanced); (b) σ̂_D estimated
without substantial error — with n_pilot ≈ 8 it has wide uncertainty, so
**inflate: use σ̂_D · 1.3** (coverage cushion) unless n_pilot ≥ 12;
(c) MDE is predeclared *before* pilot results are consulted (open
question Q2, §7).

### 4.3 Ceiling-saturation risk — honest power reporting
P08 showed three arms at M1 = 1.000. If D-E or C-EQ saturates at 1 on many
cases, d_c variance collapses and θ̂ has a hard ceiling at the fraction of
cases the other arm misses; "80% power" then becomes an uninformative
number. Required handling:
- Report **attained detectable difference** instead of nominal power when
  saturation is present: "with N cases the analysis has 80% power to detect
  MDE = (z_{.975}+z_{.80})·σ̂_D/√N, provided d_c variance remains ≥ the
  pilot estimate; per-arm saturation at 100% on >50% of pilot cases
  invalidates this statement."
- If the pilot shows **both** arms at ceiling (all d_c = 0), the campaign
  must declare the case population **too easy** and escalate to
  harder/different cases via a versioned amendment (§5.3) — not run the
  frozen N and report "not established" on an uninformative metric.
- Per-arm success rates and the saturation fraction are mandatory report
  items so readers can judge whether a "not established" verdict is
  informative or a ceiling artifact.

## 5. Contingency, stopping, and reporting

### 5.1 Arm failures, abstentions, timeouts
- **ITT rule (primary):** every scheduled rollout is in the denominator.
  Timeout, abort, crash, retry-exhaustion, or abstention = 0. The reason is
  recorded in the metadata sidecar and reported as a per-arm
  *execution-integrity rate* (descriptive), so a verdict is never silently
  confounded by differential breakage.
- **Parity guard:** if per-arm completion rates differ by > 10 percentage
  points, the primary verdict is reported as
  **`VERDICT_VALID_WITH_INTEGRITY_CAVEAT`** plus a **clean-run sensitivity
  analysis**: identical bootstrap restricted to cases/seeds where *all*
  arms completed (labeled `SENSITIVITY`; can corroborate or warn, but cannot
  by itself promote a not-established verdict to positive).
- Retries are bounded (predeclared per rollout), each retry logged; a
  rollout that succeeds only after retries counts as success but the retry
  is disclosed in cost accounting.

### 5.2 Stop rules (predeclared; S1/S5 style)
- **S1 (integrity):** > 25% rollouts aborted in any arm → stop that arm's
  further cases; analyze completed cases as-is (ITT); disclose.
- **S2 (leakage):** any confirmed oracle/answer leakage → stop the campaign,
  invalidate affected runs, versioned amendment before any resumption.
- **S3 (no-peek):** **no interim look at the primary CI** during the
  heldout. The §2.3 decision is computed exactly once, on the full frozen
  case set, after scoring completes. Execution monitoring (liveness, token
  spend, parity) is allowed; outcome monitoring is not.
- **S4 (cost):** cumulative spend beyond the frozen budget → stop, analyze
  completed cases, disclose truncation.
- **S5 (metric degeneration):** if a primary-arm metric is structurally
  unanswerable (all-null canary, per the P08 round-3 lesson) → verdict is
  the distinct void state `METRIC_DEGENERATE`, not a decision; pre-bootstrap
  veto only, never a data filter.

### 5.3 Preregistration integrity
- The frozen prereg snapshot (this protocol + benchmark manifest + N, seeds,
  arms, caps, decision rules, RNG constants) is timestamped and hashed; the
  hash is recorded at authorization.
- **No post-hoc amendment** to estimand, arms, N, decision rule, or the
  multiplicity family after the hash is set. If an amendment is genuinely
  required (e.g., S2/S5 fires, benchmark access breaks), it is a
  **versioned amendment record** (`v3.Amendment-k`: reason, severity, dual
  sign-off) that supersedes forward-looking scope only; already-scored runs
  keep the version under which they ran. P08 files remain immutable
  regardless.
- No prompt/scorer tuning after any heldout outcome is observed; a failed
  metric definition triggers a §5.3 amendment with transparency, never
  silent re-scoring.

### 5.4 Evaluator isolation and heldout separation
- Evaluator answers (oracle labels) are stored outside all agent-visible
  context; the scorer is blind to arm identity; leakage canaries must pass
  at G2 before any heldout case runs.
- **Heldout separation:** pilot, parity, canary, and heldout cases are
  disjoint case sets, all enumerated in the frozen manifest; no heldout case
  may be used in development, prompt iteration, or scorer debugging at any
  point, including after a stop.
- Contamination: benchmark items may exist in model training data. We
  measure risk (case provenance, near-duplicate checks where feasible) and
  report it; we do not assert secrecy of the heldout from the models.

### 5.5 MANDATORY negative / inconclusive reporting
Every campaign outcome — including MEANINGFUL_POSITIVE — must publish:
1. **Counterevidence first**: the arms/results that do *not* support the
   headline claim, and attribution limits (§3 carry-over: if D-N or D-R
   replicate D-E, the escrow/selection claim is negated by those arms and
   must be stated before any D-E claim).
2. Point estimate, CI, per-case d_c table, per-arm success rates, saturation
   fraction, execution-integrity rates, and the exact verdict string from
   §2.3/§5.2.
3. If the verdict is "not established": an explicit statement that this is
   **not evidence of absence**, the MDE the design *would* have detected at
   80% power (§4.2), and whether ceiling saturation makes the metric
   uninformative (§4.3).
4. Full failure/abstention log and the clean-run sensitivity result (§5.1).
5. RNG seed, B, SHA of the analysis script, and prereg hash, so any judge
   can recompute the verdict bit-for-bit.

## 6. Preregistration template (structural skeleton)

The frozen prereg for a track-I campaign MUST contain exactly these
sections (skeleton; values are filled and then frozen):

    PREREG V3-TRACK-I / <campaign-id>
    1.  Identity: campaign id, date, track, benchmark + version + sha +
        split, license/access status (G0), case manifest hash
        (disjoint from pilot).
    2.  Estimator (verbatim from §1): estimand formula, success
        definition, ITT rule, equal case weighting.
    3.  Arms and intervention matching: arm list, caps (tokens/time/calls/
        agents), action-vocabulary hash, matched-cap statement,
        no-overrun rule.
    4.  Design: N cases, k seeds/case (predeclared set),
        fault-family/system strata, counterbalanced order, pilot-case
        exclusion statement, power basis (σ̂_D, MDE, inflation factor).
    5.  Inference (verbatim from §2): B, RNG spec, percentile 95%,
        decision rule wording incl. the forbidden-"negative" clause.
    6.  Multiplicity (verbatim from §3): primary unadjusted; secondary
        family list and m; Bonferroni level; descriptive list.
    7.  Stop rules (verbatim from §5.2): S1–S5 with thresholds.
    8.  Failure/abstention/timeout handling (verbatim from §5.1).
    9.  Contingency reporting obligations (verbatim from §5.5).
    10. Freeze & sign-off: prereg hash, freeze timestamp, two-key sign-off.
    AMENDMENT LOG (append-only): none at freeze.

**Freeze rules:** any change to sections 1–9 after hashing is an
amendment, not an edit; the amendment record states what changed, why,
which sections, and re-signs both keys. A campaign may run only against the
hash named in its authorization. **Two-key sign-off:** the independent
Science-Judge key covers statistical/scientific validity; the human key
covers authorization and budget. Neither key is delegated. A campaign
missing either key is `UNAUTHORIZED` and its results are out-of-protocol
(reportable only as descriptive).

## 7. Open questions (need human / program decision)
1. **k (seeds/case) for heldout:** 2 vs 3. More seeds reduce within-case
   noise in p_c but do not shrink the generalization CI; cost is linear.
   Proposal: k = 2 (matching pilot), pending budget.
2. **Predeclared MDE** for §4.2 (e.g., 0.15 vs 0.25 case-success
   difference): must be set by the program *before* pilot results are
   consulted.
3. **Secondary family size:** keep exactly 5 Bonferroni-adjusted secondaries
   (incl. C-EQ vs C-NE) or mark D-E vs S-I descriptive-only, given
   parallelism is an intrinsic architectural asymmetry (V3 draft, arms).
4. **Observational tracks (O-A AgentRx, O-R RCAEval):** this protocol only
   covers track I; those tracks need their own frozen estimand documents.
5. **Pilot feasibility:** if the independently-authored case pool is < 6,
   the protocol assumption breaks; human must confirm pool availability
   before G3.

## 8. Reference implementation (simulation-validated)
- Location: `/Users/sushantgautam/Documents/stg2-worktrees/statistics/cluster_bootstrap.py`
  (scratch; to be copied into the campaign repo at G3 with a unit test).
- **Label: SIMULATION** — validates estimator mechanics on synthetic paired
  case data; produces no RepliClaw measurement.
- Verified run (2026-10-09, `python3 cluster_bootstrap.py`):

      self-test PASSED
        effect case:  d_bar=0.361  CI95=(0.222, 0.486)  -> MEANINGFUL_POSITIVE
        null case:    CI95=(-0.069, 0.194)  -> NOT_ESTABLISHED

  Self-tests assert: (a) a strong synthetic effect yields CI lower > 0;
  (b) a true null (same per-case p for both arms) yields a CI containing 0;
  (c) output is bit-for-bit deterministic under the frozen seed.
- Frozen API: `np.random.default_rng(20261009)`, B = 10,000, percentile
  [2.5, 97.5], case-index resampling via
  `rng.integers(0, n, size=(B, n))`.
