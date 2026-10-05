# Safe migration from RepliClaw fleet v1 → Evidence-Escrow Swarm v2
Date: 2026-10-08. **Never discard work that VS Code agents have already produced.** The strategy documents were created on an isolated branch because local worktrees/sessions cannot be observed through GitHub.

## Sequence — human + orchestrator
A. **Checkpoint existing sessions FIRST** (before stop): send the old orchestrator the "pause prompt" below. If child sessions cannot receive it, use UI Stop at a safe point and preserve worktrees.
B. The old orchestrator must stop *new dispatch*, let in-flight commands finish safely, inventory all active child sessions, branches/worktrees, uncommitted edits, changed paths, current SHA, test outputs, pending hypotheses and costs. Save an append-only handoff checkpoint (e.g., docs/checkpoints/CP-PRE-PIVOT-<timestamp>.md) on its own branch; commit or stash WIP **without altering live branch by force**, keep WIP branches.
C. Ask user to merge draft PR "Evidence-Escrow Swarm competition pivot" into repl-claw-dev via GitHub UI **after** old agents checkpoint, then pull updated repl-claw-dev in new orchestrator's session. If PR reports conflicts, compare and reconcile manually; no --force push or resets. This docs PR deliberately contains no changes under src/ or tests/.
D. Start ONE fresh RepliClaw Orchestrator in VS Code Autopilot with SEED_PROMPT.md or SEED_PROMPT_V2.md. Do not start new builders until the orchestrator reconciles feature worktrees and migration plan.
E. Inspect git branches, worktrees, WIP handoffs, HEAD and currently running sessions; integrate independent verified useful work, do not cherry-pick duplicate or incompatible changes blindly. Update EXECUTION_STATE.md with actual observations.
F. Reassign tasks under IMPLEMENTATION_PLAN.md P0–P12; use reviewers and checkpoints; never mark test gates PASS unless commands executed and captured.
G. After switch, append a post-migration checkpoint linking old tasks → salvaged/new tasks, show users what works and what remains.

## Pause prompt (paste into **existing old orchestrator**)
> URGENT STRATEGY CHECKPOINT — do not start any new tasks. A new research program is being prepared on branch strategy/evidence-escrow-swarm-20261008. Safely finish/interrupt at command boundary; ask every active worker to checkpoint **its own feature branch/worktree** (commit or safe stash). Record current branch/commit, modified paths, tests actually run, worktree and agent-session IDs, work in progress, dependencies, API costs, blockers, salvage recommendations, and next commands in an append-only docs/checkpoints/CP-PRE-PIVOT-*.md. Do not merge, force reset, delete worktrees, overwrite shared plan/state or declare completion. Report the checkpoint locations; then PAUSE and wait for a new orchestrator seed.

## Work already useful (preserve unless failing gate)
Old F00 → keep G0 baseline.
Old F01 → true open-debate and vote baseline are mandatory comparators in v2.
Old F02 → machine-executed evidence/provenance is mandatory for the SimpleAudit intervention adapter.
Old F03 → held-out evaluation, denominators, budgets and paired metrics remain essential.
Old F04 → actual ScienceClaw NeedItem/ArtifactReactor dispatch remains needed, now must support autonomous agent-selected test proposals.
Old F05 → independent scientific-case feasibility remains useful; prefer Hans slide 8 AI failure attribution with frozen SimpleAudit experiments; do not throw away an already reproducible secondary science case.
Old F06/F07 → decentralized leases and commit-before-peer visibility remain central, but contracts need richer prediction packets + evidence chronology.
Old F08/F09/F10 → remain scientific comparison, external-collaboration evidence, end-to-end demo and public release.
Agents should submit a *mapping* from working files/commits to new tickets, not rewrite work wholesale.

## Non-negotiable race/integration rules
- One orchestrator and one writer of shared EXECUTION_STATE.md on the integration branch.
- Each editing worker has disjoint owned paths and independent branch/worktree. Read-only judges never change author files.
- Do not concurrently edit root AGENTS.md / TASK_SPEC.md / SEED_PROMPT.md / IMPLEMENTATION_PLAN.md during migration.
- GitHub connector sees pushed commits, **not** local uncommitted agent work; mark anything unobserved UNKNOWN.
- No git reset --hard, git clean -fd, force push, or worktree removal during migration.
- Never send secrets into prompts/PR comments; cap costly live experiments.
- If old work includes code changes based on v1 contracts, integrate via tests and review, not by mechanically assuming v2 APIs.
- No claim that this PR automatically pauses active VS Code sessions; human must pause them in UI.

## What to inspect / what to show the user
Before: git worktree list; git status --short; git branch -vv; git log -n 8 --oneline; lists of agent sessions; last executed test evidence.
After: new HEAD, migrated work inventory, G0 observed output, reviewed work packages, next highest-priority agent dispatch, expected spend.
