# P08 Scorecard (counterevidence-first)

- case: `policy_rag_v1`  seed: `20261012`
- oracle: `/home/susan/projects/RepliClaw/experiments/policy_rag/oracle/oracle.json`
- parity ok: `True`  envelope hashes: ['fa6f4b413ab9b1f09e306de8c5b5a35c524587f82080d18eac441bedb831bc1c']

## Stopping rules

- S1 (arm abort > 25%): **not triggered**
- S5 (leakage incidents): **not triggered**

## P1 decision (S5 vs S4 on M1)

- rule: n/a
- S5 M1 mean: None
- S4 M1 mean: None
- difference CI95: None
- decision: **no_valid_runs**

## Arms (n/a / negative rows first)

| arm | M1 (95% CI) | M11 | M3 | M6 | M7 | M9 median | M10 | M4 incidents | n valid/total |
|-----|-------------|-----|----|----|----|-----------|-----|--------------|---------------|
| eess | 1.000 [1.000, 1.000] | 0.000 | 0.500 | 3212 | 0.00 | 26.0 | 1.000 | 0 | 1/1 |
| adaptive_central | 0.000 [0.000, 0.000] | n/a | n/a | n/a (no correct runs) | 0.00 | 19.8 | 1.000 | 0 | 1/1 |
| open_sharing_swarm | 0.000 [0.000, 0.000] | n/a | n/a | n/a (no correct runs) | 0.00 | 21.3 | 1.000 | 0 | 1/1 |
