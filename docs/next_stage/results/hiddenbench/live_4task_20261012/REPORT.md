# HiddenBench (ICML 2026) — RepliClaw three-arm measurement

- **Labels:** OBSERVATIONAL, ACCESS-MATCHED (not causal), MODEL-SUBSTITUTION
- **Claim scope:** observational, access-matched. Not a causal claim.
- Git SHA: `d238af8e22f8ed2725078fc0426b33d09b5fff80`
- Model: `default` @ `https://simulachat.sushant.pp.ua/api/v1` (model substitution, not the released HiddenBench baseline)
- Benchmark: `/home/susan/worktrees/repliclaw-hiddenbench/third_party/hiddenbench/data/benchmark.json` (sha256 `2815afffca4e470d…`)
- Tasks: [1, 2, 3, 4] | rounds: 3 | seed: 2026
- Caps per arm: {'max_calls_per_arm': 256, 'max_total_tokens_per_arm': 200000}
- Started: 2026-10-12T16:00:26.305023+00:00

| arm | tasks | completed | group-acc (completed) | group-acc (all) | indiv-final acc | LLM calls | tokens | wall s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| escrow | 4 | 4 | 0.000 | 0.000 | 0.083 | 90 | 92266 | 126.44 |
| open-share | 4 | 4 | 0.000 | 0.000 | 0.208 | 75 | 77024 | 97.32 |
| central | 4 | 4 | 1.000 | 1.000 | 1.000 | 4 | 3064 | 5.86 |

## Arm definitions
- **escrow**: per-round evidence packets + a ranked-answer commitment held in escrow (content-free pre-reveal digests, `repliclaw.escrow.phase` gate, `repliclaw.canonical` commit hashes); revealed only before the final vote; group decision = majority of final votes.
- **open-share**: official HiddenBench discussion protocol (agents see each other while reasoning); group decision = majority of final votes.
- **central**: one controller receives the pooled information (shared + all hidden facts) directly and decides in a single vote (C-EQ-style control; pooled access differs by design).

## Per-task detail

### escrow
- task 1 (evacuation_west_city): **incorrect** — decision=East Town, calls=24, tokens=24564
- task 2 (evacuation_north_hill): **incorrect** — decision=East Town, calls=24, tokens=25914
- task 3 (evacuation_east_town): **incorrect** — decision=West City, calls=24, tokens=24629
- task 4 (toma_butera_2009): **incorrect** — decision=Mrs. Y, calls=18, tokens=17159
### open-share
- task 1 (evacuation_west_city): **incorrect** — decision=East Town, calls=20, tokens=21550
- task 2 (evacuation_north_hill): **incorrect** — decision=East Town, calls=20, tokens=21806
- task 3 (evacuation_east_town): **incorrect** — decision=West City, calls=20, tokens=19529
- task 4 (toma_butera_2009): **incorrect** — decision=Mrs. Y, calls=15, tokens=14139
### central
- task 1 (evacuation_west_city): **correct** — decision=West City, calls=1, tokens=764
- task 2 (evacuation_north_hill): **correct** — decision=North Hill, calls=1, tokens=774
- task 3 (evacuation_east_town): **correct** — decision=East Town, calls=1, tokens=755
- task 4 (toma_butera_2009): **correct** — decision=Mr. X's son, calls=1, tokens=771

