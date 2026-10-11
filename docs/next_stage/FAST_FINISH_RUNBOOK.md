# Stage 2 fast-finish runbook — one result, no sideways expansion

**Status:** executable instructions as of 2026-10-11. No fresh campaign has been run by this document. **Default branch `main` untouched; sprint runs on `dev`.** Existing roadmap remains archival context; this file takes precedence for active fleet scheduling and never alters preregistered science.

## Outcome and definition of DONE

Deliver a **verifiable new result**: D-E (escrow + decentralized selection) vs intervention-matched C-EQ central manager across **independent heldout cases**. Both have the same executable intervention set, access permissions, input/label isolation, resource ceilings and causal evaluation. Each case has independently assessed ground truth; seeds are nested within cases. Report actual correct diagnosis, uncertainty, measured resource cost, failures, and unfavorable/null effects. Independently reviewed. The paper claim should be only what the artifacts justify. No "more agents" or algorithmic novelty claim absent evidence.

Main source: `src/repliclaw/experiments/v3/ceq.py` already exists; prior P08 campaign ran 120 live rollouts of ONE case with unequal intervention access between full and central; do not repeat that mistaken comparison. Existing RCAEval 42-case candidate and AgentRx adapter are **observational**; they cannot be substituted for an executable causal setting.

## Three workers, one coordinator

| Task | Priority | Owner/model | Timebox for first verifiable outcome | Exit evidence |
|---|---|---|---|---|
| FF-01 | P0 | `rc-fast` nonthinking | 20 min | fresh install deps/CI patch + exact `python -m pytest tests` output, CI confirmation when available |
| FF-02 | P0 | `rc-implement` thinking | 30 min | label-isolation tests, opaque ID and service-ordinal elimination or documented blocker |
| FF-03 | P0 | `rc-review` thinking | 20 min after FF-02 | statistical null-model correction + one independent contamination canary and verdict |
| FF-04 | P1 | free worker after P0 | 45 min feasibility | same real intervention executor/action manifest for both strategies; exact matched-case parity test |
| FF-05 | P1 | free worker after FF-04 | 30 min | 2–4 truly distinct controlled-case pilot, successful executable paired runs, recorded budgets, no final inference |
| FF-06 | P1 | orchestrator + review | after pilot | prospective holdout manifest, realistic power, frozen version and science approval |
| FF-07 | P1 | orchestrator + free worker | **only after FF-06 approvals** | completed case-level heldout + independent scorer + negative-inclusive report |

**These are steering targets, not guaranteed wall-clock completions.** If a prerequisite is blocked: immediately use the next step that *still leads to the same primary result*. No parallel extra dataset work. Any worker idle because dependencies are blocked should stop consuming model calls.

### Critical discovery constraint

AIOpsLab is the desired external executable context but currently not deployed; **timebox a feasibility check to 45 minutes** using its already-documented pinned local kind problem cases. If deployment needs unapproved VM/cloud compute, stop and mark `EXTERNAL_ENV_BLOCKED`; do not invest hours in infrastructure. The fallthrough is a transparent **internal controlled-case multi-case pilot**, explicitly labeled as not external validation. Do not confuse RCAEval's recorded telemetry with experimental interventions. Avoid promising a journal-strength external causal result on a fallback synthetic environment.

### Protocol constraints

- Primary arms: **D-E and C-EQ only**; optional D-N/D-R *after* primary succeeds and capacity remains. Matched *maximum budget* does not mean equal token spend; publish both. Reviewer chooses the strongest fair C-EQ, not a stripped-down S3.
- Pilot first on a bounded diverse subset (2–4 or 6 independent cases depending availability; 2 seeds/case); prioritize at least two fault families and avoid one-case duplicates. Pilot samples never go in confirmatory heldout. Calculate empirical feasibility/variance/contamination risk and record zero/abstain failures.
- Heldout sample size is **not fixed at 24** until prospective power is recomputed with pilot observations and resources approved. Existing MC guidance of N=24, k=4, MDE=.20 is **simulation-only** and includes a flawed null interpretation for forced one-arm saturation. Do not mistake 24×4×2 rollouts (192) for 192 independent cases.
- Correct Monte Carlo null generation: to assess type-I under H0 for a paired comparison, model *equal arm probabilities conditional on each case*, with ceiling cases set symmetrically. An arm-only ceiling changes treatment effect and may be an estimand/selection issue, but its significant contrast is **not by itself type-I error**. Change frozen rules only by prospective amendment and independent reviewer signoff.
- Root-cause labels, `root_cause.txt`, `ground_truth`, and any stratum/case ID that decodes to the answer must be inaccessible to the agent tool context. Do not fix merely by renaming the field; test adversarial reverse lookup of public manifest. Data needed only by the scorer stays outside the agent filesystem.
- Existing P08 score statement/commit is immutable. Old G4 two-key signoff requirements remain. Bounded local deterministic smoke does not need an invented full experimental budget. Any new external hosting requires exact human authorization.

## Native Copilot CLI orchestration (verified docs)

