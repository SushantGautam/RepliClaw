# RepliClaw Demo Transcript

**Backend:** `llm` | **Generated:** 2026-10-07T13:53:13Z

Everything below is produced by the runs themselves (no injected values, AC18).

## Case 1 — genuine supported claim

Weighted evidence score +6.91 in favor; 3 support / 0 contradict; 0 replication(s). No unresolved independent conflict.

**Verdict: `SUPPORTED`** (confidence 0.980)

Report: `artifacts/demo-llm/case_supported/20261007-155223-1dc540/verify_report.md`

---

## Case 2 — misleading artifact (no unresolved conflict this run)

**Phase 2 — visible commitments BEFORE reveal** (tamper-evident hashes; content sealed):

| agent | commitment_id | content_hash (sealed, no content visible) | committed_at |
|---|---|---|---|
| inv-analyst-1 | `cmt-inv-analyst-1-3db2ed58` | `41f26c7abbf388ab…` | 2026-10-07T13:52:38Z |
| inv-statistician-1 | `cmt-inv-statistician-1-28a6e7c3` | `9ac7081761153788…` | 2026-10-07T13:52:38Z |
| inv-falsifier-1 | `cmt-inv-falsifier-1-6af9f6c5` | `b58401e344cbc281…` | 2026-10-07T13:52:38Z |

_Note: at this point the run store would return metadata only (`read_sealed_commitment(revealed=False)`); reading content now raises `IsolationViolation`. Reveal timestamps and `reveal_verified: true` are recorded in `commitments/*.json` after the reveal phase._

**Phase 3 — revealed evidence** (verified against the commitments):

| agent | relation | conclusion | executable | confidence |
|---|---|---|---|---|
| inv-analyst-1 | contradicts | refuted | True | 0.99 |
| inv-statistician-1 | contradicts | refuted | True | 0.99 |
| inv-falsifier-1 | contradicts | refuted | True | 1.00 |

**Phase 5 — autonomous follow-up need(s)** (plannerless):

- (no follow-up needed — investigators agreed)

**Phase 6 — final provenance-linked verdict:**

### `REFUTED`  (confidence 0.980)

Weighted evidence score -7.00 against; 0 support / 3 contradict; 0 failed replication(s). No unresolved independent conflict.

Report: `artifacts/demo-llm/case_misleading/20261007-155230-0fe5d2/verify_report.md`