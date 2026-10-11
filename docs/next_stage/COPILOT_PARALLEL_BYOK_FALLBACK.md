# SUPERSEDED — Do not use this parallel-process detour as the standard fix

**2026-10-11 correction:** The official Copilot CLI custom-agent reference says an agent without `model:` inherits its parent session's selected model. RepliClaw's `rc-fast`, `rc-implement`, and `rc-review` profiles now omit per-agent model overrides to use the authorized parent `sigma2.no/Qwen3.8-27B-Thinking`. This preserves **native task/fleet parallelism, /tasks supervision, and write_agent steering**. Read `AGENTS.md` and `docs/next_stage/COPILOT_FAST_SEED.md`, restart Copilot in the updated `dev` checkout, and verify one inherited-model canary. **Do not launch standalone worktree Copilot processes to work around this without a newly verified blocker and explicit direction.**

Historical fallback draft retained below for audit only; it is not current operational guidance.

---

# Copilot CLI parallel execution when BYOK custom subagents cannot resolve the model

**Operational fallback (2026-10-11):** Copilot CLI may discover `rc-*` agents and show `sigma2.no/Qwen3.8-27B-{Thinking,NonThinking}` in *Available models*, yet refuse a `task` dispatch with *"Model ... is not available."* This is an upstream BYOK/subagent model-catalog compatibility issue, NOT evidence that the Sigma2 endpoint is down. This session saw the exact contradiction. Do **not** spend more than one short check changing `providers.json`, `infer`, the backend weights or `modelPolicy: required`; none of those is proven to fix the runtime. **Do not remove the model policy or fall back to Copilot-hosted models.**

Similar documented cases: https://github.com/microsoft/vscode/issues/333802 ; https://github.com/github/copilot-cli/issues/3891 ; https://github.com/github/copilot-cli/issues/2554 . Exact root cause on each installed CLI version requires its logs.

## Fastest safe bypass: parallel top-level Copilot CLI processes, not subagents

Copilot officially supports `-C DIR`, `--agent`, `--model`, `--mode=autopilot`, `--worktree`, `-p`, and separate interactive sessions. **A top-level Copilot process** resolves the same Sigma2 model already shown working for the orchestrator; the failing nested-model resolver is bypassed. Test its actual resolved model/provider before accepting outputs. Top-level workers are **independent sessions**, so `/tasks` and `write_agent` in the coordinator **cannot** supervise or steer them as native child tasks. Use process logs + the shared heartbeat ledger, and stop/relaunch a worker with a narrower prompt to steer it.

**Current task allocation: FF-01 CI is already being handled on dev.** Do not start a second CI worker. Run FF-02 (label leakage) and FF-03 (statistical-null interpretation) independently in parallel. Reassign capacity to FF-04 (real matched interventions) as soon as either exits successfully. Respect the no-new-live-campaign-without-approval gate.

### Prepare distinct worktrees — run ONCE in a NEW terminal, not inside a busy Copilot session

```bash
cd ~/projects/RepliClaw                 # adjust if your actual repo root differs
git fetch origin dev                     # fetch is safe with a dirty current worktree
git worktree list                        # inspect before adding; don't recreate existing branches
git worktree add -b ff-02-labels ../RepliClaw-ff-02 origin/dev
git worktree add -b ff-03-stats ../RepliClaw-ff-03 origin/dev
```

If a named worktree/branch already exists, **reuse it** and skip that `git worktree add` command. Git will refuse accidental reuse. Never force-delete a worktree containing agent changes. Neither worker writes into the busy `dev` checkout; the integrator cherry-picks verified worker commits after review.

### Worker A — terminal/SSH session A (Sigma2 THINKING only)

```bash
copilot -C ~/projects/RepliClaw-ff-02 \
  --agent rc-implement --model sigma2.no/Qwen3.8-27B-Thinking \
  --mode autopilot --no-sandbox --allow-all --no-ask-user \
  -p 'FF-02 ONLY. Read AGENTS.md and FAST_FINISH_RUNBOOK.md. Fix evaluator-label exposure: case IDs / service ordinal must not let the tested agent recover root_cause_service. Add one adversarial failing-then-passing test. Smallest patch, run focused tests, commit only to ff-02-labels. Do NOT launch subagents, delegate or fleet. Do NOT touch main/dev, hidden labels in prompts, or live experiments. After one meaningful fix provide STATUS, COMMIT SHA, TEST COMMAND/RESULT and NEXT BLOCKER. Use REPLICLAW_FLEET_DIR if present for heartbeat. Do not detour.'
```

### Worker B — terminal/SSH session B (Sigma2 THINKING only)

```bash
copilot -C ~/projects/RepliClaw-ff-03 \
  --agent rc-implement --model sigma2.no/Qwen3.8-27B-Thinking \
  --mode autopilot --no-sandbox --allow-all --no-ask-user \
  -p 'FF-03 ONLY. Read AGENTS.md and docs/next_stage/science/monte_carlo_power_v3.md. Correct the scientific interpretation: under a genuine Δ=0 null, both arms have equal case-conditional probabilities; forcing only D-E to 100% creates a real effect, not a type-I false positive. Fix the narrow analysis/explanation, add or run one decisive reproducible null check, and preserve results as simulation only. Commit only to ff-03-stats, do not modify preregistered P08, do not launch subagents/fleet/live trials. Finish with STATUS, COMMIT SHA, CHECK, NEXT; no unrelated study.'
```

Both commands are **independent** and can run simultaneously in separate terminals. They exit when `-p` completes. For persistent SSH/disconnect-safe execution, invoke each command via `nohup ... > PATH.log 2>&1 &` (or a proper managed terminal session), using distinct log paths. Do not claim background persistence or confirmed Sigma2 routing without checking the process and log.

### Shared heartbeat ledger across worktrees

In the shell that launches the workers, set `REPLICLAW_FLEET_DIR` to one absolute, writable path and pass it to **all** worker processes. Example:

```bash
export REPLICLAW_FLEET_DIR="$HOME/projects/RepliClaw/.artifacts/copilot-fleet"
python ~/projects/RepliClaw/scripts/copilot_fleet_watch.py assign FF-02 --agent rc-implement --deadline-min 30 --progress "label isolation"
python ~/projects/RepliClaw/scripts/copilot_fleet_watch.py assign FF-03 --agent rc-implement --deadline-min 25 --progress "true null-stat interpretation"
python ~/projects/RepliClaw/scripts/copilot_fleet_watch.py watch --loop --every 60
```

A periodic watcher is **not** a process supervisor; a missing heartbeat is a reason to inspect the terminal/log/process before killing a legitimate long test. If the separate CLI processes do not call `beat` as instructed, the watcher can only mark them stale, not tell you what was executed. The worker must periodically write measurable results and the coordinator must inspect the actual commits; no shortcut around evidence.

### Verification, integration, handoff

```bash
git -C ~/projects/RepliClaw-ff-02 log -1 --oneline
git -C ~/projects/RepliClaw-ff-03 log -1 --oneline
git -C ~/projects/RepliClaw worktree list
```

Review diffs/tests and cherry-pick into `dev` as the **single integrator**; always rebase/re-test against the latest `dev`, because the CI worker may have committed changes during these tasks. Never edit `main`. Report FF-02/FF-03 complete only when the commits, tests and checks really exist.

Once a future Copilot CLI release fixes BYOK child resolution, revert to native `task`/`fleet` **only after a one-shot model/provider routing canary**. Do not block the research result waiting for this fix.

Official flags: https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference
