# RepliClaw — P1 Result Statement (counterevidence-first)

**Result ID:** P1, live campaign `runs/p08-live-20261009T122444Z/` (120 runs, 6 arms × 20,
sigma2 `Qwen3.8-27B`, case `policy_rag_v1`, seed 20261010).
**Decision:** **P1 SUPPORTED** per the preregistered rule (prereg v1.2 A1; Δ = M1(S5) − M1(S4);
SUPPORTED iff bootstrap 95% CI lower bound > 0).
**Governance:** no P1/P2/P3 result is reported here outside the mandatory disclosures below
(science round-3 MUST-1; `DEMO_AND_FINAL_HANDIN_V2.md` "P1 result statement"; science-judge
`SCIENCE-JUDGE-CAMPAIGN-RESULTS-20261009.md` exact disclosure text).

---

## 0. Counterevidence first (what does NOT support the claim)

Before the positive result, the counterevidence that a reviewer would demand:

1. **The result does NOT show escrow, decentralization, or "autonomy" improves diagnosis.**
   A1 (eess_no_escrow, `PassThroughEscrow`) and A3 (eess_random_select) — arms that **run the
   exact same counterfactual interventions** but differ on escrow and selection strategy —
   **also scored M1 = 1.000**, identical to S5. The per-run `defect_class` table splits exactly
   on *whether the arm executes the preregistered counterfactual suite (I_R/I_P/I_J)*:
   S5/A1/A3 → `retrieval_omission` (×20 each); S4/S3/S0 (no interventions) → `judge_stale`
   majority. Attribution must therefore be to the **counterfactual-intervention
   identifiability mechanism**, full stop (prereg §A9.4(1)).
2. **The strongest centralized baseline is the weakest arm, but this is NOT a clean
   centralization-cost estimate.** S3 (adaptive central manager) scored M1 = 0.050 — lower
   than S4 (0.200), S0 (0.150) and all intervention arms. However S5-vs-S3 (P2) is **confounded
   by the protocol difference** (A3 disclosure); it is reported descriptively and is **not** a
   causal isolation of centralization cost, and it does not veto or gate P1.
3. **The effect is single-case.** One seeded case (`policy_rag_v1`), n = 20/arm. Nothing here
   establishes generalization across cases, tasks, or models.
4. **The secondary metrics do not add to the claim.** M11 (correct refutation of the sole
   unsupported hypothesis H_P) = 0.0 with denominator = 1/arm (near-vacuous; H_P = the
   "no defect" hypothesis the oracle holds unsupported; S5/A1/A3 failed to register the
   refuting intervention evidence as a falsification). M3 (counterfactual yield) was reported
   as 0.0 in the first scoring pass and **corrected to 0.50** — see §3.5; it must NOT be read
   as "no effective interventions."
5. **Ceiling saturation.** S5/A1/A3 are at the M1 ceiling (1.000); the Δ CI is bounded by
   construction and likely optimistic in its upper half (S-1).
6. **Matched-cap, not matched-spend.** Arms were matched on the identical envelope
   (60,000 tokens / 900 s / 4-agent cap; same model/config/seed; same 5-way defect menu) and
   none overran it (parity ok=True, executor parity all True) — this is a **matched-cap**
   same-task comparison, **not** equal token spend. Per-arm spend differs (mean tokens/run:
   S5 15,234 / A1 17,481 / A3 14,287 / S4 14,300 / S3 18,390 / S0 6,128, from `scores.json` M5);
   token comparisons require the N-2 granularity disclosure.

## 1. The result

> **Result (single seeded case `policy_rag_v1`, n=20/arm, 120 live runs, Qwen3.8-27B, seed
> 20261010).** On correct root-cause diagnosis (M1), the EESS counterfactual-intervention
> pipeline (S5) scored **1.000** vs the open-sharing swarm (S4) **0.200** (Δ = 0.800, within-case
> bootstrap 95% CI **[0.60, 0.95]**; 10,000 resamples, seed 20261010); per the preregistered
> rule this is **P1 SUPPORTED**. **This is a within-case, single-case result and does not
> establish generalization across cases.**
>
> Full arm M1 (n=20 each): A1 1.000, A3 1.000, S5 1.000, S4 0.200 [0.050, 0.400],
> S0 0.150 [0.000, 0.300], S3 0.050 [0.000, 0.150]. Stopping rules S1 (arm abort > 25%) and
> S5 (leakage) NOT triggered; parity ok=True; executor parity S5_S4/S5_S3/S5_S0 all True;
> identical envelope sha256 across arms. **M4 (oracle leakage) = 0 incidents in 120 runs**
> (oracle read only by the post-run scorer, after the completeness gate).
>
> **Attribution:** the improvement is attributable to **running the preregistered
> counterfactual interventions (I_R/I_P/I_J)**, which make the true cause
> (`retrieval_omission`) identifiable where base data alone leaves it confounded with a stale
> judge. It is **not** attributable to escrow, decentralization, or "autonomy": the no-escrow
> (A1) and random-select (A3) arms, which run the same interventions, also scored 1.000.
>
> **Fairness:** arms were matched on **cap** (identical 60,000-token / 900 s / 4-agent
> envelope, identical model/config/seed, identical defect-classification menu) — this is a
> matched-*cap*, same-task, no-overrun comparison, **not** equal token spend. No oracle
> leakage was detected (M4 = 0; oracle read only by the post-run scorer).
>
> **Secondary metrics (descriptive):** M2 (falsification attempted) = 1.0 for all
> intervention-running arms. M11 (correct refutation of the sole unsupported hypothesis H_P)
> = 0.0 (denominator = 1/arm). **M3 (counterfactual yield) = 0.50 (corrected)** — do **not**
> interpret the first-pass M3 = 0.0 as "no effective interventions."
>
> **Scope limits:** single seeded case; M1 is a 5-way exact-match classification using a
> shared taxonomy menu; the S5-vs-S3 (centralization-cost) contrast is confounded by the
> protocol difference and is not a clean causal isolation.

