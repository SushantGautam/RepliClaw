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
a naive reading (misleading statistic, contradiction, unreliable source);
accuracy on traps is the robustness measure.

**Matched four-arm comparison — 5 trap claims, 32,000 tokens/claim (live run)**

| Arm | Verdict acc | Trap acc | Abstain | Per-individual acc | Tokens | Verdict |
|---|---:|---:|---:|---:|---:|---|
| single_investigator | 100% | 100% | 0% | — | 14,133 | ✅ works — cheapest by far |
| central_adaptive | 100% | 100% | 0% | — | 50,824 | ✅ works |
| open_sharing | 100% | 100% | 0% | 100% (20/20) | 143,982 | ✅ works — but most expensive |
| escrowed_independent | **20%** | **20%** | **80%** | 90% (9/10) | 131,474 | ❌ fails |

**Budget sensitivity — C1 only, 16,000 tokens/claim (live run)**

| Arm | Verdict (expected FALSE) | Outcome |
|---|---|---|
| single_investigator | FALSE | ✅ correct, 2,806 tokens |
| central_adaptive | FALSE | ✅ correct, 6,189 tokens |
| open_sharing | FALSE | ✅ correct, 24,913 tokens |
| escrowed_independent | ABSTAIN | ❌ 3 of 4 investigators hit the per-investigator token budget before committing |

**What this shows**

- The single investigator and the central manager both work: on the traps,
  one careful pass over all the evidence beats every multi-agent design here.
- Open sharing works but costs ~10× the single investigator for the same
  answer — four agents seeing everything is a good way to spend money, not a
  way to be more accurate.
- **Independent evidence escrow fails, and we know exactly why.** Its
  investigators were 90% accurate *individually*, but each saw only one
  source, which was often not enough to commit; strict-majority aggregation
  then turned those non-commits into abstentions, discarding the correct
  votes (on every abstained claim, at least one investigator had the right
  answer). Under a tighter budget the same arm additionally starves
  before it can finish.
- Nothing in this sample shows a case where escrow beat the pooled arms; the
  pooled arms got all five traps right.

Full methods, limits, and the conditions that would change the conclusion:
[`docs/next_stage/science/falsification_indepinfo_verdict.md`](docs/next_stage/science/falsification_indepinfo_verdict.md).
Raw messages, usage, receipts, and ledgers for both runs: `artifacts/falsification/`.

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
