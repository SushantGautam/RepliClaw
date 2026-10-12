# V4 Comparison Plan — Honest Interpretation Framework

**Status:** PROSPECTIVE — companion to `v4_deadline_instrument.md`
**Date:** 2026-10-12

## §1 What this experiment tests

The V4 instrument tests ONE specific question:

> Does making decentralized investigators operate CONCURRENTLY under bounded local reasoning (12-tool cap) and a hard per-investigator deadline (120 s), with a deterministic fallback commit on timeout, improve diagnostic completion rate and top-1/top-5 accuracy relative to a strong adaptive centralized manager, when both arms have identical access-matched observational tool access and identical token envelopes?

This is NOT a test of whether decentralization is inherently superior. It is a test of whether a SPECIFIC coordination regime (concurrency + deadline + fallback) changes the completion/accuracy tradeoff at a fixed envelope.

## §2 What a positive finding would mean

A positive finding (D-E-DET > C-EQ-DET on primary metrics) would mean:

1. At the 150K token envelope, concurrent phase-1 with deadline+fallback completes more runs than sequential phase-1 did in V3 (where D-E was 0% at 150K).
2. The completion-rate improvement translates into top-1/top-5 accuracy gains over C-EQ-DET at the same envelope.
3. The mechanism ablations isolate WHICH component drives the gain: concurrency, escrow/reveal, or phase-2 intervention selection.

Interpretation: "Under bounded local reasoning with hard deadlines, concurrent decentralized investigation achieves [X]% completion and [Y]% top-1 at 150K tokens, vs [Z]% completion and [W]% top-1 for the centralized baseline." This is a MECHANISM finding about coordination architecture, not a general claim about decentralization.

## §3 What a negative finding would mean

A negative finding (C-EQ-DET ≥ D-E-DET on all primary metrics) would mean:

1. The concurrency+deadline+fallback mechanism does NOT improve completion or accuracy over a well-designed centralized manager at the same envelope.
2. The V3 finding (D-E correct but envelope-bound) persists: the bottleneck is total token consumption, not coordination topology.
3. The centralized manager's adaptivity (planning after each observation) is at least as effective as parallel investigation with a committee adjudication step.

Interpretation: "At 150K tokens, the adaptive centralized manager matches or exceeds the deadline-bound decentralized committee on top-1 ([A]% vs [B]%) and completion ([C]% vs [D]%), using fewer total tool calls ([E] vs [F])." This CONFIRMS the V3 H-nonconv/mechanism-negative verdict and closes the tool-cap axis permanently.

## §4 What a null finding would mean

A null finding (no statistically meaningful difference between arms) would mean:

1. Both architectures achieve similar completion and accuracy at 150K tokens.
2. The coordination topology (concurrent-decentralized vs sequential-centralized) is NOT the binding constraint at this envelope.
3. The V3 finding that "D-E is correct when it completes" is replicated: both arms complete at similar rates and diagnose correctly at similar rates.

Interpretation: "At 150K tokens, D-E-DET and C-EQ-DET are indistinguishable on top-1 ([A]% ± [SE]) and completion ([B]% ± [SE]). The coordination regime is not the binding constraint; the token envelope is." This supports the hypothesis that the next lever is envelope size or model capability, not architecture.

## §5 Statistical approach

### Sample size
- Primary: 11 cases × 2 seeds × 2 arms = 44 runs.
- Secondary (RE1): 5 cases × 2 seeds × 2 arms = 20 runs.
- Ablations: 4 cases × 2 seeds × 3 D-E conditions = 24 runs.

### Analysis
- **Primary estimand**: Mean top-1 accuracy (binary: 1 if rank-1 == ground truth, 0 otherwise) per arm, averaged over cases and seeds.
- **Completion rate**: Fraction of runs with status="completed" per arm.
- **Comparison**: Paired bootstrap CI on the per-case difference (D-E top-1 − C-EQ top-1), resampling cases (not runs) to respect within-case correlation from shared seeds. 10,000 bootstrap replicates.
- **No p-value claims**: With n=11 cases, formal hypothesis testing has low power. Report effect sizes with 95% CI. A CI that excludes zero is suggestive, not confirmatory.
- **Null-model amendment** (pre-committed): If the 95% CI on the top-1 difference includes [-0.10, +0.10], report as NULL regardless of point estimate direction.