## 2. Mandatory disclosures (verbatim items from `DEMO_AND_FINAL_HANDIN_V2.md`, all present)

1. **Attribution.** A P1-SUPPORTED outcome establishes "running the counterfactual
   interventions improves defect diagnosis **on this single seeded case** (`policy_rag_v1`)" —
   it does NOT establish "decentralized autonomy improves diagnosis". The mechanism is
   **counterfactual-intervention identifiability**, not autonomy or decentralization.
2. **Base-case confound.** From base data alone, `retrieval_omission` and `judge_stale` are
   causally non-identifiable (base retrieval AND base judge both point at the 14-day
   staleness). Only the intervention arms disambiguate (I_R changes the retrieved target;
   I_J flips the verdict with byte-identical downstream output; I_P is byte-identical, ruling
   out policy conflict). A comparator arm scoring M1 ≈ 0 is a **valid scientific result** —
   the treatment supplies the identifiability the baseline lacks — not "starvation".
3. **M1 definition.** M1 is a **5-way exact-match classification**
   (`defect_class == oracle.true_cause` with `bool(target_artifact)`). The shared defect
   taxonomy is given to **ALL arms equally** — a menu, not the answer.
4. **Scope.** **Single seeded case, no generalization.** No "autonomy beats central workflows"
   claim; the novelty framing stays within `PRIOR_ART_NOVELTY_GATE.md`'s defensible mechanism
   bundle (and the 2026-10-09 re-audit: CAR arXiv 2606.08275 partially anticipates element (b);
   the defensible conjunction includes matched-budget adaptive-manager comparison, which the
   re-audit found in NO surveyed system).
5. **S-1 (offline fixture stand-in).** The offline deterministic arm's `_deterministic_defect`
   returns a registered `("retrieval_omission","retrieval")` pair from base data alone so the
   parity fixture stays executable and scoreable. It is a **fixture stand-in, not a causally
   justified diagnosis** (it inherits §2's confound); it is never exercised in the primary
   live P1 (all six live arms ran the live LLM under the shared `LLMConfig`).
6. **N-2 (budget granularity).** Strategy arms' `budget_ledger.json` writes a single synthetic
   **aggregate** call; per-run totals are correct; per-call granularity is aggregate for
   strategy arms (S5 records genuine per-call usage). Disclosed in all token comparisons.
7. **R-2 (token floors).** S4/S3/S0 live-token floors were measured pre-window
   (`floor_r2.json`: S4 16,300 / S3 15,993 / S0 8,588; max arm usage fraction 0.2717 < 0.60
   flag threshold). Comparator token costs are reported as measurements, not estimates.

## 3. Execution integrity (from the independent Code Judge, MERGE-OK)

- Resume byte-reuses completed runs (verified byte-for-byte); the 7 transiently errored runs
  (stochastic empty LLM responses) were recovered by the protocol-sanctioned resumable re-run;
  recovered runs are **indistinguishable** from first-pass runs; the frozen harness
  (`scripts/campaign.py`) and frozen case (`experiments/policy_rag/`) were never modified.
- Token accounting reconciles exactly: 1,716,411 cumulative tokens (15.9% of the 10.8M master
  ceiling); per-run `usage_present` complete in all 120 runs.
- Oracle read strictly **after** the completeness gate (`gate_all_runs` before `load_oracle`);
  no manipulation or leakage.
- Provenance: per-run `tree_sha` spans `de77fba` (n=7) / `484dc66` (n=44) / `1df4c71` (n=69);
  `git diff de77fba..1df4c71 -- scripts src tests` is **EMPTY** (docs-only commits between), so
  the code-identical range `de77fba..1df4c71` is the authoritative provenance citation.

## 3.5. M3 correction (transparency record)

The first scoring pass reported M3 = 0.0 for all intervention arms. Independent science-judge
review (BLOCKING B2) established this as a **writer/scorer schema-mismatch artifact**: the
scorer read fields (`verdict_changed`/`hypothesis_falsified`) that the
`p08.counterfactual/1` writer never emitted; the real field is `severity` (pass|critical).
The scorer was corrected (`severity == "critical"`), a regression test added, and the frozen
tree **re-scored deterministically**: M3 S5/A1/A3 = **0.50** (40/80 critical — I_R and I_J
surface the defect; I0_baseline and I_P do not). **P1 is bit-identical** (secondary metric
only). The original scoring output is preserved at `scores.pre-m3-fix/` for audit.

## 4. Two-key authorization

Both keys were in hand before launch: science key = round-3 APPROVE-WITH-CONDITIONS
(`SCIENCE-JUDGE-A1-A9-ROUND3-APPROVE-WITH-CONDITIONS-20261009.md`); human key = verbatim
full-experiment authorization 2026-10-09T14:25 local (record:
`docs/application/TWO_KEY_SIGNOFF_RECORD.md`).

## 5. What remains (honest status)

- **P2 (S5 vs S3) and P3 (S0 ablation)** are **not** reported as decisions here: P2 is
  confounded (A3) and reported descriptively; P3 is a trivially-true ablation comparison.
- The **secondary tox21 case** (RQ4/P4, offline, no-LLM) remains a **separate** frozen
  sub-study; it has NOT been run as part of the live campaign.
- Public release of the results subset to the public repo branch is a **pending human
  decision** (this statement is the gated artifact for that release).
