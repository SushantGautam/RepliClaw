# RepliClaw Demo Transcript

**Backend:** `deterministic` | **Generated:** 2026-10-07T13:52:20Z

Everything below is produced by the runs themselves (no injected values, AC18).

## Case 1 — genuine supported claim

Weighted evidence score +6.26 in favor; 3 support / 0 contradict; 0 replication(s). No unresolved independent conflict.

**Verdict: `SUPPORTED`** (confidence 0.980)

Report: `artifacts/demo/case_supported/20261007-155220-142f38/verify_report.md`

---

## Case 2 — misleading artifact (conflict → autonomous follow-up)

**Phase 2 — visible commitments BEFORE reveal** (tamper-evident hashes; content sealed):

| agent | commitment_id | content_hash (sealed, no content visible) | committed_at |
|---|---|---|---|
| inv-analyst-1 | `cmt-inv-analyst-1-b7174a24` | `19cb267211fb42a8…` | 2026-10-07T13:52:20Z |
| inv-statistician-1 | `cmt-inv-statistician-1-5d2492a1` | `7d5d542a744e210e…` | 2026-10-07T13:52:20Z |
| inv-falsifier-1 | `cmt-inv-falsifier-1-60b3967e` | `f98dc802ffd4fcc0…` | 2026-10-07T13:52:20Z |

_Note: at this point the run store would return metadata only (`read_sealed_commitment(revealed=False)`); reading content now raises `IsolationViolation`. Reveal timestamps and `reveal_verified: true` are recorded in `commitments/*.json` after the reveal phase._

**Phase 3 — revealed evidence** (verified against the commitments):

| agent | relation | conclusion | executable | confidence |
|---|---|---|---|---|
| inv-analyst-1 | supports | supported | True | 0.60 |
| inv-statistician-1 | supports | supported | True | 0.90 |
| inv-falsifier-1 | contradicts | refuted | True | 0.70 |
| inv-followup-a63c2b | contradicts | refuted | True | 0.70 |

**Phase 5 — autonomous follow-up need(s)** (plannerless):

- **falsification** (priority 2.00): independent re-analysis of claim 'Treatment increases the event rate by 50% (published RR=1.5) versus control.' — investigators [inv-analyst-1, inv-falsifier-1, inv-statistician-1] disagree; recompute the primary test from raw data with a different method

**Phase 6 — final provenance-linked verdict:**

### `REFUTED`  (confidence 0.256)

Independent conflict between ['inv-analyst-1', 'inv-falsifier-1', 'inv-followup-a63c2b', 'inv-statistician-1'] was ADJUDICATED by independent follow-up inv-followup-a63c2b (contradicts, executable=True); weighted score +0.12. Recovery from misleading evidence.

Report: `artifacts/demo/case_misleading/20261007-155220-063124/verify_report.md`