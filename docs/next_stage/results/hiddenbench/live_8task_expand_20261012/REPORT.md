# HiddenBench (ICML 2026) — RepliClaw three-arm measurement

- **Labels:** OBSERVATIONAL, ACCESS-MATCHED (not causal), MODEL-SUBSTITUTION
- **Claim scope:** observational, access-matched. Not a causal claim.
- Git SHA: `da117fd21f2e71eaf6ad544f41b44829e782c6ce`
- Model: `default` @ `https://simulachat.sushant.pp.ua/api/v1` (model substitution, not the released baseline)
- Benchmark: `/home/susan/worktrees/repliclaw-hiddenbench/third_party/hiddenbench/data/benchmark.json` (sha256 `2815afffca4e470d…`)
- Tasks: [5, 6, 7, 8, 9, 10, 11, 12] | rounds: 3 | seed: 2026
- Caps per arm: {'max_calls_per_arm': 256, 'max_total_tokens_per_arm': 200000}
- Started: 2026-10-12T16:04:24.783326+00:00

| arm | tasks | done | acc(done) | acc(all) | indiv-acc | calls | tokens | wall s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| escrow | 8 | 8 | 0.000 | 0.000 | 0.031 | 180 | 200368 | 239.78 |
| open-share | 8 | 8 | 0.000 | 0.000 | 0.031 | 150 | 159721 | 234.32 |
| central | 8 | 8 | 0.750 | 0.750 | 0.750 | 8 | 7476 | 14.96 |

## Arm definitions
- **escrow**: per-round evidence packets + a ranked-answer commitment held in escrow (content-free pre-reveal digests, `repliclaw.escrow.phase` gate, `repliclaw.canonical` commit hashes); revealed only before the final vote; group decision = majority of final votes.
- **open-share**: official HiddenBench discussion protocol (agents see each other while reasoning); group decision = majority of final votes.
- **central**: one controller receives the pooled information (shared + all hidden facts) directly and decides in a single vote (C-EQ-style control; pooled access differs by design).

## Per-task detail

### escrow
- task 5 (baker_2010): **incorrect** — decision=Stevens, calls=24, tokens=44394
- task 6 (schulz_hardt_mojzisch_2012): **incorrect** — decision=Candidate B, calls=18, tokens=16589
- task 7 (graetz_et_al_1998): **incorrect** — decision=Cape Industries, calls=24, tokens=30958
- task 8 (Stasser_Stewart_1992): **incorrect** — decision=Mickey Malone, calls=18, tokens=19799
- task 9 (critical_hospital_transfer): **incorrect** — decision=Hospital B, calls=24, tokens=21691
- task 10 (emergency_supply_drop): **incorrect** — decision=Warehouse B, calls=24, tokens=21941
- task 11 (emergency_conference_relocation): **incorrect** — decision=City Library, calls=24, tokens=22519
- task 12 (evacuate_park_dilemma): **incorrect** — decision=Blueberry Ridge, calls=24, tokens=22477
### open-share
- task 5 (baker_2010): **incorrect** — decision=Stevens, calls=20, tokens=34314
- task 6 (schulz_hardt_mojzisch_2012): **incorrect** — decision=Candidate B, calls=15, tokens=11568
- task 7 (graetz_et_al_1998): **incorrect** — decision=Cape Industries, calls=20, tokens=25484
- task 8 (Stasser_Stewart_1992): **incorrect** — decision=Mickey Malone, calls=15, tokens=13665
- task 9 (critical_hospital_transfer): **incorrect** — decision=Hospital B, calls=20, tokens=18515
- task 10 (emergency_supply_drop): **incorrect** — decision=Warehouse B, calls=20, tokens=19008
- task 11 (emergency_conference_relocation): **incorrect** — decision=City Library, calls=20, tokens=17991
- task 12 (evacuate_park_dilemma): **incorrect** — decision=Blueberry Ridge, calls=20, tokens=19176
### central
- task 5 (baker_2010): **correct** — decision=Roberts, calls=1, tokens=1940
- task 6 (schulz_hardt_mojzisch_2012): **correct** — decision=Candidate C, calls=1, tokens=810
- task 7 (graetz_et_al_1998): **incorrect** — decision=Franklin Enterprises, calls=1, tokens=1175
- task 8 (Stasser_Stewart_1992): **incorrect** — decision=Mickey Malone, calls=1, tokens=894
- task 9 (critical_hospital_transfer): **correct** — decision=Hospital A, calls=1, tokens=663
- task 10 (emergency_supply_drop): **correct** — decision=Warehouse C, calls=1, tokens=655
- task 11 (emergency_conference_relocation): **correct** — decision=School Gym, calls=1, tokens=654
- task 12 (evacuate_park_dilemma): **correct** — decision=Green Valley, calls=1, tokens=685

