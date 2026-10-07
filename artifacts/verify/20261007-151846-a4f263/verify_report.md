# RepliClaw Verification Report

**Claim:** Treatment increases the event rate by 50% (published RR=1.5) versus control.
**Backend:** deterministic
**Run:** `run-7003b5ef200a`

## Verdict

### `REFUTED`  (confidence 0.256)

Independent conflict between ['inv-analyst-1', 'inv-falsifier-1', 'inv-followup-2a4dd2', 'inv-statistician-1'] was ADJUDICATED by independent follow-up inv-followup-2a4dd2 (contradicts, executable=True); weighted score +0.12. Recovery from misleading evidence.

- Independent evidence: **4** agents
- Support / contradict / replicate / fail-replicate: 2 / 2 / 0 / 0

## Surfaced disagreements

- agents: ['inv-analyst-1', 'inv-falsifier-1', 'inv-followup-2a4dd2', 'inv-statistician-1']

## Follow-up needs (plannerless)

- **falsification** (priority 2.00): independent re-analysis of claim 'Treatment increases the event rate by 50% (published RR=1.5) versus control.' — investigators [inv-analyst-1, inv-falsifier-1, inv-statistician-1] disagree; recompute the primary test from raw data with a different method

## Evidence (provenance-linked)

| agent | relation | executable | confidence | commitment |
|---|---|---|---|---|
| inv-analyst-1 | supports | True | 0.60 | `cmt-inv-analyst-1-9e104c03` |
| inv-statistician-1 | supports | True | 0.90 | `cmt-inv-statistician-1-4b72eeda` |
| inv-falsifier-1 | contradicts | True | 0.70 | `cmt-inv-falsifier-1-48aac176` |
| inv-followup-2a4dd2 | contradicts | True | 0.70 | `cmt-inv-followup-2a4dd2-3e8c98f0` |

## Usage

- LLM calls: 0
- Total tokens: 0
- Wall clock: 0.013s

Run directory: `artifacts/verify/20261007-151846-a4f263`