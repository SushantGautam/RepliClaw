# Parallel agent fleets + shared gateway / task-specific thinking levels
**Engineering playbook only, Oct 8 2026.** This does not change the frozen scientific P08 model/cost treatment. Read \`docs/AGENT_HARNESS_DECISION_20261008.md\` and \`docs/P08_SCIENCE_VALIDITY_HOTSPOTS.md\`.

## Two distinct systems, two different routing policies
| Plane | Model and thinking policy | Data boundaries |
|---|---|---|
| Engineering fleet (VS Code/Copilot, optional Pi CLI workers) | May switch provider/model and reasoning level **by ticket** for cost/speed; ensure task is reproducibly completed. | One worktree/branch per writer; no agent editing shared documents/state unless integrator; provider keys not committed. |
| **Scientific P08 benchmark** (RepliClaw \`LLMClient\` + EESS arms) | **PIN ONE model/endpoint, max output, temperature, reasoning parameters, tool access and effective costs across comparative arms**. Heterogeneous models/efforts require a new treatment or robustness study. | Commitment secrecy, oracle isolation, independent evidence; no executor running code with access to evaluator-only oracle. |

## Current scientific model adapter — facts
\`src/repliclaw/investigators.py::LLMConfig\` uses \`REPLICLAW_LLM_BASE_URL\`, \`REPLICLAW_LLM_API_KEY\` (or \`CUSTOM_SIMULACHAT_KEY\`), \`REPLICLAW_LLM_MODEL\`, \`REPLICLAW_LLM_MAX_TOKENS\` (default 4096), \`REPLICLAW_LLM_TEMPERATURE\` (default 0.2). \`LLMClient.chat\` passes ONLY model/messages/max_tokens/temperature to \`chat.completions.create\`. **It does not yet expose task-specific thinking, reasoning_effort, enable_thinking or tool calling.** Do not put unsupported environment keys in docs and pretend the runtime uses them.
Future adapter design (post-P08 or prereg-amended): \`LLMRequestProfile(provider, base_url, model, api_kind, reasoning_effort, enable_thinking, temperature, max_completion_tokens, timeout, cost_cap)\` with a single typed \`chat_json\` or \`run_tool_loop\` interface, validated per provider; persist effective raw request settings and true usage. \`enable_thinking\` often needs provider-specific extra payload; do NOT assume OpenAI Chat Completions accepts it as a top-level field. Some reasoning models reject temperature and/or \`max_tokens\`; capability probe first. Evaluate reasoning token counts/retries, because JSON truncation can bias arms. Build feature flags default OFF for any existing P08 scientific calls.

## Concrete engineering fleet allocation
Suggested maximum at first: 1 orchestrator/integrator + 3 **editing** builders on disjoint paths + 2 **read-only independent** judges + optionally 1 reconnaissance researcher and one validator. Scale only if provider throughput, cost, integration bandwidth and machine CPU permit.

| Fleet lane | Suitable default thinking | When escalate | Workflow |
|---|---|---|---|
| Docs, primary-source reconnaissance, link validation | low or medium | complex research contradiction | read-only, report exact URLs/SHAs |
| Small focused test fix or fixture builder | medium | if tests fail twice for nontrivial reason | independent feature worktree; red/green, log |
| Cross-module integration / competing architecture | high | xhigh on deep contradictory design | integrator owns merges and regression |
| Code judge, experimental leak and concurrency reviewer | high | xhigh for race, security, oracle/causal flaw | read-only, skeptical independent report |
| Science judge / benchmark prereg reviewer | xhigh if provider actually supports | use high if xhigh unsupported | read-only, independent of authors |
| Cheap syntax/lint/test triage | off or low | medium if explanation is needed | deterministic tools first (no LLM on clean automated tasks) |

**Rule:** Capability first, then price. One gateway key/provider is *not* necessarily one stable model. Each assignment records \`model_id\`, \`provider\`, \`effective_thinking_level\`, \`API format\`, \`max_output\`, \`context\`, prompt/profile hash, token usage, wall, retries, number of turns and cost. Only cheap->strong escalate on engineering tickets; not arms inside a frozen science A/B.

## Pi CLI — optional independent coding workers
Docs: https://github.com/earendil-works/pi/tree/main/packages/coding-agent/docs ; CLI https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/cli.md ; models https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/models.md .
Requires current Node (22.19+ per upstream). Install from trusted project docs; sandbox or otherwise restrict shell/file access for untrusted repos. By default Pi has NO built-in permission system; it offers tool selection, trust config, process/worktree separation and optional sandbox backends.

1. Configure \`~/.pi/agent/models.json\` privately from \`docs/PI_MODELS_TEMPLATE.json\` (replace placeholder model ID/context/output with actual probed endpoint). NEVER write keys into tracked files. Or choose built-in provider via \`/login\`.
2. For the EXISTING **engineering** fleet, give each Pi process a different *disjoint* worktree and a bounded task. Do NOT replace running VS Code builders or fork a shared integration worktree.
3. Examples (replace actual-model-id):
\`\`\`bash
# Optional engineering worker; use from its OWN git worktree directory.
export REPLICLAW_LLM_API_KEY="<load securely outside repo>"
pi --provider repliclaw-gateway --model YOUR_MODEL_ID --thinking medium --print "Implement ONLY your assigned tests. Do not edit state files."
# Read-only skeptical review (not code mutation):
pi --provider repliclaw-gateway --model YOUR_MODEL_ID --thinking high --tools read,grep,find,ls --print "Review the current diff; report blockers with file:line and tests."
# Different task gets different inference effort with SAME provider/base model:
pi --provider repliclaw-gateway --model YOUR_MODEL_ID --thinking low --tools read,grep,find,ls --print "Summarize this test log."
\`\`\`
Pi's \`--thinking\` choices are off/minimal/low/medium/high/xhigh/max **clamped to supported levels**. Actual provider mapping must be verified; an OpenAI-compatible gateway might ignore \`reasoning_effort\` or require model-specific parameters. For Qwen-family providers, \`enable_thinking\` may be a provider-specific body option, not Pi's universal switch; test explicit request/response traces before relying on it. Never send full API key in terminal transcripts.

### Worktree recipe (manual, run only if new worker is truly needed)
\`\`\`bash
git fetch origin
git status --short
git worktree list
# Example: choose UNIQUE name/path, don't reuse one owned by active worker:
git worktree add -b fleet/pi-doc-audit .worktrees/pi-doc-audit origin/repl-claw-dev
cd .worktrees/pi-doc-audit
# Start pi --model ... --thinking ... --print "Assigned task, exact paths and acceptance tests"
# After tests, commit on this feature branch and hand commit SHA to orchestrator;
# do NOT merge or push to repl-claw-dev from a builder.
\`\`\`
For true parallelism spawn independent processes/sessions yourself (terminal tabs/tmux/VS Code Sessions). Pi's minimal agent does not automatically create a 5-worker science team. Respect upstream process/resource scheduling, API rate limits and isolated agent filesystem permissions. Watch total GPU/API concurrency and total billed tokens.

## Mini-SWE-agent — simplest Python shell-loop alternative
Docs: https://github.com/SWE-agent/mini-swe-agent ; source \`src/minisweagent/agents/default.py\`, \`models/litellm_model.py\`. A \`DefaultAgent\` loops model→bash tool→observation, records linear messages and limits on calls/cost/wall. LiteLLM \`model_kwargs\` can pass provider-specific fields, e.g. \`reasoning_effort\` when actually supported. This makes it good for reproducible independent coding-worker A/B tests but not the preferred EESS scientific tool-loop. If adopted in a future experiment, use strict shell/FS allowlists and same base model/thinking across comparator arms.

## Python scientific agent spike: recommendation after P08
Use **PydanticAI** as the leading candidate because the existing engine and SimpleAudit are Python, with Pydantic models already in \`pyproject.toml\`. Run it in a **separate feature branch** via adapter \`ScientificInvestigatorBackend\`, not by editing all old protocols. Define typed actions \`inspect_case\`, \`propose_hypothesis\`, \`commit_prediction\`, \`claim_need\`, \`execute_allowlisted_intervention\`, \`publish_evidence\`, \`request_replication\`, \`finalize_verdict\`. Ensure typed argument validation and phase gate; no broad shell access to sealed truth. Evaluate PydanticAI vs existing one-shot JSON client on the **same three case fixtures under the same capped model and tools**. Keep backend ONLY if real evidence of better task performance/reuse against latency/engineering overhead.
Potential alternative: OpenAI Agents SDK \`Agent+Runner\` with tools and tracing; avoid handoff managers in a test intended to prove agent-local autonomy.

## Parallelism doesn't equal novelty
Engineering fleet count is not ScienceClaw competition proof. Scientific decentralization must show actual independently owned experiment choice, distinct capabilities, asynchronous/independent tool execution where claimed, verifiable cross-agent evidence use and measured gain vs matched central adaptive manager. NEVER accidentally let a framework's built-in supervisor choose scientific work while labeling result decentralized.

## Rollback / when to STOP an agent
**Do not stop current P08 builders/reviewers just to add Pi.** The code they built is nontrivial. STEER the current orchestrator via \`docs/STEER_ACTIVE_ORCHESTRATOR.md\`. Pause **bulk live scientific runs** until the P08 science-judge gates pass; existing authorized small token-floor measurement can continue if within its previously recorded cap. Stop/restart only a crashed/misbehaving worker after checkpointing its branch, worktree, status, test log and current process. If a worker is truly stuck, first ask it to checkpoint at a command boundary and then use VS Code Stop / Ctrl+C for that **specific** process (not \`kill -9\` of the fleet). Resume from a saved cursor.

## Scientific impact / credit
The hackathon judges a measured collective scientific result, not the origin of your code editor agent. Reusing Pi/miniswe/PydanticAI with proper attribution is usually a stronger engineering choice than inventing a new model loop; it does not remove novelty from RepliClaw's **protocol-level tested contribution**. Disclose all dependencies, model settings, budgets and what remained custom.
