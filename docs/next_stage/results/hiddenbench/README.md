# HiddenBench (ICML 2026) integration — three-arm measurement

Adapter: `src/repliclaw/benchmarks/hiddenbench/` over the vendored official
benchmark (`third_party/hiddenbench/`, unmodified copy of
`github.com/Yassellee/HiddenBench_ICML`, pinned commit in
`VENDOR_PROVENANCE.txt`).

**Claim scope (mandatory labels):** OBSERVATIONAL / ACCESS-MATCHED —
never causal. When the endpoint model is not the benchmark's released
baseline, all results are MODEL-SUBSTITUTION (our runs use the SimulaChat
`default` model = Qwen3.8-27B).

## Arms (identical tasks, prompts, agent count, fact assignment, rounds)
- `escrow` — per-round evidence packets + a ranked-answer commitment held in
  escrow (`repliclaw.escrow.phase.PhaseGate`, `repliclaw.canonical` commit
  hashes, content-free pre-reveal digests); revealed only before the final
  vote. Group decision = majority of final votes.
- `open-share` — official HiddenBench discussion protocol (agents see each
  other while reasoning). Group decision = majority of final votes.
- `central` — one controller receives the pooled information (shared + all
  hidden facts) directly and decides in one vote (C-EQ-style control; pooled
  access differs by design and is labeled as such).

## Reproduce a live small run (4 tasks, ~5 min wall, ~170 LLM calls)
```bash
cd <worktree>
export REPLICLAW_LLM_API_KEY="$(cat ~/.config/simulachat.key)"
uv run python -m repliclaw.benchmarks.hiddenbench.runner \
    --task-ids 1,2,3,4 --rounds 3 --seed 2026 \
    --max-calls 256 --max-tokens 200000 \
    --out docs/next_stage/results/hiddenbench/live_4task_<date>
```
Expansion: `--task-ids 5,6,7,8,9,10,11,12` (see
`live_8task_expand_20261012/`). Full benchmark: omit `--task-ids`
(65 tasks; scale caps accordingly).

## Offline smoke (no network)
```bash
uv run pytest tests/test_hiddenbench_adapter.py -q
# or: uv run python -m repliclaw.benchmarks.hiddenbench.runner --task-ids 1 --fake --out /some/dir
```

## Runs
- `live_4task_20261012/` — tasks 1–4, rounds 3, seed 2026.
- `live_8task_expand_20261012/` — tasks 5–12, same caps/seed.
  (12 tasks = 1.5% of the 65-task benchmark: directional only, no p-values,
  case-level paired reading; model substitution applies.)

## Combined 12-task reading (both live runs, seed 2026, rounds 3)
| arm | group-acc (12) | individual final-vote acc | LLM calls | tokens | completions |
| --- | --- | --- | --- | --- | --- |
| escrow | 0/12 | 0.057 | 270 | 292,634 | 12/12 |
| open-share | 0/12 | 0.120 | 225 | 236,745 | 12/12 |
| central (pooled) | 10/12 | 0.875 | 12 | 10,540 | 12/12 |

OBSERVATIONAL, MODEL-SUBSTITUTION: under Qwen3.8-27B, the 27B group could not
pool distributed hidden information in either distributed arm (0/12 in both,
individual final votes ≤ 0.12), while the pooled-information central control
scored 10/12. The two distributed arms are access-matched to each other; the
central arm differs by design (pooled direct access) and is a control, not a
causal comparison. No positive escrow-vs-open-share effect is claimed — on
this slice escrow's individual final accuracy (0.057) was below open-share's
(0.120); the escrow advantage hypothesis remains untested on this model slice.
