# RepliClaw fleet — worker contracts
Wave A (2026-10-08). Each worker gets one ticket file (F01–F05.md). The orchestrator (main session on `repl-claw-dev`) owns all shared state files and all integration; workers never touch them.

## Universal ground rules (all workers)
1. **Work only inside your assigned worktree directory** (absolute paths in your ticket) on your assigned branch. Never edit the main tree, `repl-claw-dev`, other worktrees, or the main repo's `.git`.
2. **Use your worktree's venv**: `<worktree>/.venv/bin/python`, `.venv/bin/pytest` (or `python -m pytest`), `.venv/bin/ruff`, `.venv/bin/mypy`. The venv's `repliclaw` install points at YOUR worktree's `src/` — verify with `python -c "import repliclaw; print(repliclaw.__file__)"` before coding.
3. **Red test first**: for every defect, write a failing test that reproduces it, confirm it fails for the right reason, then implement, then confirm green.
4. **Never weaken, delete, or skip an existing test.** No `pytest.mark.skip` on previously-passing tests. No fabricated numbers or mocked "success".
5. **Gate before you call it done** (run in your worktree, record exact output in handoff):
   - `.venv/bin/python -m pytest` — full suite, zero failures (baseline: 66 passed).
   - `.venv/bin/ruff check src/repliclaw/ tests/`
   - `.venv/bin/mypy src/repliclaw/`
   - your focused new tests individually.
6. **Commits**: commit on your feature branch with clear messages + trailer `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>`. Do NOT push to origin. Do NOT merge or rebase.
7. **LLM API: FORBIDDEN.** All work must be offline/deterministic or use a local mock client that counts tokens. Live-model runs belong to a later gate (F08) owned by the orchestrator. Never write API keys into code, tests, logs, or commits.
8. **Handoff required**: before finishing, write `<worktree>/docs/fleet/handoff-<TICKET>.md` (commit it) containing: branch, final SHA, files touched, commands run with exit codes, observed behavior (actual output snippets), contract deviations, unresolved issues, integration notes. Your final message must mirror this summary.
9. **Scope discipline**: implement your ticket only. If you discover work belonging to another ticket (F02/F03/F06...), note it in your handoff instead of doing it.
10. **Interfaces**: additive, backward-compatible changes only (new optional fields with defaults, new modules). The five `STRATEGY_RUNNERS` signatures and the benchmark `rows` schema keys must keep working — other tickets are being merged against the same base concurrently.

## Base commit
All worktrees start at `a14fa6766aa3af51e92c8272f8a344fab144569a` (repl-claw-dev). Integrations happen sequentially in the order F01 → F02 → F03 → F05 (F04 is docs-only), so expect the main branch to move after you finish; that is fine — the integrator reconciles.
