# Adversarial Scientific-Audit Dataset (RX-441)

A self-contained, hand-authored dataset for auditing **research claims under
fragmented, conflicting, and deceptive evidence**. The domain is a fictional
pharmaceutical formulation audit (Compound RX-441); no real compounds,
companies, or studies are referenced.

Unlike the earlier CompoundCausal-32 benchmark — where investigators used
deterministic scripted policies over one shared global evidence vector — this
dataset fragments the evidence into **named source partitions** and plants
**real traps**, so it genuinely tests independent, cross-referencing analysis.

## Layout

```
adversarial_audit/
  __init__.py            # public (investigator-facing) exports only
  data.py                # public evidence loader (reads data/public/ ONLY)
  ground_truth.py        # EVALUATOR-ONLY reader of data/private/ (not exported)
  data/
    public/
      claims.json        # the 7 investigable claims (questions, no answers)
      evidence.json      # 18 evidence artifacts across 4 named sources
      manifest.json      # provenance + ground-truth POINTER (never content)
    private/
      ground_truth.json  # per-claim answer + rationale + required artifacts
      trap_annotations.json  # per-artifact trap taxonomy
```

## Claims (7)

| ID | Claim (abridged) | Answer |
|----|------------------|--------|
| C1 | New formulation increases bioavailability by 40% | **FALSE** (~15%, 90% CI 1.08–1.22) |
| C2 | Stable at 25C/60% RH, 6 months (no DP > 0.5%) | **TRUE** (D-2 = 0.18%, validated method) |
| C3 | Higher storage temperature *causes* potency loss | **FALSE** (confounded by batch age) |
| C4 | New granulation reduces batch-to-batch variability | **TRUE** (CV 8.2% → 3.1%) |
| C5 | Vendor chamber more reliable than in-house | **FALSE** (flawed uptime methodology) |
| C6 | New formulation cuts manufacturing cost by 25% | **FALSE** (~9%; double-counted overhead) |
| C7 | Pilot-scale data confirms lab-scale potency | **TRUE** (99.5% vs 99.7%) |

## Evidence sources (4 partitions)

* **source_a** — In-house QC Laboratory (reliable, validated methods).
* **source_b** — StabilTech Vendor Services (unreliable; known error track record).
* **source_c** — Process Engineering Group (reliable).
* **source_d** — External Literature / Quoted Studies (mixed quality).

`data.evidence_for_source(source_id)` returns one partition, so an
investigator can be given only a single source. **No single source contains
the full answer**: every claim's decisive evidence spans at least two sources
(see `required_artifacts` in the private ground truth), so a single-source or
naive global-aggregate approach is structurally disadvantaged.

## Traps planted

* **Misleading statistics** — `D1` (n=6, no CI, "definitive" 40% bioavailability
  gain), `B3` (vendor re-presents the same n=6 result as confirmation), `B2`
  ("99.9% uptime" from a business-hours-only window + miscalibrated sensor),
  `C3` (25% cost cut that double-counts a shared overhead), `D2` (r=0.85
  correlation stated as causal).
* **Contradictory evidence** — `A3` vs `B1` (D-2 = 0.18% vs 0.7%); `A6` vs `B2`
  (in-house 24/7 log vs vendor uptime claim).
* **Unreliable reports** — `B1` (unvalidated HPLC method), `B2` (excluded
  off-hours data, drifted sensor), `B3` (underpowered re-analysis).
* **Genuinely supporting evidence** — `A1`, `A3`, `A4`, `A5`, `A6`, `A7`, `C1`,
  `C2`, `C4`, `D3`, `D4`.

## How ground truth is isolated

* Answers, rationales, and the trap taxonomy live **only** in
  `data/private/` (`ground_truth.json`, `trap_annotations.json`).
* The public loader (`data.py`) reads **only** `data/public/` and strips any
  evaluator-only field, so an investigator holding `data.py` cannot reach the
  answers. `ground_truth.py` is the sole reader of `data/private/` and is
  **not exported** from the package `__init__` (evaluators import the module
  directly, mirroring the RCAEval `heldout_ground_truth` convention).
* `manifest.json` carries a ground-truth **pointer + sha256 only**, never the
  content (matching `repliclaw.benchmark_case_manifest/v1`).

## Which approach is expected to be misled, and why

A **naive global aggregator** that trusts every artifact's headline number is
expected to fail: it will accept the n=6 "40% bioavailability" point estimate
(`D1`/`B3`) over the powered CI-bearing study (`A1`), accept the vendor's
unvalidated "unstable" reading (`B1`) over the validated in-house result
(`A3`), read the confounded r=0.85 correlation (`D2`) as causation, accept the
business-hours-only "99.9% uptime" (`B2`) as proof of superior reliability, and
accept the double-counted "25% cost cut" (`C3`). That yields roughly 5 of 7
claims wrong. **Over-reliance on a single misleading source** (e.g. only
`source_b` or only `source_d`) is likewise punished, because each of those
partitions contains at least one trap and lacks the cross-source evidence
needed to resolve most claims. Only a **careful, independent,
cross-referencing** auditor — who weighs methodology (validation status,
sample size, confidence intervals, confounders, allocation factors) and
reconciles conflicts across sources — is expected to reach all 7 correct
conclusions. The dataset is deliberately **fair**: every correct answer is
genuinely reachable from the public evidence by such an auditor, and no
RepliClaw-specific strategy is required to succeed.
