# RepliClaw

Research project on decentralized scientific inference: can independent
investigators who commit to falsifiable predictions *before* seeing each
other's results outperform a strong centralized manager when the evidence is
fragmented, contradictory, and potentially misleading?

All claims are backed by committed, inspectable run evidence, and null or
negative results are reported as valid answers.

## The experiment

The current benchmark (`src/repliclaw/benchmarks/`) is a matched four-arm
comparison on an adversarial scientific-audit dataset (pharma formulation
RX-441; 18 artifacts across 4 sources; five engineered trap claims;
evaluator-only ground truth). No single source resolves any claim.

| Arm | What it is |
|---|---|
| `escrowed_independent` | 4 investigators, one per evidence source; each sees only its own source and seals its verdict before any peer result (commit → hash-verified reveal), then strict-majority aggregation |
| `open_sharing` | 4 investigators see all evidence, form initial verdicts, share them, then finalize |
| `central_adaptive` | One strong manager with adaptive tool calls |
| `single_investigator` | One investigator, single pass |

Arms share the same evidence union, model, temperature, and per-claim
token/call envelope. Every LLM call is captured in receipts (messages, usage,
wall time); the escrow arm additionally produces a tamper-evident commitment
ledger.

## Results

Live runs, Qwen3.8-27B, temperature 0.2. "Trap" = claim engineered to fool
## Results — every run, one table

✅ worked · ❌ failed · ➖ tie / inconclusive. All LLM runs used Qwen3.8-27B
(OpenAI-compatible endpoint, temperature 0.2); where that model is not a
benchmark's released baseline the run is model-substitution, and the
telemetry runs are observational (access-matched), not intervention-based.

| Run | Setup | Result | Verdict |
|---|---|---|---|
| Prototype benchmark (archived) | 6 known-answer tasks × 5 strategies; deterministic, offline | repl_claw 1.000 correct, 1.000 recovery; best baseline 0.500 | ✅ (offline harness only) |
| G3 pilot (V3, 60K cap) | 10 cases × 2 seeds × 2 arms, 2 rounds | D-E 0/12 completed (budget aborts + 2 crashes); C-EQ 5/12 completed, all hits | ❌ D-E (feasibility stop); C-EQ partial |
| Fast-finish heldout (V3.2, 150K/48t) | 10 cases × 2 seeds; D-E 19 vs C-EQ 17 runs | D-E 0/19 completed (all spent the full budget); C-EQ 17/17 hit at ~63K tokens | ❌ D-E; ✅ C-EQ |
| V3 campaign final (V3) | 8 cases, full cohort | D-E 6/8 vs C-EQ 6/8 (C-EQ a lower bound); D-E ~3.7× cost per run | ➖ tie |
| P08 one-seed demo | 1 case (policy_rag_v1), 3 arms, matched envelope, real counterfactual interventions | escrow+interventions 1.0 vs open-share 0.0 (CI [1.0, 1.0]) | ✅ demonstration only (1 seed) |
| P1 preregistered campaign | 6 arms × 20 runs (120), 1 seeded case, 1.72M tokens | S5 1.000 vs open-share 0.200 (Δ 0.800, CI [0.60, 0.95]); no-escrow and random-select ablations also 1.000 | ✅ — but the effect is attributable to the interventions, not escrow (1 case) |
| V4 full re-run | 10 frozen cases × 2 seeds × 2 arms (40 runs); cases historically exposed | D-E top-1 80% vs C-EQ 65% (+15 pp, p=0.555, CI crosses 0) | ➖ inconclusive |
| V4 AIOpsLab live | 5 live K8s fault-injection tasks, 2 arms, 150K | D-E 4/5 (1 budget abort), C-EQ 5/5; C-EQ used half the tokens, ~1/3 the time | ✅ C-EQ (directional, n=5) |
| HiddenBench (ICML 2026), observational | 12 tasks × 3 arms, seed 2026 | escrow 0/12, open-share 0/12, central (pooled) 10/12 | ❌ both distributed arms; ✅ pooled control |
| Mechanism smoke v2 | 1 reused case × 2 arms, 3 live runs | 2/2 completed, 2/2 acc@5 hits, 0/2 top-1 hits | ➖ exploratory |
| **Falsification 4-arm (current, live)** | 5 trap claims, 32K matched envelope | single 100% (14K tokens), central 100% (51K), open-share 100% (144K, 20/20 individual); escrow 20%, 80% abstention, 90% individual (9/10) | ✅ pooled arms; ❌ escrow |
| Falsification budget sensitivity | C1, 16K envelope | pooled arms all correct (2.8K–24.9K tokens); escrow ABSTAIN — 3 of 4 investigators hit their per-investigator budget before committing | ❌ escrow |

**Big picture across all runs**

- The centralized and single-agent arms (C-EQ, central_adaptive,
  single_investigator, pooled controls) win or tie in every run.
- Decentralized escrow never beats the centralized baseline: one tie (V3, at
  ~3.7× the cost) and losses or non-completions everywhere else. Its failure
  modes are consistent: budget exhaustion during coordination (G3,
  fast-finish, AIOpsLab, C1) and aggregation discarding correct individual
  votes (falsification 4-arm, HiddenBench).
- The only escrow-involved win (P1) is attributable to the counterfactual
  interventions, not escrow — ablation arms without escrow that ran the same
  interventions also scored 1.000.
- On current valid evidence, independent evidence escrow has not shown a
  benefit and has a measurable cost in accuracy, completion, and spend.

Detail, methods, limits, and raw evidence for each run:
[`docs/next_stage/science/falsification_indepinfo_verdict.md`](docs/next_stage/science/falsification_indepinfo_verdict.md)
(current experiment), `docs/next_stage/results/` (per-run reports), and
`artifacts/` (receipts, ledgers, transcripts).

## Install & reproduce

Python ≥ 3.10, [uv](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev
uv run pytest                       # 390 passed, 20 skipped; hermetic, no network
```

The live comparison requires an OpenAI-compatible endpoint:

```bash
export REPLICLAW_LLM_API_KEY=...
uv run python -m repliclaw.benchmarks.falsification \
    --claims C1,C2,C3,C5,C6 \
    --token-envelope 32000 \
    --out artifacts/falsification/<run>
```

`--dry-run` substitutes a deterministic mock and is a harness check only; it
is labeled as such and is never reported as a result.

## Repository layout

```
src/repliclaw/     library (protocol, escrow, investigators, benchmarks)
tests/             hermetic test suite
docs/next_stage/   design, preregistration, reviews, scientific verdicts
artifacts/         committed run evidence (receipts, ledgers, transcripts)
deps/scienceclaw/  vendored, pinned ScienceClaw primitives
```

## Notes

- Offline/mock outputs are always labeled; they are never presented as live
  results.
- This project was developed with AI coding agents and uses LLM agents both as
  a development tool and, by design, as the experimental investigator arms.
