# RepliClaw Demo — Summary & Baseline Comparison

Backend: `deterministic` | Wall clock: 0.1s

## Case results

| case | truth | verdict | confidence |
|---|---|---|---|
| genuine supported (RR=1.5, raw RR=1.5) | supported | **SUPPORTED** | 0.980 |
| misleading (means look significant; raw RR=1.0) | refuted | **REFUTED** | 0.256 |

## Baseline comparison on the misleading case

| strategy | verdict | confidence | agents | follow-up needs | tokens | latency (s) |
|---|---|---|---|---|---|---|
| single_agent | SUPPORTED | 0.980 | 1 | 0 | 0 | 0.002 |
| fixed_dag | SUPPORTED | 0.594 | 3 | 0 | 0 | 0.007 |
| isolated_vote | INCONCLUSIVE | 0.475 | 3 | 0 | 0 | 0.006 |
| open_debate | INCONCLUSIVE | 0.475 | 3 | 0 | 0 | 0.005 |
| repl_claw | REFUTED | 0.256 | 4 | 1 | 0 | 0.013 |

## Interpretation (derived from the numbers above, not asserted)

- RepliClaw concluded **REFUTED** (conf 0.256, 4 agents, 1 follow-up need(s)) — matching the ground truth that the published RR is not supported by the raw events.
- 1 follow-up need(s) was/were emitted AND fulfilled by independent follow-up investigator(s) (evidence-conditional, non-hard-coded path): `inv-followup-a63c2b`.
- Baselines that false-accepted the misleading artifact: **single_agent, fixed_dag**.
- Baselines that abstained instead of deciding: **isolated_vote, open_debate**.
- Control case: the genuine supported claim was verified **SUPPORTED** (conf 0.980), so the refutation above is not a blanket abstention/refutation bias.

_Deterministic-backend runs (offline) additionally demonstrate the full conflict → follow-up adjudication recovery path; see `artifacts/demo/` and `artifacts/benchmark/`._