### Multiple comparisons
- Primary metrics: top-1, top-5, completion, total tokens, wall time, tool cost (6 metrics).
- Apply Holm-Bonferroni correction across the 6 primary metrics.
- Secondary metrics are exploratory; no correction applied; label as such.

## §6 Pre-committed interpretation rules

| Outcome | Top-1 diff CI | Completion diff | Interpretation |
|---------|---------------|-----------------|----------------|
| Positive | Lower bound > 0 | D-E > C-EQ | Concurrency+deadline improves diagnosis at fixed envelope |
| Negative | Upper bound < 0 | Either | Centralized manager is at least as good; V3 verdict confirmed |
| Null | CI includes [-0.10, +0.10] | Either | Architecture is not the binding constraint |
| Inconclusive | Wide CI spanning both | Mixed | Insufficient power; report effect sizes, do not claim superiority |

## §7 What this experiment does NOT test

1. **True causal interventions**: The OBS tools are read-only queries against a frozen snapshot. No live system is perturbed. This is an access-matched observational comparison, NOT an intervention-matched one.
2. **Generalizability beyond RCAEval telemetry**: The case set is drawn from a specific benchmark suite. Findings may not transfer to other incident types or telemetry schemas.
3. **Model capability**: All runs use Qwen3.8-27B. A stronger model might change the completion/accuracy balance.
4. **Envelope scaling**: The 150K envelope is fixed. How the arms compare at 300K or 600K is a separate experiment.
5. **Real-time operation**: The 120 s deadline is a design parameter, not a real-world SLA. The experiment does not test whether the system meets operational latency requirements.

## §8 Reporting commitments

1. Report ALL runs, including crashes and budget aborts. Do not cherry-pick successful runs.
2. Report the fallback usage rate explicitly: what fraction of D-E phase-1 commits were deadline_fallback vs committed.
3. Report the per-investigator token distribution (min/mean/max), not just totals.
4. Report the time-to-first-diagnosis metric: it measures the practical value of concurrency.
5. Report the repeated-action rate: it measures whether the 12-tool cap actually constrains redundant behavior.
6. If the result is negative or null, publish it with the same rigor as a positive result. The V3 campaign's standing negative (H-nonconv) is a valid scientific finding.
7. No SOTA claims. No "outperforms X" language without a direct head-to-head on the same cases, same model, same envelope.

## §9 Relationship to prior work

- **V3 campaign (R1–R9)**: Established that D-E is correct when it completes, but completion is envelope-bound. V4 addresses the completion bottleneck directly.
- **Fast-finish sprint (FF-05)**: Confirmed 0% D-E completion at 150K on 10 pilot cases. V4 uses FRESH cases (no overlap with FF-05).
- **P08 (policy-rag hero case)**: Single-case counterfactual evidence that interventions matter. Not directly comparable to the multi-case telemetry diagnosis task.
- **AutoScientists (2026)**: Self-organizing decentralized scientific teams. V4 does NOT claim novelty for decentralization per se; the contribution is the specific deadline+fallback+concurrency mechanism and its controlled comparison against a matched central baseline.

## §10 Decision gate

After the full primary run (44 runs) is complete and scored:

1. Independent review by two reviewers (code + science) before any public claim.
2. If the result is positive: propose a follow-up at 300K/600K to test envelope scaling.
3. If the result is negative: close the architecture axis permanently; recommend shifting to envelope/model axes.
4. If the result is null: report as such; recommend investigating whether the 120 s deadline or 12-tool cap is too tight/too loose (sensitivity analysis on these parameters).
5. In all cases: update EXECUTION_STATE.md with the actual numbers, artifact paths, and verdict.
