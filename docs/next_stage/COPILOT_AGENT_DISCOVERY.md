# UPDATE: Native BYOK model inheritance is now the correct fix

**2026-10-11:** The three worker profiles (`rc-fast`, `rc-implement`, `rc-review`) now omit the optional `model:` and `modelPolicy:` keys. They inherit `sigma2.no/Qwen3.8-27B-Thinking` from the root session under GitHub Copilot CLI's documented behavior. The `infer: true` values remain. **Do not follow the superseded directions below asking for per-worker `modelPolicy: required` or explicit child-model routing.** Restart Copilot, verify the root model, run one read-only native `task` canary, then use `/fleet` and `/tasks` normally. `rc-fast` runs thinking during this compatibility workaround. Root session is explicitly pinned to Sigma2, and runtime model verification is still required.

Source: https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference (custom agent `model`: unset inherits outer model).

---

# Copilot CLI — rc-* custom agents missing from the task tool

**Fix shipped 2026-10-11 (dev):** changed `infer: false` → `infer: true` for **rc-fast, rc-implement, rc-review**. The `rc-orchestrator` remains `infer: false` intentionally: it is explicitly selected via `--agent`. Each agent keeps `modelPolicy: required` and its authored Sigma2 model. This addresses agent eligibility; it does **not** prove local CLI discovery, model registry, or successful dispatch.

## 60-second local discovery checklist — run on the host executing Copilot CLI

```bash
# Run from the actual RepliClaw checkout on your Copilot CLI host.
cd /absolute/path/to/RepliClaw
git status --short --branch
git fetch origin
git switch dev
git pull --ff-only origin dev
pwd
git rev-parse --show-toplevel
ls -l .github/agents/rc-*.agent.md
grep -H -E '^(name|infer|model|modelPolicy):' .github/agents/rc-*.agent.md
copilot version
printf 'COPILOT_HOME=%s\n' "${COPILOT_HOME:-$HOME/.copilot}"
```

Expected worker frontmatter: `infer: true`, `modelPolicy: required`, model `Qwen3.8-27B-Thinking` or `Qwen3.8-27B-NonThinking`. Expected top-level rc-orchestrator: `infer: false`, `modelPolicy: required`. No filename in this directory may be missing. Do not copy profile names to a config variable as a substitute for real agent files.

**Close/restart any old Copilot CLI session** (custom-agent discovery occurs at session startup). From the checkout root, launch:

```bash
copilot --agent rc-orchestrator --model sigma2.no/Qwen3.8-27B-Thinking
```

In the new interactive CLI:

- `/agent`: show registered custom agent definitions (all 4 expected), separate from currently running subagents.
- `/subagents` (alias `/agents`): inspect worker model locks. Required means the selected model must resolve or dispatch should be refused.
- `/tasks`: shows running/completed subagent jobs, **not the registry**; no entries before starting a task is normal.
- Ask the coordinator to invoke the **`task` tool** explicitly with `agent_type: rc-fast` (or the corresponding agent-selection field in the tool's ACTUAL available schema). Do not use `task` as the agent type—that is a built-in task-executor model and may use an unauthorized model. Ask it to return `MODEL_DISPATCH_OK` without changing files, and check session logs/events for agent ID + model/provider.

If `/agent` lists the four, but the `task` tool still doesn't offer them, verify worker `infer: true`, restart, and check your installed CLI version. An agent name displayed in `/agent` is NOT by itself proof that it is available as a subagent, and a completed `/tasks` entry is not proof of its resolved model.

## If Copilot must launch from another working directory

Preferred: launch Copilot while the cwd is the RepliClaw checkout root.

Alternatively, the official CLI supports a trusted project directory:

```bash
copilot --add-dir=/absolute/path/to/RepliClaw \
  --agent rc-orchestrator --model sigma2.no/Qwen3.8-27B-Thinking
```

The `--add-dir` root is trusted configuration: only point it at your own checked-out repo.

Last-resort user-level installation (e.g., if you absolutely must run from other repositories without `--add-dir`):

```bash
COPILOT_AGENT_DIR="${COPILOT_HOME:-$HOME/.copilot}/agents"
mkdir -p "$COPILOT_AGENT_DIR"
cp /absolute/path/to/RepliClaw/.github/agents/rc-*.agent.md "$COPILOT_AGENT_DIR/"
```

**Beware:** user-level custom agents take priority over project profiles. If you later update files on dev, stale user-level copies may override them. Prefer repository scope to avoid drift. Be especially careful not to set `COPILOT_HOME` to an unused empty directory: this also moves the provider-model registry (`providers.json`) and credentials, not just the agent directory. Never copy secrets into Git or markdown.

## Why /fleet alone is NOT a safe model guarantee

GitHub issue [github/copilot-cli#2261](https://github.com/github/copilot-cli/issues/2261) documents `fleet.start()` dispatching built-in `explore` despite custom agents being registered, at least in affected Copilot CLI/SDK versions. **Native /fleet is not an enforceable model whitelist until you personally verify actual child IDs and model endpoints on your installed version.**

Safe steps:
1. Explicit `rc-fast` `task` invocation → see custom agent ID and Sigma2 nonthinking model.
2. Explicit `rc-implement` `task` invocation → see custom agent ID and Sigma2 thinking model.
3. If desired, a harmless isolated `/fleet` canary: verify every child is custom and Qwen. ANY unexpected built-in or provider → stop that fleet and use explicit `task` dispatches for subsequent parallelism.
4. Keep coordinator `--model sigma2.no/Qwen3.8-27B-Thinking` and `modelPolicy: required`. If your local providers registry only names a different provider-qualified model, resolve its EXACT model string via `/model` and update the authored profile IDs before dispatch. Never drop `modelPolicy: required` to make dispatch succeed.

If still missing, capture just these NONSECRET details: `copilot version`, `pwd`, `git rev-parse --show-toplevel`, `git branch --show-current`, `ls .github/agents/rc-*.agent.md`, whether `/agent` lists rc-fast, and whether `/subagents` lists rc-fast. **Do not paste API keys, headers, entire providers.json or authentication tokens.**

## Official references
- https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference#custom-agents-reference
- https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-custom-agents-for-cli
- https://github.com/github/copilot-cli/issues/2261 (fleet custom routing issue)

This page is a **configuration and model-dispatch preflight**, not experimental evidence. The fast-finish research target does not change.
