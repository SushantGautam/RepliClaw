# STEERING PROMPT for CURRENT RUNNING ORCHESTRATOR — DO NOT FULL-RESTART
Date: 2026-10-08. This prompt is **not a replacement for SEED_PROMPT.md**. It changes P08 review priorities without changing approved scientific treatment. Current remote checkpoint at review time: \`repl-claw-dev\` \`5cbcca16d8fdebc77c2101d15b0267d857f06004\`; your local work is likely newer, inspect it first.

## Paste into EXISTING VS Code/Copilot orchestrator chat
**URGENT READ-ONLY SCIENCE/HARNESS AUDIT — KEEP EXISTING FLEET RUNNING.**
Continue existing P08 workers and preserve every worktree, branch, WIP and in-flight command. This is a steering request, NOT cancellation or a fresh migration. Inspect actual local HEAD, worker sessions, \`EXECUTION_STATE.md\`, the latest prereg and the existing judge reviews. Then read:
- \`docs/AGENT_HARNESS_DECISION_20261008.md\`
- \`docs/P08_SCIENCE_VALIDITY_HOTSPOTS.md\`
- \`docs/FLEET_MODEL_THINKING_AND_REUSE.md\`

If these docs reside in a PR branch not yet merged, read them from \`review/agent-harness-and-validity-20261008\` via git show/fetch; do not merge or reset your active tree mid-task.

**Your critical priority is scientific validity, not switching coding harnesses.** Spawn/assign two **READ-ONLY INDEPENDENT** reviewers (science and code; different contexts/worktrees if actually supported) while existing editing workers continue:
1. **P1 prereg direction/comparator**: §2 says S5 vs S4 escrow benefit, yet literal "S5 succeeds" test uses CI upper(S5−S3) < 0, which means S5 lost to S3 on higher-is-better correctness. Verify sign, comparison, decision labels, logic, interim/final stopping rules. Write a reviewer verdict at exact file:line and test sign with simple controlled numbers. If truly wrong, DO NOT change silently or after seeing live outcomes. Create a versioned prereg amendment for independent judge approval **before** confirmatory runs.
2. **Post-evidence LLM prompt**: inspect \`src/repliclaw/eess_live/orchestrator.py\` post-evidence \`RESOLVE\` prompt. It apparently does not include actual public verified evidence despite saying "evidence has been observed". This may invalidate evidence-based LLM verdict claims. Record actual prompt payloads in safe test; design negative-path tests without leaking sealed oracle. Material prompt change may require an amendment to all-arm comparators.
3. **Genuine scientific autonomy**: HYP_BY_AGENT/ARM_BY_HYP preassign experiment family; NeedWorker uses deterministic policy; scientific workers loop sequentially. Label constrained local-ranking baseline accurately; plan a *small separate later* open-ended hypothesis/tool-call PoC, not a stealth change to P08 arms.
4. **S3 parity/case leakage**: S3 wraps original RepliClawProtocol with commit/reveal and central follow-up, not a neutral equal-intervention central manager. Existing judge advised re-labeling; verify case_loader delivers actual same case, allowed actions and oracle to all arms. Check \`EESSArm._verdict\` fallback \`claim.reference_truth\`; no investigator/scored arm may see evaluator truth.
5. **RandomPolicy trace correctness**: \`utility\` and \`components.rng_draw\` use two different RNG calls. Assign a tiny isolated test/fix if confirmed, but never alter post-start prereg behavior without an amendment.
6. **Model/effort and resource reporting**: existing scientific Python LLM client does not support per-task thinking; DO NOT assume pinned reasoning high across arms. Record actual request settings and usage. Keep P08 research model/treatment frozen. Set per-ticket medium/high/xhigh only on the *engineering* workers using actual harness-supported config; do not claim universal enable_thinking/effort support.

**Harness decision:** No switch to Pi or mini-SWE-agent for P08. Optional **one** new disjoint Pi engineering-worker PoC (do not steal active P08 branch): compare a small test/fixture code task vs current VS Code worker at the same provider/model and record actual time/cost/test outcome. PydanticAI is a future Python typed-tools SCIENTIFIC backend spike after the prereg live campaign; not immediate rewrite.

**Parallelism:** Keep running active runner-CLI, code judge, token-floor. Add read-only science validity reviewer, a read-only Pi-vs-mini integration investigator, and ONLY if nonoverlapping a fresh small test worker. One integration owner. Existing live-key token-floor measurement (previously authorized/strictly capped) may finish, but NO BULK LIVE RUN before both independent science approval AND human authorization. Honor provider API limits; avoid duplicate expensive workers. Code judge must review any behavior-affecting fix and state whether amendment is needed.

**Outputs:** Write \`docs/fleet/reviews/SCIENCE-JUDGE-HARNESS-RED-FLAGS-*.md\`; review notes, exact paths/SHAs and actual test logs. Existing P08 integration checkpoint may continue. Do not report "P08 READY" until prereg sign, evidence visibility, same-case, usage-invalidation, runner commands and tests are verified.

Report at end: current HEAD, list of active worker session IDs/worktree refs (actual), each finding VERIFIED/NOT VERIFIED/ALREADY FIXED, independent gate, whether any PR amendment is needed, and next scientific action. Continue existing assigned work.

## Only when old session becomes unusable
1. Ask it to checkpoint at a command boundary (status, worktrees, commits, tests, experiment keys).
2. Stop that **one** session via VS Code Stop / terminal Ctrl+C; do not kill the entire fleet or remove worktrees.
3. Start new RepliClaw Orchestrator from latest integration branch with root SEED_PROMPT.md **plus** this steering prompt, first reconciling active worker sessions and WIP. Do not use \`git reset --hard\`, \`git clean -fd\`, \`kill -9\` or force pushes as restart primitives.
