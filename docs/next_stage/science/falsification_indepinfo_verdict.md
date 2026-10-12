# Independent evidence escrow under fragmentation — short scientific verdict

**Question.** Does independent evidence escrow (partitioned, pre-disclosure-sealed
investigators) help RepliClaw under genuinely fragmented, contradictory, and
potentially deceptive evidence — compared with pooled analysis under a matched
evidence union and matched total spend?

**Not** a claim that escrow must win. The mission is to determine whether it
helps, preserving negative outcomes.

## Instrument (all on `dev`, real LLM, no mocks)

- **Arms (matched evidence union + matched per-claim envelope):**
  1. `escrowed_independent` — N=4 `PartitionedInvestigator`s, one per evidence
     source, each seeing **only its own partition**, each sealing a per-claim
     verdict via the real escrow ledger before any peer is seen, then reveal +
     strict-majority aggregation.
  2. `open_sharing` — N=4, all evidence, initial verdict → share → finalize.
  3. `central_adaptive` — 1 strong manager, all evidence, adaptive re-checks.
  4. `single_investigator` — 1, all evidence, single pass.
  The escrowed partitions exactly tile the union the pooled arms see; no arm
  gets secret extra evidence.
- **Dataset:** `adversarial_audit_rx441/v1` — pharma formulation RX-441, 18
  artifacts across 4 sources, **5 trap claims** (C1,C2,C3,C5,C6; 4 FALSE + 1
  TRUE) engineered so that no single source resolves any claim. sha256
  `c3d4c9399f87f188…`.
- **Model:** `Qwen/Qwen3.8-27B-FP8` (endpoint `default`), temperature 0.2.
- **Caps:** matched per-claim envelope. Default 16,000 tokens / 16 calls
  (team arm 4×4,000 tokens / 4 calls); adequate run 32,000 / 16 (team 4×8,000).
- **Reproduce (live):**
  `REPLICLAW_LLM_API_KEY=… uv run python -m repliclaw.benchmarks.falsification
   --claims C1,C2,C3,C5,C6 --token-envelope 32000 --out artifacts/falsification/<dir>`

Raw messages, usage, receipts, raw predictions, and the escrow ledger are
committed under `artifacts/falsification/live_traps_32k/` (adequate) and
`artifacts/falsification/live_c1/` (default, budget-sensitivity).

## Results (5 trap claims × 4 arms)

| Arm | Team acc | Abstain | Ind acc | Tokens | LLM calls | False-consensus |
|-----|---------:|--------:|--------:|-------:|----------:|----------------:|
| `single_investigator` | **100%** | 0% | — | **14,133** | 5 | — (n=1) |
| `central_adaptive` | **100%** | 0% | — | 50,824 | 17 | — (n=1) |
| `open_sharing` | **100%** | 0% | — | 143,982 | 47 | — |
| `escrowed_independent` | **20%** | **80%** | **90% (9/10)** | **131,474** | 79 | **1.00** |

Budget sensitivity (C1 only, 16,000 envelope): escrowed 3/4 investigators hit
the 4,000-token bound and abstained (team ABSTAIN, expected FALSE); pooled arms
correct. At 32,000 the bottleneck moves from tokens to `max_turns` (4 calls).

## What happened in the escrowed arm

- Each partitioned investigator saw only 1–3 artifacts (one source). On the
  cross-source trap claims that was often **insufficient to commit**:
  investigators ran out of calls/tokens (`status=bound`) and produced no sealed
  verdict.
- The strict-majority rule (needs >2 of 4) turned those non-commits and 2–2
  splits into **team abstentions** (4 of 5 claims).
- `false_consensus_rate = 1.0`: on **every** claim the team got wrong, at least
  one partitioned investigator had the correct verdict **individually**. The
  investigators were 90% accurate on the votes they cast; the mechanism lost
  4 of 5.

The failure is localized to the **aggregation/completion mechanism**, not to
the model's inability to judge (individual accuracy 90%).

## Verdict

On this small sample, **independent evidence escrow as implemented does not
help — it clearly hurts**: 5× lower team accuracy than the pooled arms
(20% vs 100%), 80% abstention, and ~9× the tokens of the single investigator.
There is **no evidence it helps and direct evidence it costs accuracy,
completion, and spend** under fragmentation.

Why it underperforms here: the trap claims require **cross-source
reconciliation**, which escrow deliberately defers; a single source is
insufficient to commit, the per-investigator call/token budget is the binding
constraint, and strict-majority aggregation converts the resulting
non-commits into abstentions that discard the (mostly correct) individual
verdicts.

## Honest limits (exploratory, not confirmatory)

- n=5 trap claims, 1 model, 1 dataset, temperature 0.2 — small, single-model;
  LLM sampling variance is not controlled. This is a **small live
  comparison**, not a powered experiment.
- The strict-majority aggregation and the 4-call/4,000-token per-investigator
  budget are **design choices**; a different aggregator (e.g., majority over
  committers) or a larger per-investigator budget could change the escrowed
  numbers. The finding is about this instrument, not a proof that *no* escrow
  design can help.
- All arms saw the **same evidence union**; the escrowed arm's disadvantage is
  the intended treatment (partitioned, pre-reveal access), not extra evidence
  given to pooled arms.

## What would change the conclusion

A case set where a **single source is sufficient** and cross-checking protects
against a **deceptive single-source headline** that fools the pooled arms
(pooled wrong, escrowed right). None of the 5 traps produced that pattern; the
pooled arms were correct on all 5.

**Bottom line:** on valid, fragmented, misleading evidence, independent evidence
escrow has not demonstrated a benefit; it measurably costs accuracy and spend.
Keep it only if a specific threat model (e.g., one corrupted source) is the
target and the aggregation is redesigned to aggregate over committers.
