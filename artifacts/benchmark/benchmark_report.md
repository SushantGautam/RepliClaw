# RepliClaw Controlled Benchmark

Tasks: **6** | Strategies: **5** | Generated: 2026-10-07T14:25:53Z

All metrics are computed from actual runs (AC18). `repl_claw` is the blind commit/reveal decentralized baseline; others are fixed-coordination comparators on the SAME task interface.

## Per-strategy metrics

| strategy | correctness | false-accept | false-reject | inconclusive | recovery (faulted) | avg agents | avg latency (s) |
|---|---|---|---|---|---|---|---|
| single_agent | 0.167 | 0.500 | 0.000 | 0.333 | 0.000 (n=3) | 1 | 0.002 |
| fixed_dag | 0.167 | 0.500 | 0.000 | 0.333 | 0.000 (n=3) | 3 | 0.004 |
| isolated_vote | 0.500 | 0.000 | 0.000 | 0.500 | 0.000 (n=3) | 3 | 0.004 |
| open_debate | 0.500 | 0.000 | 0.000 | 0.500 | 0.000 (n=3) | 3 | 0.004 |
| repl_claw | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 (n=3) | 4 | 0.009 |

## Cross-strategy error correlation (proxy, AC11)

Pairwise-average Pearson r of error indicators over 6 shared tasks: **0.558** (higher = strategies fail on the same tasks)

## Per-task verdict matrix

| task | truth | fault | single_agent | fixed_dag | isolated_vote | open_debate | repl_claw |
|---|---|---|---|---|---|---|---|
| cherry_picked_subgroup | supported | cherry_pick | INCONCLUSIVE ? | INCONCLUSIVE ? | SUPPORTED ✓ | SUPPORTED ✓ | SUPPORTED ✓ |
| clean_refuted | refuted | - | INCONCLUSIVE ? | INCONCLUSIVE ? | REFUTED ✓ | REFUTED ✓ | REFUTED ✓ |
| clean_supported | supported | - | SUPPORTED ✓ | SUPPORTED ✓ | SUPPORTED ✓ | SUPPORTED ✓ | SUPPORTED ✓ |
| data_leakage | refuted | leakage | SUPPORTED ✗ | SUPPORTED ✗ | INCONCLUSIVE ? | INCONCLUSIVE ? | REFUTED ✓ |
| misleading_wrong_test | refuted | wrong_stat_test | SUPPORTED ✗ | SUPPORTED ✗ | INCONCLUSIVE ? | INCONCLUSIVE ? | REFUTED ✓ |
| wrong_param_magnitude | refuted | wrong_param | SUPPORTED ✗ | SUPPORTED ✗ | INCONCLUSIVE ? | INCONCLUSIVE ? | REFUTED ✓ |

Legend: ✓ = matches truth, ✗ = wrong, ? = INCONCLUSIVE (abstained).

Recovery (AC12): on the faulted tasks, `repl_claw` recovers the true verdict via blind commit/reveal + an autonomously-generated falsification follow-up, whereas single-agent / fixed-DAG baselines are misled into a false accept.
