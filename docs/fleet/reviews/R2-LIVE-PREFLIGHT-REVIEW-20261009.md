# Independent Review — R-2 Live Pre-Flight (first authorized live measurement, 2026-10-09)

> **Reviewer:** general-purpose science+code review agent (read-only, post-execution)
> **Target:** `artifacts/p08/token_floor_r2_20261009T105739Z/` (floor_r2.json + 3 full run trees) at HEAD `81256a3`.
> **R-2 VERDICT: ACCEPT-WITH-NOTES.** Campaign readiness: YES from a budget standpoint (120 runs
> projected 1.9M–3.1M tokens = 18–29% of the 10.8M master ceiling; worst case all-120-at-full-
> envelope = 7.2M < 10.8M — a mid-campaign ceiling trip is arithmetically impossible as long as
> the per-arm 60k envelope holds).

## 1. Provenance — PASS
- floor_r2.json ↔ each arm's budget_ledger.json: exact match (S4 16,300 tok / 104.052584 s /
  1 call / completed; S3 15,993 / 105.958439; S0 8,588 / 57.374145). Statuses match
  run_metadata.json. max_arm_usage_fraction 0.2717 = 16,300/60,000; verdict OK per
  scripts/r2_preflight.py (FLOOR_FLAG_FRACTION 0.60).
- pin/tree_sha 81256a30… identical in floor_r2.json and all three run_metadata.json; git
  confirms 81256a3 was HEAD at run time.
- a9_defect_instruction_sha256 `5c7192eb…996e7` identical across arms AND independently
  recomputed from src/repliclaw/defect_adjudication.py → same hash.
- envelope_sha256 `fa6f4b41…831bc1c` independently recomputed (sha256 of compact sorted JSON
  {max_agents:4, max_tokens:60000, max_wall_s:900.0}) → exact match.

## 2. Frozen-setting parity — PASS
All three run_metadata.json: model=Qwen3.8-27B, endpoint=https://ai-gateway.sigma2.no/v1,
temperature=0.2, max_tokens=4096, max_calls=64, timeout=120.0, harness_seed=20261010,
lam=0.5, mu=0.5, max_cycles=6, lease_ttl_s=120.0, offline_arm=false, client_factory=live,
envelope {60000, 900.0, 4}. --assert-frozen (runner.py:287-305) is enforced pre-run — a
deviating run could not have produced status=completed. No deviation from protocol frozen
settings; model/endpoint = operator-specified sigma2 config.

## 3. Science — PLAUSIBLE, two caveats
- S0 (8,588) ≈ half of S3/S4 (~16k), matching 1 agent vs 3 (S3 run.json n_investigators: 3).
  S3 split 4,532 prompt / 11,461 completion over 4 LLM calls in 106 s — realistic for
  Qwen3.8-27B. Verdicts non-trivial and case-correct (stale 14-day refund window vs 30-day
  policy; defect_class judge_stale; 3 independent supports in S4). Timestamps reconstruct a
  clean sequential S4→S3→S0 execution matching the protocol loop.
- Caveat A: the contract ledger records a single harness-level call with completion_tokens: 0
  (runner.py:556-585, A8 design "real LLM usage") — all 16k attributed to prompt_tokens;
  per-call completion breakdown survives only in S3 run.json. Acknowledge in the result
  disclosure so floors aren't misread as pure prompt cost.
- Caveat B: run_metadata start_ts == end_ts (both written at metadata-write time,
  runner.py:857-858) — misleading provenance field. ACTUAL START RECOVERABLE from run.json /
  evidence. **FIXED post-review** (see addendum).

## 4. Headroom — ADEQUATE
Measured 3 arms: 40,881 × 20 = 817,620. S5/A1/A3 floors UNKNOWN — the prior S5 figure
(1,358–1,380, artifacts/p08/live_token_floor/floor.json) is STALE (pre-A8, 3-agent envelope,
uncertain verdict; do not budget from it). Expected total ~1.78M; aggressive 3×-floor band
2.8M; reviewer band 16–26k/run → 1.92M–3.12M. Pathological all-120-at-60k = 7.2M < 10.8M.
Headroom ≥3.4× over worst case. Binding risk = per-run quality (aborted_budget wastes a run
slot), not the master ceiling.

## 5. Security / leak — PASS
`grep -rn sk-RK7F` across artifacts/ src/ scripts/ docs/ → zero hits. Case-insensitive
grep for api_key|authorization|bearer across the full run tree → zero hits. No auth material
in traces.jsonl / store.jsonl / events / verdicts / metadata.

## 6. Protocol deviations — MINOR
1. --case policy_rag → canonical policy_rag_v1 via alias (case_loader.py:41-42): protocol intent, not a deviation.
2. One extra live smoke-probe chat call before the 3 arm runs — outside the floor record, token-excluded; documented in PROGRESS.md disclosure.
3. floor_r2.json wall_s = ledger clock vs run_metadata wall_s = monotonic t0 (marginally different; consistent).
4. start_ts/end_ts identity = code bug (Caveat B), fixed post-review.
5. Arm order, flags, out layout, floor schema, pin: protocol-verbatim.

## Notes for the record
(a) fix runner start_ts before the 120 campaign trees — DONE (addendum);
(b) document the smoke-probe call in disclosures — DONE (PROGRESS.md R-2 entry);
(c) disclose the ledger's single-call completion_tokens:0 shape in the result disclosure;
(d) S5/A1/A3 floors genuinely unmeasured — baseline on first campaign runs + re-check headroom.

## Campaign readiness answer
Launch-ready from a budget standpoint: 16–26 k tokens/run × 120 = 1.9M–3.1M tokens
(18–29% of the 10.8M ceiling), ≥3.4× margin; pathological case 7.2M. The master ceiling
cannot trip mid-campaign. Binding constraints are per-run quality and the unmeasured
S5/A1/A3 floors — covered by the per-arm envelope plus a post-first-S5 headroom re-check.

---

## Addendum (integrator, 2026-10-09)
Caveat B fixed: `src/repliclaw/comparators/runner.py` now captures `start_iso` at
`run_one_arm` entry (alongside `t0`) and writes it as `start_ts`, leaving `end_ts` at
metadata-write time. Verified on a fresh offline run: start_ts 11:10:10.107958 < end_ts
11:10:10.394168, gap 0.286 s == wall_s. Fix lands with this review in the same commit as
the R-2 evidence; the three committed R-2 run trees retain the pre-fix start_ts values
(actual start is recoverable from run.json per the review), disclosed as such.
