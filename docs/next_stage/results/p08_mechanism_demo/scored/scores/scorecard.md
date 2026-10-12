# P08 Scorecard (counterevidence-first)

- case: `policy_rag_v1`  seed: `20261010`
- oracle: `/home/susan/projects/RepliClaw/experiments/policy_rag/oracle/oracle.json`
- parity ok: `True`  envelope hashes: ['fa6f4b413ab9b1f09e306de8c5b5a35c524587f82080d18eac441bedb831bc1c']

## Stopping rules

- S1 (arm abort > 25%): **not triggered**
- S5 (leakage incidents): **not triggered**

## P1 decision (S5 vs S4 on M1)

- rule: P1 decision rule (prereg v1.2; character-identical in §2 and §8.1 S4). Estimand: Δ = M1(S5) − M1(S4), the run-level mean difference in correct-diagnosis rate (M1, higher is better) between the escrow arm (S5) and the open-sharing swarm (S4), on the same case/oracle at the matched envelope. Polarity / null: H0: Δ ≤ 0 (S5 does not exceed S4); favorable direction: Δ > 0 (S5 better than S4). CI convention: bootstrap percentile 95% CI on Δ, 10,000 resamples, seed 20261010, run-level within-case resampling (resample run indices independently within each arm; Δ_b = mean_b(M1,S5) − mean_b(M1,S4)). Final decision (primary, n_run = 20 per arm): P1 SUPPORTED (S5 beats S4) iff CI_lower(Δ) > 0. P1 FALSIFIED (S5 worse) iff CI_upper(Δ) < 0; the report leads with this falsification per §8.1 and preserves all S5 artifacts verbatim. Otherwise (CI contains 0): P1 NOT SUPPORTED; report descriptively (point estimate + 95% CI). Interim screen (n_run = 10 per arm, first 10 runs): the 10-run 95% CI on Δ is a screening device only. It supports and falsifies nothing, triggers no stop, no amendment, and no report change; it is reported solely to monitor whether the 20-run block is tracking toward or away from the decision boundary.
- S5 M1 mean: 1.0
- S4 M1 mean: 0.0
- difference CI95: [1.0, 1.0]
- decision: **SUPPORTED**

## Arms (n/a / negative rows first)

| arm | M1 (95% CI) | M11 | M3 | M6 | M7 | M9 median | M10 | M4 incidents | n valid/total |
|-----|-------------|-----|----|----|----|-----------|-----|--------------|---------------|
| S5 | 1.000 [1.000, 1.000] | 0.000 | 0.500 | 3212 | 0.00 | 26.0 | 1.000 | 0 | 1/1 |
| S3 | 0.000 [0.000, 0.000] | n/a | n/a | n/a (no correct runs) | 0.00 | 19.8 | 1.000 | 0 | 1/1 |
| S4 | 0.000 [0.000, 0.000] | n/a | n/a | n/a (no correct runs) | 0.00 | 21.3 | 1.000 | 0 | 1/1 |
