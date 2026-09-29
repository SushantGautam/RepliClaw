# RepliClaw fleet — integration & independent judge procedure
Orchestrator-owned. Run this for EVERY P0 ticket before it is considered merged. Never let an author self-approve.

## Integration (main tree only, one ticket at a time)
Order: F01 → F02 → F03 → F05 (F04 is docs-only, applied to `DECISIONS.md` not the tree). For a finished worker branch:

```bash
cd /Users/sushantgautam/Documents/ScienceClawHackathon
WT=.worktrees/fNN                      # e.g. f01
BR=$(git -C $WT rev-parse --abbrev-ref HEAD)
SHA=$(git -C $WT rev-parse HEAD)
git -C $WT status --short              # must be clean (worker committed)

# 1. Gate in the WORKTREE first (fast, isolated):
$WT/.venv/bin/python -m pytest
$WT/.venv/bin/ruff check src/repliclaw/ tests/
$WT/.venv/bin/mypy src/repliclaw/

# 2. Merge into repl-claw-dev (main tree):
git merge --no-ff $BR -m "integrate: $BR ($SHA)"

# 3. Full regression in the MAIN tree (authoritative):
.venv/bin/python -m pytest
.venv/bin/ruff check src/repliclaw/ tests/
.venv/bin/mypy src/repliclaw/

# 4. E2E proof: run the ticket's repro from its handoff; capture to logs/.
# 5. Resolve conflicts ONLY if a rebase/merge hit one; re-run full gate after.
```
If the merge conflicts (another ticket already changed the same file), STOP, note it, and either re-run that worker's focused fix on top or reconcile manually — then re-gate. Never force.

## Independent judges (two, both read-only, different from the author)
Dispatch AFTER the branch is built and BEFORE (or immediately after) merge. They review the DIFF and the actual run evidence, not the author's prose.
- **Code Judge** (RepliClaw Code Judge): correctness, security (subprocess/prompt injection), concurrency/races, idempotency, test quality, contracts. Cite `file:line`, give `BLOCKER/MAJOR/MINOR`, provide an exact repro for each.
- **Science Judge** (RepliClaw Science Judge): fairness (crippled baselines?), leakage (truth/labels into prompts?), denominator correctness, calibrated-vs-heuristic confidence, alternative explanations (more compute? data peek? post-hoc case selection?). Report PASS/WEAK/FAIL per axis.

Both must end with a Gate result and required remediation. If either returns a BLOCKER or MAJOR: the worker repairs in their worktree, re-gates, and BOTH judges re-review. Only then merge + checkpoint.

### Judge dispatch prompt skeleton
```
You are the <Code|Science> Judge reviewing RepliClaw ticket <FNN> on branch <BR> @ <SHA>.
Read docs/fleet/FNN.md (acceptance), docs/fleet/handoff-FNN.md, and the diff
(`git -C /Users/.../.worktrees/fNN diff a14fa67..HEAD`).
Reproduce the key claims by running the handoff repro commands yourself.
Do not edit. Report Blockers/Majors/Minors with file:line + repro, then a Gate result.
```

## Checkpoint (after each merged P0 ticket)
Create `docs/checkpoints/CP-<date>-<ticket>.md`: HEAD SHA, exact commands + observed output, per-strategy/scientific numbers (real), confidence limits, reviewer verdicts, next action. Append a short `PROGRESS.md` entry. Update `EXECUTION_STATE.md`.

## Hard rules
- One state writer (orchestrator). Workers never touch EXECUTION_STATE/PROGRESS/DECISIONS/README/TASK_SPEC/AGENTS/IMPLEMENTATION_PLAN on the shared branch.
- A failed or tied experiment stays recorded as-is. No metric is reported that isn't in a run artifact.
- Worktrees are code isolation, not sandboxing: no API keys, datasets, or secrets in worker output/commits.
