# V3.2 Pre-Registration Freeze Stamp — 2026-10-11

Freeze of the V3.2 both-constraints amendment for the bounded
20-run live pilot (round 4). Stamped **after** both pre-launch
independent reviews (code judge PASS; science judge PASS-WITH-CONDITIONS)
and **after** all pre-launch fixes they required (including the pyarrow
concurrent-read lock, science-judge C1), so this SHA covers the final
pre-launch diff.

## Frozen implementation (SHA + file hashes at commit 2082640505d4f64c51a03793124ccfc676e73cc3)

```
1064150c92c4ad855805b86359d37f88de2aa0c47b770a04403ac26db257a614  src/repliclaw/experiments/v3/telemetry_arms.py
540409fc9c9a88333a22edff2c273a9469541ea1052a005aaf4b2c323c1269f9  src/repliclaw/experiments/v3/telemetry.py
c75da8fe37ae207663cab56175e3d5fadbefeca04f7cc6427ac97e87686289b5  scripts/pilot_run.py
5b9094d5c588d6b4206311fd4c6935b51d33babc88490216da2b979c1f4a02fb  scripts/pilot_parallel.py
880db6017cdd13fa23e0073dfb90be4458c6ff58cc25e38f42c218064d9fc6bd  scripts/pilot_report.py
```

Pilot case registry: SHA-256 `13096078103d38f613dd57e7a99b3c187178c2001077325125b51529c0258a8a` (unchanged).
Live model: SimulaChat gateway `default` (gateway-echoes `Qwen3.8-27B`; 12/12 agents echoed in the V3.2 canary) — a model **substitution**, NOT the published baseline (see required disclosure list below).

## Amended vs unchanged

| Parameter | V3.1 (superseded) | V3.2 (frozen) | Changed? |
|---|---|---|---|
| MAX_TOKENS_PER_RUN | 90,000 | **150,000** | AMENDED (B1) |
| MAX_TOOL_CALLS (per sandbox) | 24 | **48** | AMENDED (B2) |
| Envelope ratio band (volume measure) | [0.6, 1.25] | **[0.6, 1.40]** | AMENDED (B3) |
| Round cumulative ceiling | 4.32M | **7.2M** | AMENDED (B4) |
| Cases, seeds, arms, agent counts, per-sandbox tool set, tool order | (unchanged) | (unchanged) | NO |
| Scorer, metrics, hit/miss definition | (unchanged) | (unchanged) | NO |
| Stop-1..4 rules, round-4-only authorization | (unchanged) | (unchanged) | NO |
| P08 surface (ENVELOPE_TOKENS=60,000) | 60,000 | 60,000 (verified untouched) | NO |

## Launch protocol (round 4)

- Driver: `scripts/pilot_parallel.py run` (concurrency 6, default `default` model — do **not** set `SIMULACHAT_MODEL`; verify every agent's model field echoes the gateway model; concurrency and retry-once documented in `parallel_meta.json`).
- 10 pilot cases × 2 seeds × 2 arms = 20 runs; fresh 7.2M cumulative ceiling; pre-claim ceiling gate refuses runs that would breach.
- Evidence: per-run status/manifest/agent-model/ledger; `parallel_meta.json`; STOP.json if a rule trips; T0+4 independent report.
- The prior round-0 V3.2 canary (case RCA-P-01) is a SEPARATE canary run (run_v32_canary/), excluded from round 4 evidence; round 4 starts from a clean state.
- If any stop rule trips: pause, write cause decomposition (agent-level attribution, budget vs tool-loop vs label-gate), do **not** proceed; return to human gate.

## Required disclosure list (any report or claim citing round-4 results MUST carry these)

1. **MODEL-SUBSTITUTION:** the live round uses the SimulaChat gateway `default` (echoes `Qwen3.8-27B`), not the official published baseline model — results are NOT the official baseline.
2. **B3 post-hoc recalibration:** the volume band 1.40 was recalibrated after observing historical violations (N1); it is not part of the original pre-registration.
3. **Completion gaps may be canary-constructed:** some "completion" evidence predates the live run and came from offline canaries.
4. **D-E infeasibility is multi-resource:** rounds 1–4 are feasibility-only for D-E; NO effect estimate may be drawn from them.
5. **Parallel execution provenance:** round 4 runs through `pilot_parallel.py` (threads, concurrency 6, retry-once), recorded in `parallel_meta.json` and per-run `parallel` stamps.
6. **If any stop rule trips:** a cause decomposition (driver vs arm failures, budget vs tool-loop vs label-gate) is mandatory, and control returns to the human gate.
7. **Live V3.2 canary non-convergence (round 0, case RCA-P-01, pre-freeze):** D-E-TELEM `aborted_budget` on both seeds (~151K tokens, ~50–53 tool calls) via a non-convergent repeating-tool-call pattern (repeated `top_anomalies`/`service_metrics` with identical args); both phase-1 escrow commits present, no phase-2 submission. Round 4 is pre-registered accordingly as feasibility-only for D-E. The canary is excluded from round-4 evidence (separate run dir, no parallel stamps). **Interpretation caveat:** D-E's token overhead at 150K is a composite of genuine decentralization overhead AND per-agent non-convergence (redundant re-queries no central manager would make); the frozen design can only attribute this post-hoc from per-sandbox `audit_sandboxes.json`.

## Post-round documentation corrections (recorded at freeze time; NOT re-freeze triggers)

- `pilot_parallel.py` module docstring (line ~12) overstates per-run stamps ("worker id, attempt count" — neither is persisted; concurrency + driver sha + git rev are). Corrected after round 4 (science-judge C3 note); the file was left byte-identical to the frozen hash at launch.

## What this does NOT authorize

- No round 5 (V3.3) without a new human-approved amendment, new independent reviews, and a new freeze.
- No effect-claim inference from rounds 1–4 (feasibility-only); any effect estimate requires the next authorization gate.
- No P08-surface changes; no model change without disclosure; no budget above 7.2M cumulative tokens for the round.
- No public release (`main` stays human-gated).
