# DRAFT — P1 result attribution disclosures (A9.4 / C7 + S-1 + N-2)

> **STATUS: DRAFT — NOT yet folded into `docs/APPLICATION_V2.md`.**
> Do **not** paste into the live application until **science round 3 on A1–A9 returns
> APPROVE** AND the human two-key authorization is recorded. If round 3 flags any
> wording below, revise here first, re-verify, then fold in. Owned by the integration
> lead. These disclosures are **mandatory** per PREREG §6b **A9.4** (from the A9 design
> review Q2) plus the A9 code-judge non-blocking items **S-1** and **N-2**.

Provenance pin: A9 merged @ `3491032` (milestone `915968c`), run branch `repl-claw-dev`.
Shared defect-instruction sha256 `5c7192eb…65996e7` (1201 chars). Sealed oracle
`experiments/policy_rag/oracle/oracle.json`: `true_cause="retrieval_omission"`,
`fault_marker="14-day-stale-top1"` (read only by the scorer).

---

## 1. Attribution scope (A9.4 item 1)

A **P1-SUPPORTED** outcome (if reached) establishes:

> "Running the counterfactual interventions improves defect diagnosis **on this
> single seeded case** (`policy_rag_v1`)."

It does **not** establish "decentralized autonomy improves diagnosis" in the
abstract. Attribute the mechanism to **counterfactual-intervention identifiability**,
not to autonomy or decentralization.

## 2. The base-case retrieval-vs-judge confound (A9.4 item 2)

From **base data alone**, `retrieval_omission` and `judge_stale` are **causally
non-identifiable**: both the base retrieval and the base judge independently point at
the 14-day staleness. Only the interventions S5 runs disambiguate —

- **I_R** (retrieval counterfactual) changes the retrieved target;
- **I_J** (judge counterfactual) flips the verdict with byte-identical downstream output;
- **I_P** (policy counterfactual) is byte-identical, ruling out policy conflict.

A correct causal diagnosis is therefore identifiable **only via** the interventions
S5 executes. Consequently, **a comparator arm scoring M1 ≈ 0 is a valid scientific
result** — the treatment supplies the identifiability the baseline lacks — and is
**not** "starvation" or an unfair handicap.

## 3. M1 is a 5-way exact-match classification (A9.4 item 3)

- M1 = `defect_class == oracle.true_cause` (exact match) with `bool(target_artifact)`;
  5 effective cause classes plus `none` in the shared taxonomy.
- The shared defect taxonomy (PREREG §6b A9.2.1) is given to **ALL arms equally** —
  it is a **menu, not the answer**. S5's defect token is partly taxonomy-assisted,
  and so is every comparator's, equally.
- The M1 **definition** (`_diagnosis_correct`) and the A1.3 P1 rule string are
  **byte-unchanged** by A9; only the *input* to M1 stops being a structural null.

## 4. Single seeded case — no generalization (A9.4 item 4)

This is **one seeded case**. Make **no** "autonomy beats central workflows" claim and
**no** generalization beyond `policy_rag_v1`. The novelty framing stays strictly
within `docs/PRIOR_ART_NOVELTY_GATE.md`'s defensible mechanism bundle (local
pre-outcome commitments + causally discriminating SimpleAudit interventions + local
task reallocation + strong adaptive-manager comparator).

## 5. S-1 — offline deterministic-arm fixture stand-in (A9 code-judge, non-blocking)

The **offline deterministic** arm's `_deterministic_defect`
(`src/repliclaw/investigators.py`) returns a registered
`("retrieval_omission", "retrieval")` pair from base data alone so the parity fixture
stays executable and scoreable. This is a **fixture stand-in, not a causally justified
diagnosis** — it inherits the retrieval-vs-judge confound of §2 (base data cannot
distinguish them). It is **never exercised in the primary live P1** (A8 puts S0/S3/S4
on live-LLM for the live window), and the A8 executor-parity guard is defense-in-depth.
Disclose that the offline deterministic defect value is a placeholder for run
executability, not a finding.

## 6. N-2 — strategy `budget_ledger.json` granularity (round-2 non-blocking)

For the strategy (comparator) arms, `budget_ledger.json` writes a **single synthetic
aggregate call** (`llm_calls:1`, `completion_tokens:0`, all tokens recorded as
`prompt_tokens`) — see `src/repliclaw/comparators/runner.py`. The **per-run token
totals are correct**; only the **per-call granularity is aggregate** for strategy arms.
The S5 live arm records genuine per-call usage. Disclose this granularity difference
in any budget/token comparison.

## 7. R-2 — live-token floors (pre-window, still open)

S4/S3/S0 live-token floors are **not yet measured** (S5-only floor 1,358–1,380 is
insufficient with 6 live arms). These will be measured on the **first pre-flight live
run** and recorded pre-window. Backstop if any arm overruns: 60,000-token/arm cap,
10.8M master ceiling, and the S0 stopping rule. Do **not** report a comparator token
cost as final until the pre-flight floor is recorded.

---

**Fold-in plan (post round-3 APPROVE + two-key):** add §1–§4 to the P1/result section of
`docs/APPLICATION_V2.md`; add §5–§6 to the limitations/methods section; add §7 to the
budget/accounting note. Then update `docs/application/FACT_CHECK_LIST.md` with a
fact-check row citing this doc + the round-3 report.
