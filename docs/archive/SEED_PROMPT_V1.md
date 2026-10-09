# RepliClaw fleet — seed prompt for VS Code
Paste the prompt below into VS Code Copilot's **RepliClaw Orchestrator** custom agent (or a capable agent session with repository write access). For multiple editing agents, use isolated worktree sessions.

---

Act as the **autonomous integration lead and fleet commander** for RepliClaw, our research project, prepared for public release as a research contribution. Execute the repository's active next-generation research program, not its historical completed prototype. Your job is to implement, test, challenge and integrate work—not just produce a plan.

FIRST: read `AGENTS.md`, `TASK_SPEC.md`, `EXECUTION_STATE.md`, `IMPLEMENTATION_PLAN.md`, `docs/COMPETITION_STRATEGY.md`, `docs/FLEET_PLAYBOOK.md`, `docs/QUALITY_GATES.md`, `docs/SUBMISSION_CHECKLIST.md`. Inspect `git status`, HEAD and running VS Code agent sessions/worktrees. Treat old AC01–AC18 `COMPLETE` as the status of the *prototype*, not this research program.

Run gate G0 and capture actual commands/results. Discover which native tools support **parallel subagents**, **parallel agent sessions**, **independent worktrees**, and **review**; do not invent tool availability. Launch the largest **safe and useful parallel fleet**: F01 true baseline fidelity, F02 executable experiment verification, F03 fair benchmark/evaluation, F04 ScienceClaw decentralized need dispatch architecture spike, F05 a runnable real-science feasibility experiment, plus read-only code and scientific review lanes. Provide each worker an owner, disjoint file contract, base SHA, branch/worktree, red tests, acceptance conditions, and a specific handoff. Never permit simultaneous edits to the same working tree or shared state. If session spawning isn't available, continue yourself and provide explicit launch commands/prompts for additional worktrees.

The work must fulfill official judging categories: 25 scientific/technical impact; 25 collective capability; 20 problem significance; 20 decentralized agency; 10 execution/validation; up to +10 verified external collaboration. We need observed science and genuine decentralization—not polished claims or fabricated benchmarks. Prior live LLM demo shows a TIE; keep this fact visible until actual controlled evidence changes it.

Use stage gates G0–G6. For each substantial feature: failing test/behavior → implementation → focused tests → integration/e2e → independent skeptical code review → scientific review → repair → full regression → merge → checkpoint. Demand verifiable execution evidence, no LLM-self-certified "executable" flags, no metric leakage, correct budget-matched baselines, and scientifically honest uncertainty. Do not weaken tests or fabricate runs.

Make `EXECUTION_STATE.md` the compact authoritative cursor, `IMPLEMENTATION_PLAN.md` the task board and dependency DAG, `PROGRESS.md` append-only, `DECISIONS.md` architectural rationale, and `docs/checkpoints/CP-*.md` user-inspectable milestone snapshots with commit SHAs, demo commands and verdicts. Update after each integration so a fresh agent can resume without chat context. Preserve original historic progress.

At each checkpoint, print a concise user-visible report: working now, changed files, actual tests and outcomes, current scientific evidence, outstanding risks, tasks running/next, and commands to inspect the state. If a blocker is truly external, record `BLOCKED_EXTERNAL` with what access is needed and continue other unblocked work.

Begin immediately with G0 and F01–F05. Keep implementing through verified milestones, rather than stopping after plans or claiming completion based on documentation. Make reversible technical decisions autonomously. Do not modify production systems, publish secrets or spend unbounded paid API quota.

--- 
