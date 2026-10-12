# V3.3 Heldout Feasibility Protocol (FF-06)

**Status: FROZEN (2026-10-12, post null-model amendment signoff).**

This is a **feasibility smoke**, NOT a powered confirmatory study. It tests
whether the pilot finding (D-E budget-thrash / C-EQ efficient completion)
reproduces on **independent unseen cases**. No effect estimate, power claim,
or superiority statement is made. §6 no-confirmatory-reuse applies to the
pilot; this heldout is a SEPARATE, prospectively-specified check.

## 1. Why N=3 (honest constraint)

The frozen pilot roster (`FROZEN_PILOT_IDS`, SHA256-verified in
`telemetry.py:61`) contains exactly 10 cases. The pilot (round 0) consumed
RCA-P-01 through RCA-P-07 (7 cases). Only **3 independent cases remain**:

| Opaque ID | Upstream ID | Fault family |
|---|---|---|
| RCA-P-08 | re2ob_productcatalogservice_delay_1 | RE2 delay |
| RCA-P-09 | re3ob_adservice_f3_1 | RE3 fault-injection |
| RCA-P-10 | re3ob_cartservice_f1_1 | RE3 fault-injection |

The RCAEval dataset has 735 cases total, but extending the frozen roster
requires a versioned amendment + re-freeze with independent signoff
(out of scope for this sprint). We do NOT fabricate a larger sample.

**Power reality:** N=3 × k=2 seeds = 6 paired observations (12 runs).
Exact binomial: 5/6 or 6/6 discordant pairs favoring one arm gives
one-sided p ≤ 0.031. This can detect a LARGE, CONSISTENT effect but has
no power to estimate a population effect size or bound type-I error at
conventional levels. The result is a **reproducibility check**, not a
confirmatory trial.

## 2. Design

- **Arms:** D-E-TELEM vs C-EQ-TELEM (identical to pilot).
- **Cases:** RCA-P-08, RCA-P-09, RCA-P-10 (never used in any prior run).
- **Seeds:** 20261011, 20261012 (same as pilot — paired within case).
- **Total runs:** 3 cases × 2 seeds × 2 arms = **12 runs**.
- **Caps:** IDENTICAL frozen values (MAX_TOKENS_PER_RUN=150000,
  MAX_TOOL_CALLS=48, MAX_LOGS_CALLS=4, MAX_TRACES_CALLS=4, 900 s wall).
- **Model:** SimulaChat `default` (Qwen3.8-27B), same as pilot.
- **Driver:** `scripts/pilot_parallel.py run --round 1` (new round number,
  new out dir; STOP.json guard prevents mixing with round 0).

## 3. Stop rules (unchanged from frozen spec)

All four stop rules apply verbatim (S-sat, crash >25%, token ceiling,
floor). With only 3 cases, S-sat (s ≥ 0.25 after any case completion)
will likely trip early if one arm saturates — this is CORRECT behavior
(halts waste) and the partial result is still informative for
reproducibility.

## 4. Success/failure criteria (pre-registered)

- **Reproducibility confirmed:** the SAME qualitative pattern holds —
  C-EQ completes + hits ranking on all/most runs; D-E exhausts budget
  without committing. This is a feasibility finding, not a statistical
  test.
- **Reproducibility NOT confirmed:** the pattern differs materially on
  unseen cases (e.g., D-E succeeds on some, or C-EQ fails). This is an
  equally valid negative finding — report it honestly.
- **Inconclusive:** too many crashes/timeouts to compare. Report as such.

## 5. Reporting

- Per-run table: case, seed, arm, status, tokens, wall_s, hit.
- Per-arm summary: completed/aborted_budget/crashed counts, hit rate.
- Contrast vs pilot: does the direction hold? Magnitude similar?
- NO p-value, NO confidence interval, NO "statistically significant"
  language. Use "consistent with" / "not consistent with" the pilot.
- Token cost per arm disclosed (matched cap ≠ matched spend).

## 6. Exclusions and constraints

- Pilot cases (RCA-P-01..07) are NEVER included.
- No prompt/cap/strategy changes between pilot and heldout (parity frozen).
- No post-hoc case selection (all 3 remaining cases run, regardless of
  expected outcome).
- If a case's data is missing/corrupt, it is excluded BEFORE the run
  starts (recorded here), not after seeing results.

## 7. Signoff

Null-model amendment signed off 2026-10-12 (human). This protocol is the
prospective freeze for the bounded heldout feasibility smoke. Execution
authorized under existing G4 resource scope (bounded local runs, no cloud).

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