Documentation: https://docs.github.com/en/copilot/concepts/agents/copilot-cli/fleet , https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference , https://docs.github.com/en/copilot/reference/hooks-reference . `/fleet` and `--fleet` support parallel execution; `/tasks` permits inspection, termination and drill-in/steering; `task`, `list_agents`, `read_agent`, `write_agent` are agent tools. Subagent `modelPolicy: required` means a missing model fails dispatch instead of falling back. Custom agents normally do NOT get `AGENTS.md` unless `include-custom-instructions: true` (set in our profiles).

Repository files: `.github/agents/rc-*.agent.md` (4 strict Sigma2-only profiles), `.github/hooks/repliclaw-fleet.json`, `scripts/copilot_fleet_watch.py` (small watchdog). Native event hooks fire **only on events**; they do not wake a hung agent after X seconds. `subagentStart` has no agent ID; `postToolUse` has no worker ID, so hook session activity is **not** a per-worker heartbeat. Explicit per-task `beat` is the verifiable signal. `subagentStop` hook allows one corrective continuation if response misses STATUS/ARTIFACT/CHECK, not infinite quality loops.

### Run and monitor

Use an existing CLI setup and check `copilot version`, `/models`, `/subagents` and custom agent availability first. Your Sigma2 provider is on the CLI machine, not in the repo. Local registry expected: provider-qualified session `sigma2.no/Qwen3.8-27B-Thinking`; worker profiles OMIT the optional model key to inherit that exact parent model. Do not use bare-ID per-subagent model overrides until supported by the installed CLI.

From existing local repo/worktree on **dev**:

```bash
# Verify flags and provider registry on this exact host first:
copilot version
copilot --help | grep -E 'fleet|autopilot|model|agent|no-sandbox'
# Interactive is preferable for real-time steering and drill-in:
# Keep COPILOT_HOME unchanged: use the HOME whose Sigma2 providers.json already works.
# Do NOT set COPILOT_HOME to a new directory here.
export COPILOT_SUBAGENT_MAX_CONCURRENT=3
export COPILOT_SUBAGENT_MAX_DEPTH=1
copilot --agent rc-orchestrator --model sigma2.no/Qwen3.8-27B-Thinking \
  --reasoning-effort medium --no-sandbox --allow-all --autopilot \
  --fleet -i "$(cat docs/next_stage/COPILOT_FAST_SEED.md)"
```

**CLI version caveat:** `--fleet` in current docs requires a prompt (`-i` above); flags in Copilot CLI 1.0.95 may differ. Check local `--help` and update *only the launch syntax* if necessary. Interactive: `/tasks` (view/steer/stop), `/subagents` (models) and `/model` (root). **Avoid `/delegate`**: it uses Copilot cloud agent and may not keep Sigma2 BYOK. Do not invoke builtin research/rubber-duck/review subagents because they may default to other models. `--fleet` is a delegation mechanism, not a model whitelist; ensure assigned `rc-*` profiles and verify requests resolved to the correct Sigma2 provider.

Optional dedicated watchdog terminal on the **same host and same working tree**:

```bash
python scripts/copilot_fleet_watch.py watch --loop --every 60
```

Coordinator: `assign FF-01`, worker: `beat FF-01`, worker `done FF-01`, inspect `watch`. Only live Copilot agents can use `write_agent` to steer another agent. A watchdog cannot inject messages by itself; logs must be read by the coordinator or operator. Record files under `.artifacts/copilot-fleet/` (ignored by Git). No secrets/transcript content stored by hooks.

### Native Copilot BYOK subagents — inherited model, not per-worker override

The custom worker profiles intentionally omit `model:` so native `task` and `/fleet` workers inherit the top-level `sigma2.no/Qwen3.8-27B-Thinking` model. This is the **documented** behavior (GitHub Copilot CLI command reference). The existing installed CLI rejects explicit child BYOK model overrides despite listing the model as available; do NOT change architecture, provider registry or `COPILOT_HOME`. The `rc-fast` worker temporarily also runs thinking Qwen, staying within the approved two-model set. Verify one read-only child dispatch, then proceed with up to three parallel native workers; supervise with `/tasks` and `write_agent`. Restore nonthinking for rc-fast only after a tested native model-override fix. Any old `COPILOT_PARALLEL_BYOK_FALLBACK.md` instructions are superseded and **must not** be used as routine operational guidance.

### Steering policy

**T+0:** coordinator assigns FF-01/02, FF-03 only after FF-02 artifact exists if shared paths collide. **Every 2–3 min:** poll `/tasks` and `watch`. If no task heartbeat for >4m, check whether it's executing a legitimate test; otherwise send `write_agent` a specific next command, missing artifact and timebox. If >8m without changed artifact/tests, **narrow or replace worker**; never spawn another agent to research a new subject. On repeated retry errors, cap retries twice and retain evidence. Stop fleet promptly when next step is blocked on human-approved compute or frozen protocol. Keep primary result front and center in `FAST_FINISH_STATUS.md`.

## Deliverable checklist

One command reproducing final benchmark subset; pinned manifests, commits and model/seed/caps; fully separated evaluator/oracle; exact fair D-E vs C-EQ interface; original metric, case-level paired analysis and uncertainty; raw outcomes, costs, failures and limitations; independent gate reviews; no false positives from scientific simulation interpretation; no green local tests masquerading as green remote CI.
