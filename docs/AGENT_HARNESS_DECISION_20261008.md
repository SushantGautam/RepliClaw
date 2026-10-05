# Agent harness reuse decision — source-level review, 2026-10-08
**Status: decision proposal / no runtime migration approved.** Review target: \`repl-claw-dev\` @ \`5cbcca16d8fdebc77c2101d15b0267d857f06004\`, local agent state may be newer. The engineering agent fleet may have unpushed work. Treat the CI figures below as entries in \`EXECUTION_STATE.md\`, not tests run in this review.

## Executive decision
**KEEP the existing Python RepliClaw scientific protocol, SimpleAudit case executor, escrow ledger, need market and comparative scoring. Do not migrate the P08 experiment to Pi or mini-SWE-agent.**
- **Development fleet**: continue existing VS Code/Copilot orchestrator + isolated feature worktrees + independent code/science reviewers. **OPTIONALLY ADD Pi** as a parallel, independent engineering-worker process after a one-ticket PoC; no full fleet restart required. The Pi CLI/SDK are for coding, not automatic scientific novelty.
- **Scientific task execution**: keep current thin OpenAI-compatible LLMClient as the **frozen P08** comparison runtime. For a follow-up research upgrade **SPIKE PydanticAI** (Python structured outputs/tool calling/usage limits and OpenAI-compatible provider) behind a small investigator-runner interface. Do not import it into the current prereg arms without explicit post-hoc amendment, all-arm parity and independent science approval.
- **Mini-SWE-agent**: a good lightweight Python shell-coding **comparator or one-ticket worker**, not the primary scientific harness for SimpleAudit. Its default shell-only, linear history loop is useful for benchmark transparency and repository repair but poorly matched to role-specific, typed, independently gated interventions.
- **beita6969/ScienceClaw**: a different project built on OpenClaw with typed workflow and replay-verified Skill–Operator evolution. Potential reuse as a science execution backend, NOT this project's execution framework and not equivalent to decentralized research. Integration must pass cost, API and provenance tests first.
- **Do not fork Pi / mini-SWE / SimpleAudit / ScienceClaw** just to claim framework ownership. RepliClaw's candidate contribution is independently committed predictions + execution-verified counterfactual AI-failure diagnosis + local evidence-driven decisions + controlled empirical evaluation. Harness attribution strengthens the claim.

## What actually implements an agent right now
1. \`src/repliclaw/investigators.py\`: \`LLMClient.chat\` calls \`openai.OpenAI(...).chat.completions.create(model, messages, max_tokens, temperature)\`. \`LLMInvestigator.run\` makes a \`chat_json\` request. There is no general model→tool-call→observation→model recursion; no per-call reasoning_effort config; default 4096 completion tokens and 0.2 temperature. In this layer an investigator is **a constrained JSON inference call**, not a software-executing AI coding agent.
2. \`src/repliclaw/eess_live/orchestrator.py\`: three named agents \`alpha, beta, gamma\`, agent hypotheses from \`HYP_BY_AGENT\` and prescribed \`ARM_BY_HYP\` mappings; COMMIT prompts call LLMs, \`NeedWorker\` selects via per-agent \`LocalEigPolicy\` / \`RandomPolicy\` on verified evidence, real P02 runs execute, RESOLVE prompts call LLMs. The outer agent loop iterates sequentially over \`AGENT_IDS\`, not simultaneously running independent long-lived LLM tool loops. It proves a controlled protocol prototype, not yet fully open-ended autonomous scientists. Distinct agent IDs alone are not asynchronous autonomy.
3. \`src/repliclaw/needmarket/policy.py\`: local, reproducible \`gain/cost + λ*diversity − μ*crowding\` ranking, with mapping supplied by evidence-derivation code. This is deterministic autonomous **policy choice** but not an LLM-generated open-ended experiment design.
4. \`src/repliclaw/scienceclaw_adapter.py\` and \`deps/scienceclaw\`: local reuse of Artifacts/NeedItem and ScienceClaw primitives distinct from \`beita6969/ScienceClaw\`. Do not assume those two unrelated repositories can be drop-in exchanged.
5. **Engineering agents** live in VS Code/Copilot, configured by \`.github/agents/\` and the workspace seed; these are NOT the measured scientific agents. Unpushed VS Code sessions cannot be seen through GitHub.

## Reuse matrix
| Harness | Evidence (primary source) | Advantage for RepliClaw | Cost/weakness | Decision |
|---|---|---|---|---|
| Existing Python thin client | repo investigators.py, eess_live, escrow/needmarket, P08 prereg | Smallest frozen dependency, existing replay/tests, same API and budget accounting | No generic multi-turn tools; fixed hypotheses/slots; no per-role thinking controls yet | **KEEP P08; document limitations** |
| **Pi** (earendil-works/pi) | README; packages/coding-agent/docs/cli.md, sdk.md, models.md, extensions.md; MIT LICENSE | Full LLM tool loop; CLI/JSON/RPC/TS SDK; custom OpenAI-compatible endpoints, models.json, \`--thinking off/minimal/low/medium/high/xhigh/max\`; extensions & session tracing; easy independent CLI workers in worktrees | TypeScript/Node 22.19+, no built-in subagent orchestration by default, Pi shell tools need permissions/cwd boundaries, JS<->Python bridge and divergent benchmark accounting; a wrapper does not create scientific decentralization | **OPTIONAL engineering worker**, not main P08 runtime |
| **mini-SWE-agent** | SWE-agent/mini-swe-agent README; src/minisweagent/agents/default.py, models/litellm_model.py | Very small Python model→single shell tool→observation loop; LiteLLM routing and \`model_kwargs\` supporting \`reasoning_effort\`; saved linear trajectory, step/cost/wall limits | Shell acts as broad untyped capability; default is repo-repair/coding not constrained causal scientific actions; model/provider support depends on LiteLLM; not a decentralized fleet by itself | **OPTIONAL coding worker or baseline only** |
| **PydanticAI** | pydantic/pydantic-ai docs/models/openai.md and docs/agent.md | Python native, typed tool calls/output, model-provider setup, usage limits; fits existing Pydantic/domain tools and SimpleAudit allowlist | Fresh dependency/adaptation, hidden behavior change to causal treatment, extra provider differences and context history | **NEXT SCIENTIFIC HARNESS SPIKE**, only *after* P08 freeze |
| **OpenAI Agents SDK** | openai/openai-agents-python docs/running_agents.md, docs/models/index.md | Python-native Runner loops, tools, handoffs, tracing, custom model providers | Handoffs/coordinator might confound independent local-choice experimental treatment, additional tracing/provider configuration; not automatically a decentralized collective | Viable alternative, defer until spike comparison |
| **beita6969 ScienceClaw** | github.com/beita6969/ScienceClaw README and packages/scienceclaw/docs/DESIGN.md | Real typed workflows, clean replay, skills/operators, scientific validators | Different OpenClaw/Skill–Operator platform and research objective, dependencies/tool weights; adaptation cost and licensing to inspect | Reuse **targeted primitives only after measured PoC** |

## Candidate scientific architecture AFTER frozen P08 (NOT part of current live comparisons)
\`\`\`text
Independent scientific agent [PydanticAI/other proven tool loop]
  local context gate / private hypothesis belief
  -> typed propose_hypothesis / propose_intervention / claim_need / submit_forecast tools
      -> RepliClaw escrow + atomic decentralized need marketplace (owned research protocol)
         -> allowlisted SimpleAudit counterfactual executor (machine-verified)
            -> public-only evidence map / hidden oracle separately
            -> local next-action choice and independent scientific report
\`\`\`
Agent harness should be **replaceable** by adapter; different harness implementations may be secondary robustness studies. Mechanism comparisons S0/S3/S4/S5 MUST use **the same base model + thinking settings + tools + evaluator + constraints within a preregistered experiment**. No secret tool affordances or unmatched free model calls.

## Thinking-effort and base model: separate two planes
**Engineering fleet (not measured)**: permitted to optimize route by role, e.g. cheap/low thinking for lint and file scanning, medium for standard implementation, high for integration, xhigh only for skeptical scientific and architectural analysis. Prefer one stable OpenAI-compatible gateway/credential per provider, model aliases, explicit per-worker effort. Model-specific support must be probed. Record provider, effective model, effort, max tokens, temperature, usage/cost and retries. A cheaper first pass with escalation on failure can save tokens if reliability validated.
**Scientific experimental arms (measured)**: same **pinned** model and effective reasoning setting across S3/S4/S5 and ablations, same number of allowed model/tool turns and comparable concurrency. Pin at arm-design time and record full raw request settings; changing effort is a new experimental factor. Never use a high-reasoning EESS vs low-reasoning central manager to claim collective gain. Do not move source code or alter active prereg before independent approval.

## Pi engineering-worker feasibility PoC (isolated, *no code migration*)
- Install per official https://github.com/earendil-works/pi and use same gateway as existing scientific client if endpoint is compatible.
- Configure *local* \`~/.pi/agent/models.json\` (NOT committed secrets) using \`api:"openai-completions"\` and \`apiKey:"$REPLICLAW_LLM_API_KEY"\` (variable must exist in shell), model ID actually returned by gateway, provider-verified context/output limits.
- Commands \`pi --provider repliclaw-gateway --model <actual-id> --thinking medium --print "...\`; \`pi --thinking high ...\` etc. \`--thinking\` is clamped to model/provider support.
- Independent workers in isolated git worktrees, e.g. one Pi process builds a noncritical documentation/fixture task and another reviews changes. Pi does not bundle multiagent fleet scheduling; our VS Code orchestrator remains sole integrator. Benchmark: setup time, actual passing red/green tests, unit task outcome, real token cost, error/recovery rate. Reject if worse than VS Code direct agent for this one task.
- Never configure \`pi\` or coding tools as the **science result generator** without explicit typed/restricted tool wrapper and source attribution. Shell executing arbitrary code can access oracle paths unless OS/process permissions or tool wrappers actually block it.

## Novelty claim / release integrity
No component of "LLM plus tools", multi-agent loops, skill execution, clean replay, science tooling, or harness choice is inherently novel in 2026. Reuse frameworks transparently and cite dependency versions. Scientific claim targets **mechanistic effect** of escrow, independent pre-outcome causal prediction, and evidence-driven decentralized experiment selection on real validated AI failure investigations **relative to strong baselines**. If experiments don't demonstrate it, report boundary conditions rather than pretending reuse harms originality.

## Evidence and source references (reviewed 2026-10-08)
Own repo: https://github.com/SushantGautam/RepliClaw/tree/repl-claw-dev
Pi: https://github.com/earendil-works/pi ; https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/cli.md ; https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/sdk.md ; https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/models.md ; https://github.com/earendil-works/pi/blob/main/LICENSE
Mini: https://github.com/SWE-agent/mini-swe-agent ; https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/agents/default.py ; https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/models/litellm_model.py
PydanticAI: https://github.com/pydantic/pydantic-ai/blob/main/docs/models/openai.md ; https://github.com/pydantic/pydantic-ai/blob/main/docs/agent.md
OpenAI Agents: https://github.com/openai/openai-agents-python/blob/main/docs/running_agents.md
Other ScienceClaw: https://github.com/beita6969/ScienceClaw
