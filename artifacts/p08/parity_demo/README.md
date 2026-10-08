# C1 same-task parity demonstration (offline, deterministic)

**Date:** 2026-10-08 · **Run branch:** repl-claw-dev @ d3beaeb · **Command:** `.venv/bin/python /tmp/parity_demo.py` (report: `parity_report.json`)

## What it demonstrates (C1, judge blocking item 6)
All four offline arms — `single_agent`, `adaptive_central`, `open_sharing_swarm`,
`eess` — were executed by `ComparatorHarness.run()` over **one Claim object and one
shared `BudgetEnvelope`** (60,000 tokens / 900 s / 4 agents; 4 because
`adaptive_central` manages 3 delegates + coordinator). Result:

- `parity: true` — all 4 arms report the identical envelope hash
  `fa6f4b413ab9b1f09e306de8c5b5a35c524587f82080d18eac441bedb831bc1c` and none
  exceeded the envelope.
- `over_budget_arms: []`.

## Honest caveats (do not over-read this artifact)
1. This proves the **matched-budget parity mechanism**, not a scientific
   comparison: verdicts here are from deterministic/offline arms on their own
   case bindings. The eess arm runs the P02 `policy_rag_v1` slice internally,
   the other arms run the claim passed in; the `correct=` column in the run log
   (fixture `clean_refuted` truth) is therefore **not a result claim** — the
   verdict divergence is a known consequence of eess being P02-bound, which is
   exactly what the in-flight `p08/runner-cli` `case_loader` work must close so
   every arm executes the same case set.
2. Live-arm parity (shared envelope across live arms) is covered by
   `test_live_arms_share_one_envelope_hash` in `tests/test_eess_live.py` (green).
3. Full P05 parity suite: 5 `parity` tests pass on the run branch.

## Artifacts
- `parity_report.json` — full per-arm ArmResult + parity report (real output).
