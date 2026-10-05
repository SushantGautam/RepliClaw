# Erratum & Multi-Case Follow-up to the P1 Result Statement

**Date:** 2026-10-12  
**Applies to:** `P1_RESULT_STATEMENT_20261009.md` (P08 live campaign, commit `97a4559`)  
**Status:** Erratum (additive; the P1 statement is NOT modified and remains the authoritative record of the original 120-run campaign)  
**Follow-up evidence:** fast-finish sprint on branch `dev` (release PR: RepliClaw#3); findings memo `docs/next_stage/science/fast_finish_result.md`

---

## 1. What this erratum adds

The P1 statement's counterevidence item §0.1 established, on the single case
`policy_rag_v1`, that the M1 improvement is attributable to **access to the
preregistered counterfactual interventions**, not to escrow, decentralization, or
autonomy (arms A1/A3 — no escrow, random selection — scored M1 = 1.000 identically
to S5).

That attribution was **single-case** (P1 §0.3, §2.4). The fast-finish follow-up
supplies the multi-case confirmation that was missing:

**Intervention-matched, multi-case comparison (dev, 2026-10-11/12):**

| Arm | Runs | Completed | Hits | Avg tokens | Avg wall |
|-----|------|-----------|------|------------|----------|
| C-EQ (adaptive centralized) | 17 | 17 (100%) | 17 (100%) | 63,053 | 71s |
| D-E (decentralized escrow) | 19 | 0 (0%) | 0 (0%) | 152,192 | 409s |

- Frozen 10-case RCAEval roster, 2 paired seeds, 150K-token / 48-call envelope,
  SimulaChat Qwen3.8-27B, **identical intervention access for both arms** (parity
  proven by executable test; no oracle leak; no fixed scripts).
- Reproduced on 3 unseen heldout cases (RCA-P-08/09/10) with zero exceptions.
- D-E's failure is coordination thrashing (60–90% redundant tool re-issues);
  when D-E does complete (only at 300K–600K envelopes in historical rounds R6–R9)
  its accuracy is 100%. The deficiency is convergence cost, not correctness.

## 2. Consequences for the P1 claims

1. **§0.1 attribution stands and is strengthened.** Across 10 independent cases,
   the decentralized-escrow architecture shows no advantage over an adaptive
   centralized controller when both have equal intervention access. The P1 effect
   remains attributable to counterfactual-intervention identifiability.
2. **§0.3 scope limit is confirmed, not relaxed.** The single-case result did not
   generalize in the direction of architectural benefit; the multi-case follow-up
   found none.
3. **No P1 decision is altered.** P1 remains SUPPORTED per the preregistered rule
   for what it claims (intervention-access effect, single seeded case). This
   erratum adds external multi-case context; it neither vetoes nor extends the
   preregistered decision.

## 3. Honest caveats

- The follow-up is an **exploratory/feasibility sample** (10 cases, 1 model,
  1 benchmark family). No confirmatory p-value is claimed; the null-model
  correction (AMEND_NULL_MODEL_CORRECTION_20261011.md, approved 2026-10-12)
  governs interpretation.
- D-E was tested in its current implementation; a protocol redesign could change
  the convergence behavior.
- "D-E provides no benefit at matched practical budgets" is scoped to the frozen
  envelope and tested model; the 600K-envelope historical rounds show completion
  parity at 3–5× token cost, not quality superiority.

## 4. References

- Findings memo: `docs/next_stage/science/fast_finish_result.md` (branch `dev`, PR #3)
- Heldout feasibility protocol: `docs/next_stage/design/v33_heldout_feasibility_protocol.md`
- Null-model amendment (approved): `docs/next_stage/AMEND_NULL_MODEL_CORRECTION_20261011.md`
- Raw evidence: `.artifacts/rcaeval/pilot/{run_live_full_r0c,run_heldout_r1}/` (gitignored; per-run ledgers cited in the findings memo)
