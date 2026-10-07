# RepliClaw Verification Report

**Claim:** Treatment increases the event rate by 50% (published RR=1.5) versus control.
**Backend:** deterministic
**Run:** `run-52ef61e393ea`

## Verdict

### `REFUTED`  (confidence 0.256)

Independent conflict between ['inv-analyst-1', 'inv-falsifier-1', 'inv-followup-a63c2b', 'inv-statistician-1'] was ADJUDICATED by independent follow-up inv-followup-a63c2b (contradicts, executable=True); weighted score +0.12. Recovery from misleading evidence.

- Independent evidence: **4** agents
- Support / contradict / replicate / fail-replicate: 2 / 2 / 0 / 0

## Surfaced disagreements

- agents: ['inv-analyst-1', 'inv-falsifier-1', 'inv-followup-a63c2b', 'inv-statistician-1']

## Follow-up needs (plannerless)

- **falsification** (priority 2.00): independent re-analysis of claim 'Treatment increases the event rate by 50% (published RR=1.5) versus control.' — investigators [inv-analyst-1, inv-falsifier-1, inv-statistician-1] disagree; recompute the primary test from raw data with a different method

## Evidence (provenance-linked)

| agent | relation | executable | confidence | commitment |
|---|---|---|---|---|
| inv-analyst-1 | supports | True | 0.60 | `cmt-inv-analyst-1-b7174a24` |
| inv-statistician-1 | supports | True | 0.90 | `cmt-inv-statistician-1-5d2492a1` |
| inv-falsifier-1 | contradicts | True | 0.70 | `cmt-inv-falsifier-1-60b3967e` |
| inv-followup-a63c2b | contradicts | True | 0.70 | `cmt-inv-followup-a63c2b-df9b7150` |

## Usage

- LLM calls: 0
- Total tokens: 0
- Wall clock: 0.014s

Run directory: `artifacts/demo/case_misleading/20261007-155220-063124`