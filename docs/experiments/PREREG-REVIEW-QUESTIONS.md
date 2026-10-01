# P08 Pre-Registration — Science-Judge Review Questions

Each question below maps to a section of `PREREG-2026-10.md` (cited inline). A **YES** (or the specified selection) is required to approve; any **NO** blocks the live window until the prereg is revised and re-reviewed. Record answers in the judge scorecard per `docs/fleet/JUDGES.md`, then record approval in `EXECUTION_STATE.md`.

---

## A. Scientific validity

**Q1 — S3 definition (REVIEW gate for deviation D-1; prereg §3, §11).**
Do you accept S3 as the P05 `AdaptiveCentralManager` (reused `repl_claw` evidence-driven re-planning, n = 3 fixed) as "adaptive central manager — dynamic role assignment", or do you require a purpose-built dynamic role-assignment implementation before the window?
*Block condition:* NO → S3 must be re-implemented and re-tested (19-test bar) or the S3 column of RQ2 is descope-declared.

**Q2 — Falsifiable predictions (prereg §2).**
Are P1–P4 falsifiable as written, and is the "negative = publishable" framing acceptable for each? Do any of them embed an unfalsifiable hedge (e.g., a noise floor that could be moved after seeing results)?
*Note:* the noise floor for S4 (prereg §8.1 S4) is pre-registered as "bootstrap difference CI upper bound < 0 confirmed in the first 10-run interim" — confirm that floor is acceptable.

**Q3 — Statistical plan (prereg §7.2).**
Do you accept that the primary comparison (S5 vs S4, n_cases = 1) is **descriptive with bootstrap CIs only**, with no inferential test reported, and that case-level inference for RQ4 is limited to a sign-consistency check (no McNemar/t-test across 2 cases)?
*Block condition:* NO → specify the minimum inferential design you require (which implies more cases or a different unit of analysis, i.e., a protocol-level change).

**Q4 — Metric definitions (prereg §6).**
Confirm the exact denominators: M1 denominator = per-arm `N_run` (never pooled); M11 denominator = preregistered falsifiable hypotheses *with an attempted falsification*; M7 aborts excluded from M1 with a stated sensitivity re-computation. Any denominator you disagree with must be named here.

**Q5 — Counterevidence rule (prereg §8.1 S4, §8.2).**
Do you accept that counterevidence to EESS (S5 losing to S4 beyond the pre-registered floor) does **not** stop the runs, that the campaign continues to completion, and that the report leads with the falsification? Confirm the "counterevidence section before positive results" ordering is mandatory.

## B. Matched-budget integrity

**Q6 — Envelope (prereg §5.1, DECISION-1).**
Confirm the per-arm envelope: **60,000 tokens / 900 s / 3 concurrent agents**, with master ceiling **10.8M tokens** and parallelism ≤ 2. Note the 60k figure is *derived* from the M9 demo floor (`acaefbb`: 2,565–2,749 tokens per full 3-agent run) at ~20× headroom, and is **not** a measured capacity. If you resize, state the new value; the master ceiling recomputes proportionally.

**Q7 — Parity mechanism (prereg §5.2).**
Do you accept that "matched budget" is proven by (a) identical envelope hash across all arms of a case, (b) hard `BudgetOverflow` abort at the ceiling, and (c) a post-run `assert_budget_parity` — and that **equal consumption is an outcome (M5/M6), not a parity requirement**?
*Block condition:* NO if you require consumption parity (equal spend); that is a different experiment (budget-matching by feedback) and would need its own prereg section.

**Q8 — Runs per arm (prereg §7.1, DECISION-2).**
Confirm 20 runs/arm (primary) and 10 runs/arm (secondary), justified as a **resource-constraint statement, not a power analysis**. If you reduce to 10/arm primary, M10 (verdict stability) becomes descope-declared — acceptable?

## C. Scope and descope decisions

**Q9 — Arm set (prereg §3, D-3, DECISION-3).**
Do you accept running **S0, S3, S4, S5, A1, A3** and excluding A2 (no counterfactual) and S2 (static roles) from this window? If you require A2, the window extends and the prereg is versioned v1.1 — confirm which.

**Q10 — A1 definition (prereg §3, D-4, DECISION-4).**
Select one: **(a)** A1 = S5 with escrow replaced by pass-through (need-market kept) — isolates escrow value via A1 vs S5 and market value via A1 vs S4; or **(b)** A1 = S4 plus one need-market negotiation cycle. The choice fixes which scientific contrast A1 serves; pick explicitly.

**Q11 — Secondary case / RQ4 (prereg §4.2, D-5, `[PENDING: P06]`).**
Do you accept the descope rule: if P06 has not landed a verified Tox21 case package (P02 verification bar: deterministic engine + replay + leakage test) by window start, RQ4 is **descope-declared and reported as not-run**, not silently dropped?

## D. Safety, leakage, and conduct

**Q12 — Oracle isolation (prereg §4.1, §8.1 S1).**
Confirm the three-layer oracle isolation: (1) P02 `test_oracle_not_leaked` re-run as pre-flight; (2) arms run from the non-oracle case directory per `EESS_CONTRACTS` §6 with a teardown re-grep (M4); (3) the scorer is a separate entrypoint receiving the oracle only after artifacts are sealed. And confirm the consequence: **any single leakage incident stops the entire campaign** with full evidence preservation.

**Q13 — Hard budget enforcement (prereg §5.2, §9.1).**
Confirm the harness (not the model) is the enforcement point: `BudgetLedger.record()` raises `BudgetOverflow` and aborts the run at the envelope, with overruns impossible by construction and missing usage fields invalidating a run rather than being estimated.

**Q14 — Authorization and window (prereg §9.2).**
Confirm: (a) start requires **both** science-judge approval (this sign-off) **and** human operator authorization, both recorded in `EXECUTION_STATE.md`; (b) window 2026-10-10 → 2026-10-23 UTC, shortenable by you but not extendable without re-review; (c) no worker (LLM-API-forbidden role) may trigger live runs.

## E. Reproducibility

**Q15 — Replay and artifact contract (prereg §10).**
Confirm: (a) every reported number must be re-computable by re-running the scorer on sealed artifacts (no LLM re-runs in verification); (b) the artifact layout of §10.3 is mandatory; (c) the P02 replay.sh sha256 pin must reproduce before run 1; (d) partial runs (if the window truncates) are reported as `partial`, never dropped.

**Q16 — Pending-marker resolution (prereg §12).**
Acknowledge the three `[PENDING]` markers and their resolution gates: P06 (Tox21 case), P07 (merge of `p07/integration`, SHA pinned at run start), P05 parity-suite re-verification on the merged tree. Confirm that **any** unresolved pending marker at pre-flight blocks its corresponding arm/case (not the whole campaign) — except P05 re-verification and P06-for-RQ4, which block case-wide as stated in §12.

---

## Approval record

| Item | Value |
|------|-------|
| Judge | ____________________ |
| Decision | APPROVE / APPROVE-WITH-CONDITIONS / REJECT |
| Conditions (if any, cite question IDs) | ____________________ |
| Date | ____________________ |
| Recorded in | judge scorecard + `EXECUTION_STATE.md` |
| Prereg hash (post-approval) | ____________________ |
