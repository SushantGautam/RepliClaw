# VS Code rapid parallel fleet — active tasks

This file **replaces** the broad old six-lane literature/benchmark plan. Historical decisions/results remain unchanged. Work on `dev`; create one isolated worktree per editing lane, coordinator/integrator alone merges. Use `docs/next_stage/VS_CODE_FAST_FLEET.md` for launch and integration.

| Lane | Priority | Exclusive owner paths | First actual artifact | Dependency |
| --- | --- | --- | --- | --- |
| A / `rc-telemetry` | P0 | `src/repliclaw/experiments/v3/telemetry_arms.py` + focused tests of that file | Bounded/parallel investigator change preserving sealed commit -> reveal -> committee; phase and budget evidence | Existing telemetry and R9 evidence |
| B / `rc-causal` | P0 | `src/repliclaw/eess_live/**`, `src/repliclaw/counterfactual/**`, new causal-case files only | Real executable D-E/C-EQ intervention parity pilot entrypoint; 2+ distinct cases if defensible, otherwise one-case limitation | Existing P08 executor and central arm |
| C / `rc-eval` | P0 | `scripts/pilot_parallel.py`, `scripts/pilot_report.py`, new reporter files; no edit to lane A/B code | Paired observable result launcher, top-1/top-5, completions, tokens/time/phase result table | Existing saved cases/scorer |
| D / `rc-integrity` | P0 | `read-only science/code review; lead owns any new correction addendum | Evidence-based report of observational-vs-intervention claims, exposed case list and label risks; concise BLOCK/PASS; lead applies any corrections | Read-only evidence |
| Lead / `rc-speed-lead` | critical | integration/cherry-picks/new result memo | Independently running sessions in worktrees, first integrated code, real run launch, final honest outcome | All lanes |

Launch all four independent lanes immediately if session/compute support allows. Phase 2: merge A+C and run bounded real RCAEval observational pilot while B finishes causal track. Reviewer D audits one critical scientific fact at a time; do not block unrelated code execution.

Strict interface contract: no file overlap, no fabricated interventions, independent agent commitments, equal baseline executor and compute caps where causal, evaluator-only gold, same scorer, negative outcomes retained. One focused regression check per changed module, then real execution. No giant test campaign or idle documentation round. At a blockage lasting >15 min, narrow and ship an executable subset; tell the lead exact next action.
