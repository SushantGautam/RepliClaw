# RepliClaw — VS Code parallel fleet, hours-to-result

**Do not use Copilot CLI orchestration.** Use VS Code Agents window / Agent Host or local VS Code agent with your existing Sigma2 Qwen BYOK setup. Native VS Code sessions can run simultaneously; use isolated worktrees for simultaneous code edits. A separate agent chat in the same session shares that session's working tree and cannot safely edit the same files in parallel.

## Launch: one integrator + four immediate sessions
- Integrator on `dev`: `rc-speed-lead`, uses `SEED_PROMPT.md`.
- Worktree/session A: `rc-telemetry` (fix D-E phase-1 sequential and uncontrolled continuation; commit/reveal must still be real).
- Worktree/session B: `rc-causal` (reuse actual P08 counterfactual executor and adaptive C-EQ to obtain executable interventions; never pass recorded telemetry off as interventions).
- Worktree/session C: `rc-eval` (minimal pilot harness/report; no changes to A/B-owned modules).
- Worktree/session D: `rc-integrity` (small read-only integrity review + versioned claims correction).

Start sessions from the Agents window using the corresponding workspace agent, select the verified Sigma2 Qwen3.8 Thinking/NonThinking model **per session**, and choose a separate worktree for each session. If the harness cannot start sessions programmatically, open four sessions manually; do not spend a half-hour debugging orchestration APIs. Running a local VS Code agent against the remote SSH workspace is preferable to switching to an unapproved model. If additional capacity exists, add independent reproduction/critical-review sessions ONLY after A/B/C/D are dispatched.

### Fallback manual worktrees (optional, run in a local repo parent)
```bash
git fetch origin
git switch dev
git pull --ff-only origin dev
git worktree add -b sprint/rc-telemetry ../RepliClaw-telemetry dev
git worktree add -b sprint/rc-causal ../RepliClaw-causal dev
git worktree add -b sprint/rc-eval ../RepliClaw-eval dev
git worktree add -b sprint/rc-integrity ../RepliClaw-integrity dev
```
If any branch/worktree already exists, reuse it only after checking its owner and state or choose a new unique name. **Never reset or force-push work you do not own.** Open each path as a distinct VS Code agent session. Integrator on clean dev cherry-picks reviewed commits in dependency order or merges isolated branches.

## Time discipline and true deliverable
- **0–5 min:** check dev SHA, claim disjoint paths, dispatch four agents. No all-repo reading.
- **5–30 min:** each lane ships a minimally runnable change or direct blocker with exact file/command. Lead reads session updates and narrows tasks; no more than 10 min without a real inspection when actively supervising.
- **30–120 min:** integrate A+C as soon as runnable; paired live observations on reused RCAEval pilot cases; freeze current input and report actual metrics (no independent heldout claim). B runs in parallel and can deliver a one-case executable causal demo before distinct controlled cases exist.
- **2–4 h:** deliver a succinct measured outcome, commands, case/seed/model/caps, raw run directories, original failures and revised claims. This is a target, not a promise of background execution or of a positive result.

**No more slow testing loops:** minimal focused checks for code that actually changed, one runnable end-to-end sample, then the real bounded measurement. Do not replay old 150K failure experiment unchanged. Do not rerun passing full pytest 20 times. Never turn off a failing scientific integrity check or give D-E extra information secretly. Do not use hidden labels as demonstrations.

## Evidence and stop conditions
At checkpoint send: `TASK / CHANGED FILES + SHA / ONE VERIFIED COMMAND OR RUN / OBSERVED OUTCOME / BLOCKER / NEXT ACTION`. The lead updates the user after a real result, not status prose. Scientific review can correct claims without blocking all unrelated engineering. Historical P08 and V3 raw artifacts remain frozen. New live experiments are exploratory until independently preregistered with genuinely fresh cases and authorized resources. If external intervention environment isn't available, ship the observational engineering result and explicitly say the causal hypothesis remains untested.
