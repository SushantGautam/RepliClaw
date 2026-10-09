# P08 Scorecard (counterevidence-first)

- case: `policy_rag_v1`  seed: `20261010`
- oracle: `/Users/sushantgautam/Documents/ScienceClawHackathon/experiments/policy_rag/oracle/oracle.json`
- parity ok: `True`  envelope hashes: ['fa6f4b413ab9b1f09e306de8c5b5a35c524587f82080d18eac441bedb831bc1c']

## Stopping rules

- S1 (arm abort > 25%): **not triggered**
- S5 (leakage incidents): **not triggered**

## P1 decision (S5 vs S4 on M1)

- rule: P1 decision rule (prereg v1.2; character-identical in §2 and §8.1 S4). Estimand: Δ = M1(S5) − M1(S4), the run-level mean difference in correct-diagnosis rate (M1, higher is better) between the escrow arm (S5) and the open-sharing swarm (S4), on the same case/oracle at the matched envelope. Polarity / null: H0: Δ ≤ 0 (S5 does not exceed S4); favorable direction: Δ > 0 (S5 better than S4). CI convention: bootstrap percentile 95% CI on Δ, 10,000 resamples, seed 20261010, run-level within-case resampling (resample run indices independently within each arm; Δ_b = mean_b(M1,S5) − mean_b(M1,S4)). Final decision (primary, n_run = 20 per arm): P1 SUPPORTED (S5 beats S4) iff CI_lower(Δ) > 0. P1 FALSIFIED (S5 worse) iff CI_upper(Δ) < 0; the report leads with this falsification per §8.1 and preserves all S5 artifacts verbatim. Otherwise (CI contains 0): P1 NOT SUPPORTED; report descriptively (point estimate + 95% CI). Interim screen (n_run = 10 per arm, first 10 runs): the 10-run 95% CI on Δ is a screening device only. It supports and falsifies nothing, triggers no stop, no amendment, and no report change; it is reported solely to monitor whether the 20-run block is tracking toward or away from the decision boundary.
- S5 M1 mean: 1.0
- S4 M1 mean: 0.2
- difference CI95: [0.6, 0.95]
- decision: **SUPPORTED**

## Arms (n/a / negative rows first)

| arm | M1 (95% CI) | M11 | M3 | M6 | M7 | M9 median | M10 | M4 incidents | n valid/total |
|-----|-------------|-----|----|----|----|-----------|-----|--------------|---------------|
| A1 | 1.000 [1.000, 1.000] | 0.000 | 0.500 | 17481 | 0.00 | 110.2 | 0.650 | 0 | 20/20 |
| A3 | 1.000 [1.000, 1.000] | 0.000 | 0.500 | 14287 | 0.00 | 86.0 | 0.750 | 0 | 20/20 |
| S5 | 1.000 [1.000, 1.000] | 0.000 | 0.500 | 15234 | 0.00 | 94.3 | 0.550 | 0 | 20/20 |
| S4 | 0.200 [0.050, 0.400] | n/a | n/a | 15051 | 0.00 | 69.5 | 1.000 | 0 | 20/20 |
| S0 | 0.150 [0.000, 0.300] | n/a | n/a | 7336 | 0.00 | 30.5 | 1.000 | 0 | 20/20 |
| S3 | 0.050 [0.000, 0.150] | n/a | n/a | 21167 | 0.00 | 133.4 | 1.000 | 0 | 20/20 |
