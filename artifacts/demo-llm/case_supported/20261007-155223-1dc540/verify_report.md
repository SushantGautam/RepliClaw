# RepliClaw Verification Report

**Claim:** Treatment increases the event rate by ~50% (published RR=1.5) versus control.
**Backend:** llm
**Run:** `run-6b035e9ffbcf`

## Verdict

### `SUPPORTED`  (confidence 0.980)

Weighted evidence score +6.91 in favor; 3 support / 0 contradict; 0 replication(s). No unresolved independent conflict.

- Independent evidence: **3** agents
- Support / contradict / replicate / fail-replicate: 3 / 0 / 0 / 0

## Evidence (provenance-linked)

| agent | relation | executable | confidence | commitment |
|---|---|---|---|---|
| inv-analyst-1 | supports | True | 0.95 | `cmt-inv-analyst-1-c50c3848` |
| inv-statistician-1 | supports | True | 1.00 | `cmt-inv-statistician-1-49b64c02` |
| inv-falsifier-1 | supports | True | 0.95 | `cmt-inv-falsifier-1-ee9d63a5` |

## Usage

- LLM calls: 3
- Total tokens: 2565
- Wall clock: 7.663s

Run directory: `artifacts/demo-llm/case_supported/20261007-155223-1dc540`