# Fast-finish runbook — VS Code sessions (replaces CLI runbook)

**Active workflow:** `AGENTS.md` + `VS_CODE_FAST_FLEET.md` + `SEED_PROMPT.md`. The previous Copilot CLI sprint is CLOSED. Its scored results and historical `FAST_FINISH_STATUS.md` remain evidence, **not new tasks**. Do not launch the obsolete FF-01..FF-07 tasks.

## Start now
1. Open RepliClaw `dev` in VS Code; `git fetch origin && git switch dev && git pull --ff-only origin dev`. Inspect dirty files before changing. Existing `main` remains untouched.
2. Start separate VS Code Agent/Agent Host **sessions with different worktrees** for four independent lanes, preferably in parallel. Do not confuse multiple chats in a single worktree with isolated work. If the chosen harness supports session tools, the lead may spawn and monitor sessions directly; otherwise create sessions in the Agents window and paste each lane task there. Do not invent an agent-spawn API.
3. Use `rc-speed-lead` for coordination; `rc-telemetry`, `rc-causal`, `rc-eval`, `rc-integrity` are dedicated agent profiles. Let the selected model be the user's authorized Sigma2 Qwen3.8 model; do not assume custom BYOK works on every remote Agent Host.
4. Integration lead alone updates `dev`; lane owners commit to isolated worktree branches and send SHA + changed paths. Merge/cherry-pick completed nonconflicting work promptly. If an environment lacks isolated worktrees, do not run simultaneous modifying agents on the same checkout.
5. Use `docs/next_stage/SEED_PROMPT.md` as the kickoff text. First code commit or real run artifact, not an essay, is the required first checkpoint.

## Targets
- **Within ~30 min:** parallel investigators with bounded turns and escrow invariant (observational lane); working causal executor entrypoint or exact blocker (causal lane); honest score/runner interface (evaluation lane); truth/label findings (integrity lane).
- **Within ~90–120 min:** bounded paired live observational result from the existing RCAEval cases with a changed D-E implementation and the unchanged strongest C-EQ. Never relabel reused cases as heldout.
- **Within ~2–4 h:** separate actual executable intervention comparison on genuinely different controlled cases if they exist or can be constructed legitimately; else runnable one-case demo and clear limitation. Aggregate a short reproducible report on `dev`.

Run only focused tests necessary to ensure a runnable comparison, then real jobs. No wide pytest cycles after every edit, no additional literature/repo survey, no new benchmark/provider plumbing. A negative result is an acceptable outcome. Do not modify previously frozen instruments/results; give new experiments new versioned paths.

## Acceptance
A reader can run an actual command (with the user's endpoint configured) and inspect **both arms' raw outputs and exact resource spend**. Distinguish observational RCAEval access parity from genuine P08-style counterfactual interventions. Report phase-1/2/3 coverage, top-1/top-5, completion, per-case tokens and time, and new-vs-old changes. No unsupported causal superiority or confirmatory claims.
