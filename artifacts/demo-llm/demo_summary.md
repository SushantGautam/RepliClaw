# RepliClaw Demo — Summary & Baseline Comparison

Backend: `llm` | Wall clock: 49.8s

## Case results

| case | truth | verdict | confidence |
|---|---|---|---|
| genuine supported (RR=1.5, raw RR=1.5) | supported | **SUPPORTED** | 0.980 |
| misleading (means look significant; raw RR=1.0) | refuted | **REFUTED** | 0.980 |

## Baseline comparison on the misleading case

| strategy | verdict | confidence | agents | follow-up needs | tokens | latency (s) |
|---|---|---|---|---|---|---|
| single_agent | REFUTED | 0.980 | 1 | 0 | 899 | 2.799 |
| fixed_dag | REFUTED | 0.623 | 3 | 0 | 2890 | 10.083 |
| isolated_vote | REFUTED | 0.980 | 3 | 0 | 2672 | 7.248 |
| open_debate | REFUTED | 0.980 | 3 | 0 | 2758 | 7.910 |
| repl_claw | REFUTED | 0.980 | 3 | 0 | 2683 | 6.726 |

## Interpretation (derived from the numbers above, not asserted)

- RepliClaw concluded **REFUTED** (conf 0.980, 3 agents, 0 follow-up need(s)) — matching the ground truth that the published RR is not supported by the raw events.
- No follow-up need was emitted this run: the revealed evidence did not contain an unresolved independent conflict (the follow-up branch is evidence-conditional, not fixed).
- On this run, no baseline false-accepted the misleading artifact (with live models, raw-event reading is straightforward for all roles).
- Control case: the genuine supported claim was verified **SUPPORTED** (conf 0.980), so the refutation above is not a blanket abstention/refutation bias.

_Deterministic-backend runs (offline) additionally demonstrate the full conflict → follow-up adjudication recovery path; see `artifacts/demo/` and `artifacts/benchmark/`._