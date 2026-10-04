# RepliClaw — Execution State (v2 Evidence-Escrow program)
Last updated: 2026-10-08 (orchestrator, A8 conditions applied + docs merged)
status: WORKING
program: EESS — Evidence-Escrow Scientific Swarm (docs/EVIDENCE_ESCROW_SWARM.md)
branch: repl-claw-dev (run branch)
HEAD: a708523 on repl-claw-dev (p08/executor-parity MERGE — A8 RC-1 executor parity; PUSHED)
current_milestone: P08 LIVE WINDOW (2026-10-10→23) PRE-FLIGHT. ALL 3 NO-GO code blockers GREEN (H1/H5/H7 + H2/A4 @ 80a3f4e) AND **A8 (RC-1) MERGED @ a708523** — code-judge round 2 **MERGE-OK** (d7430df4; BLOCK #1 closed+reproduced). A8 = live S0/S3/S4 on policy_rag_v1 (case-conditional, offline on tox21_ar_agonist) + scorer model/executor parity guard (P1 vetoed only on mixed S5/S4 pre-bootstrap; S0/RQ3 non-vetoing) + honest agent accounting both paths + RC-2/3/4. **MAIN-TREE GATE @ a708523: 225 passed/8 skipped, ruff clean, mypy clean (55 files), preflight ALL 5 GATES PASS, score self-test PASS.** Round-2 science sign-off (A1–A8) + human two-key = HARD GATE for any live run.

## Current cursor
status: WORKING
next: (1) **ROUND-2 SCIENCE-JUDGE SIGN-OFF on A1–A8** (final amendment text + CODE-JUDGE-A8-EXECUTOR-PARITY-20261008.md MERGE-OK + main-tree gate evidence @ a708523) — the last scientific gate before live; (2) **HUMAN two-key authorization** recorded here; (3) pre-flight already substantially satisfied (6-arm FakeLLMClient parity re-run = test_a8_fake_llmclient_parity_all_six_arms + test_a8_six_arm_primary_runset_is_scoreable; live-arm contract suite = preflight gate 5; self-test PASS) — run a final recorded pre-flight pass after sign-off; (4) live campaign 2026-10-10→23. Bulk live run HARD NO-GO until (1)+(2).
A8 design-review conditions (SCIENCE-JUDGE-A8-DESIGN-REVIEW-20261008.md, WITH-CONDITIONS): C1 case-conditional routing (live S0/S3/S4 on policy_rag_v1 only; offline on tox21_ar_agonist — frozen RQ4/P4 preserved) = CODE @ 0a502d4; C2 EP checkable fields split (per-run: model+offline_arm; by-construction: full LLMConfig via shared factory) = TEXT @ A8.2; C3 honest agent accounting on LIVE path (eess_live/arm.py was n_agents=0) = CODE @ 0a502d4; C4 RQ pairing (P1=S5/S4 RQ1; P2=S5/S3 RQ2; S0=RQ3 ablation, reported NOT vetoing) = TEXT @ A8.2 + CODE @ 5393e54 (parity.ok excludes S0); C5 3→6 live arms risk disclosure = TEXT @ A8.1; C6 offline-parity subsumption = TEXT @ A8.4; C7 FakeLLMClient re-run = pre-flight tooling ("fake-v1") = TEXT @ A8.2/GATE.
active_workers (actual IDs — read_agent is authoritative):
  - code-judge A8 executor-parity round 1: **d7430df4** — returned **BLOCK** (reproduced BLOCKER #1: stray `<out>/run` unscoreable run-set). Fix landed @ 247208f.
  - code-judge A8 **RE-REVIEW** @ 247208f: **in flight** (dispatched next)
merged_this_segment:
  - e8bb697: p09/docs-a8 (3 app docs: FACT_CHECK_LIST F30-F32 + F20/F27/F28 refreshed; SUBMISSION_CHECKLIST step 9; DRAFT_ANSWERS) — F31/F32 re-refreshed by orchestrator to final A8 text (uncommitted)
  - (pending) p08/executor-parity @ 5393e54 — awaiting code-judge
envelope_deviation: **RESOLVED AS AMENDMENT A7 @ eeae6cc** — ledger enforces max_agents as CUMULATIVE distinct investigators (budget.py:100); S3 deploys 4 distinct (3+follow-up) so the 3-agent v1.1 cap hard-aborts S3 (BudgetOverflow: 4 > 3, reproduced). A7 fixes the live campaign envelope at 60k/900s/4 for all six arms (C1 hash equality; non-constraining for every arm; token/wall ceilings + 10.8M master ceiling unchanged) and corrects the v1.2 §7 non-change entry. case_loader docstring cites A7. Gate 207/8 + preflight 5/5 @ eeae6cc.
s3_residual: RESOLVED by inspection @ 8a287a9 — S3 runs the full investigator pipeline (same verdict shape); no M1 special handling needed.

## Current gates (executed, real output)
| Tree | SHA | Gate |
|---|---|---|
| **repl-claw-dev (RUN BRANCH)** | **d3beaeb** (f78b119 + contract + PREREG v1.1 + scorer 3f3928b + live-arm merge d0cb054 + arms.py cleanup d3beaeb; erratum d4c6f6b) | **149 passed, 8 skipped**; ruff clean; mypy clean (54 files); `p08.score --self-test` PASS; 5 parity tests pass |
| p08/live-eess (live S5/A1/A3 arms) | 9022138 (1806cd2 + 2 integration commits) | **141 passed, 8 skipped**; ruff clean; mypy clean (53 files); tree clean; MERGED into run branch |
| p07/integration (full stack + S5 arm + N1/N3) | 7ccfbaa | 134 passed, 8 skipped; ruff clean; mypy clean (45 files) |
| p08/s5-arm | 14a485d | 25 comparator tests; merged clean into p07 |
| p06/secondary-case (Tox21) | 859aa4e | green (ruff clean, mypy 22 files) — merged into run branch |
| judge race-repro (N1 pre-fix) | — | anchor inconsistency 2/4 runs with widened latency (reproduced) |
| N1 stress (post-fix) | — | 8 procs × 30 appends × 5 runs, widened window: 5/5 seq 1..240 contiguous, anchor==last, verify_ledger()==[] |

## Judge verdicts (persisted in docs/fleet/reviews/)
- **CODE-JUDGE-P07 (2026-10-08)**: REJECT → all fixed (B1 broker atomic claim via staging+os.link, M2/M3/M4 ledger) → re-review **APPROVE-WITH-CONDITIONS** (N1 anchor-outside-lock MAJOR + N2 + N3) → N1/N2/N3 **closed @ d634e00** (stress-verified).
- **SCIENCE-JUDGE-P07 (2026-10-08)**: CONDITIONAL → B1 (no S5 arm) closed @ 14a485d/7ccfbaa; B2 (no slice) closed @ c570971; B3 (0-token harness) — the deterministic slice IS the offline proof; M2 discriminability, M3 S4 revealed-fix closed; M1/M4/M5 = narrative/prereg-level (handled in v1.1).
- **SCIENCE-JUDGE-PREREG-P08 (2026-10-08)**: **REJECT on readiness (not merit)**. 16 Q answered; 8 blocking items: (1) scorer absent, (2) usage zero-fill, (3) P3 cites excluded A2, (4) S5 cited to non-existent file — live arm must be built OR run re-scoped deterministic, (5) S4 fix not on run branch (NOW ON: f78b119), (6) arms run different tasks (C1), (7) P07 not on run branch (NOW ON: f78b119), (8) runner CLI absent + wrong Tox21 path. **8-item v1.1 re-submission checklist.** Live window CANNOT open until checklist green.

## Fleet (this segment)
| Worker | id | Status | Deliverable |
|---|---|---|---|
| code-judge re-review | 9f3c5294 | DONE | APPROVE-WITH-CONDITIONS (report persisted) |
| slice-tests builder | (completed) | DONE | 7 slice tests + demo @ d634e00 |
| comparators S5 builder | (completed) | DONE | EESSArm + S4 fix @ 14a485d, merged 7ccfbaa |
| science-judge prereg answers | ca89d310 | DONE | REJECT + 16 answers (persisted) |
| **prereg-v11** | b0e95e4 | **DONE** | PREREG-2026-10-v1.1.md (all 16 Q-answers + 8 blockers) @ .worktrees/p08-prereg — MERGED to run branch 9f67db2 (pushed), gate 134/8 clean, orchestrator re-ran all 6 acceptance greps |
| **live-eess-arm** | d250675d | **DEAD → work RECONCILED by orchestrator** | live S5/A1/A3 (judge item 4/C2) @ .worktrees/p08-live @ 9022138 (3 commits over f78b119). Worker handoff committed 1806cd2, then flushed a final divergent batch at 20:32 and exited. Orchestrator reconciled: kept its 642-line orchestrator (judge-item-7 usage hardening intact) + escrow/accounting/budget_calls/fake; restored contract arm.py (work_dir/run-01, prereg keys, 22-key final_verdict) from 1806cd2; deleted deviant arms.py + comparators/arm_registry.py; restored my 7-test contract suite. Gate @ 9022138: **141 passed, 8 skipped; mypy clean (53 files); ruff clean; tree clean**. NOTE: its escrow-seam security tests (PhaseViolation gating, owner-only reveal, foreign-file guard) were lost in the final flush and are worth re-adding in a future pass (low priority). |
| **runner-cli-usage** | e7ac1011-6231 | **ABANDONED (stalled)** | Steered at 20:40 with hard checkpoint; 393 tool calls / 8090s with ZERO files written to p08-runner and no activity for 15+ min → declared dead. Worktree .worktrees/p08-runner left untouched (clean @ f78b119) for forensics. |
| **runner-cli-recovery** | 5d7f572d | RUNNING | Replacement build on FRESH worktree .worktrees/p08-runner2 (p08/runner-cli-2 @ d3beaeb): full §10.1 CLI + case_loader (C1 same-task) + usage-invalidation propagation + D-10 hyperparam pin (λ=μ=0.5, max_cycles=6, TTL=120 via ctor kwargs + --assert-frozen pre-flight assertion). |
## FLEET RECOVERY 2026-10-08 22:10 (compaction event)
All 6 prior background agents lost (session compaction cleared them). Recovery actions:
| worker | fate | recovery |
|---|---|---|
| runner-cli-recovery (5d7f572d) | DIED mid-build | WIP preserved UNCOMMITTED in main tree (case_loader.py, runner.py, managers.py, strategies.py, preflight.sh, tests/test_runner_cli.py). Replacement **runner-cli-finish (3c1bc3f2)** on worktree .worktrees/p08-runner2 (p08/runner-cli-2) — instructed to REUSE the WIP logic (read-only), build on its own base, commit there. I integrate the main-tree WIP afterwards. |
| science-judge-red-flags (6eef2110) | report never landed | **science-judge-redflags2 (a90304fb)** — same spec, writes SCIENCE-JUDGE-HARNESS-RED-FLAGS-20261008.md |
| code-judge-harness (17b9f336) | report never landed | **code-judge-harness2 (dd8bbe25)** — same spec, writes CODE-JUDGE-HARNESS-20261008.md |
| code-judge-live-eess (466e3ae5) | superseded | NOT re-dispatched — its scope is subsumed by code-judge-harness2 (reviews the same live-arm + confound surface); re-dispatch on new findings only. |
| science-judge-prereg-v11 (70515a08) | superseded | NOT re-dispatched — subsumed by redflags2 + the v1.2 amendment doc (1bdc6490) which operationalizes its checklist. |
| NEW | unblocked by R1 | **prereg-v12-amendment (1bdc6490)** — drafts docs/experiments/PREREG-2026-10-v1.2-AMENDMENT.md (corrected P1 rule, P2 check, S3 relabel, A4 prompt amendment, honesty framing, sign-off block). Docs-only, no commits. |
| NEW | unblocked by floor merge | **floor-tests-port (ddf44a39)** — ports the 18-test offline suite for scripts/measure_live_token_floor.py from 4af1d0d to the current main-tree script. Single-file commit. |
| NEW | A6 pre-start fix | **random-policy-fix (ee467dab)** — worktree .worktrees/p08-random-policy (p08/random-policy @ f2657d1): single-RNG-draw fix + selection-order byte-identity proof (amendment A6 test 3). |
| NEW | A6 pre-start fix | **leak-guard-canary (3c2177bc)** — worktree .worktrees/p08-leak-guard (p08/leak-guard @ f2657d1): canary no-oracle-leak tests + reference_truth fallback removal (amendment A6 test 1). |

Model allocation (actual support): this VS Code task tool exposes NO per-worker thinking-level parameter; model override IS supported (enum incl. `sigma2.no-NonThinking/Qwen3.8-27B`). Recorded as effective config: all 5 recovery workers on default reasoning model (tasks are integration-grade: amendment text, adjudication, recovery build). Non-thinking variant reserved for the next mechanical dispatch (docs/fixtures/lint).

| **science-judge-prereg-v11 (lost)** | 70515a08 | **LOST @ compaction** | Superseded by redflags2 (a90304fb) + v1.2 amendment (1bdc6490). Report never landed. |
| **p09-draft-rerun** | bf65a0fc | RUNNING | Rework docs/application/*.md on current verified state (live arm exists+tested, scorer self-test, offline campaign runnable, live pending two-key; prior-art = AutoScientists/Co-Scientist/Robin/AgentRx). No commits; orchestrator reviews + commits. |
| **oracle-scorer** | 8f4d284 | **DONE (orchestrator direct build)** | 3 subagent turns died on model API errors → built directly: repliclaw.p08.score @ .worktrees/p08-scorer, 8 tests incl. oracle-gate safety proof + exact-number metrics + bootstrap determinism + voided-run denominator. MERGED @ 3f3928b; gate 142/8 + ruff + mypy + SELF-TEST PASS. **Judge checklist item 1 SATISFIED** |
| **code-judge-live-eess** | 466e3ae5 | RUNNING (read-only) | Independent Code Judge on p08/live-eess @ 9022138 (escrow seam, budget integrity, A3 determinism, offline parity, test adequacy). Report → docs/fleet/reviews/CODE-JUDGE-P08-LIVE.md. |
| **token-floor-measure** | 1670f65f | RUNNING | `scripts/measure_live_token_floor.py` + real-key live S5 floor run @ .worktrees/p08-tokenfloor (p08/token-floor). **AUTHORIZED the live key** (judge item 2/F). Artifact artifacts/p08/live_token_floor/floor.json. |

Workers FORBIDDEN live LLM keys EXCEPT token-floor-measure (single authorized measurement, <25k tokens). Shared interface: docs/experiments/P08-ARTIFACT-CONTRACT.md (frozen v1).

## Branch/worktree map
- **repl-claw-dev @ f45fe16 PUSHED** (run branch = full P02-P08 stack + docs + contract + PREREG v1.1 + scorer + live arm + C1 parity artifact + token floor + P09 docs; **tree currently DIRTY: runner worker is writing src/ files into the main tree mid-run — gate only at commit boundaries**)
- **p08/token-floor @ 4af1d0d** — superseded by the parallel session's 6-cycle measurement (main tree c523329); kept as documented alternative (2-cycle + 3× labeled estimate + 18 offline tests). NOT merged (its artifacts conflict with the 6-cycle version; primary = 6-cycle).

## SCIENCE RED FLAGS (2026-10-08, docs/P08_SCIENCE_VALIDITY_HOTSPOTS.md — all 7 VERIFIED in source by orchestrator)
- **R1 (BLOCKER — ORCHESTRATOR-CONFIRMED NUMERICALLY):** P1 decision rule sign-reversed AND comparator-mismatched — PREREG §2/§8.1 lines 34/194/211: "S5 succeeds iff CI upper(S5−S3 on M1) < 0". Verified: rule fires **only** when S5 LOSES (S5−S3 ub=−0.25 → fires; S5−S3 ub=+0.35 → not). Comparator: rule uses S3, hypothesis claims S4. **NO live run until a versioned amendment (v1.2) with corrected estimand/polarity is judge-approved.**
- **R2 (BLOCKER):** post-evidence verdict prompt (orchestrator.py ~443-451) contains NO actual evidence — LLM verdicts are not causally informed by data. Amendment-triggering fix + parity rerun required.
- **R3:** autonomy framing overstated (fixed HYP_BY_AGENT/ARM_BY_HYP menu + sequential cycles) → must be labeled "local decentralized selection over a frozen preregistered menu".
- **R4:** S3 = incumbent RepliClaw protocol (managers.py:56 strategy="repl_claw"), not neutral central manager → confound; relabel per prior judge.
- **R5:** reference_truth fallback in arm (managers.py:192) → possible oracle path into reported verdicts; need no-leak negative test.
- **R6:** LLM client sends no reasoning_effort (known) → run_metadata must record EFFECTIVE treatment, never overclaim.
- **R7:** RandomPolicy double RNG draw (policy.py:167-168) → trace mislabel; one-line fix, selection-neutral.
- **NO BULK LIVE RUN** until: R1 amendment approved + R2 fix + R5 guard + independent science approval + human authorization.
- Adjudication in flight: science-judge-red-flags (6eef2110) + code-judge-harness (17b9f336), reports → docs/fleet/reviews/SCIENCE-JUDGE-HARNESS-RED-FLAGS-20261008.md / CODE-JUDGE-HARNESS-20261008.md.
- **v1.2 amendment DRAFT committed @ 6eeaaea** (docs/experiments/PREREG-2026-10-v1.2-AMENDMENT.md): corrected P1 string (S5−S4, CI lower bound ≥ 0, 20-run final, 10-run interim = directional-only screen) byte-identical ×3; P2 M11→M6 fix; S3 relabel + confound disclosure; A4 prompt amendment with gates; A5 honesty label; A6 negative-path test list; sign-off block (science judge + human). **Verified: scorer score.py:445-468 still implements the OLD rule — A1.7 scorer alignment is a gated code change, not done.** A5 application-text fixes applied @ f2657d1.

## NO-GO BLOCKER TRACKING (science judge SCIENCE-JUDGE-HARNESS-RED-FLAGS-20261008.md, committed @ a30b77d)
Judge verdict: **NO-GO** for bulk live runs. 7/7 hotspots VERIFIED. Blockers + status:
| Judge item | Amendment | Status |
|---|---|---|
| H1 — P1 rule fix + scorer re-validation | A1 + A1.7 | **MERGED @ 5967f24** (a9779fb): canonical string byte-identical (sha256 766f4eb9…), S5−S4, strict branches, 5 sealed fixtures, no_valid_runs degraded path. Code judge MERGE-OK 9/9 (CODE-JUDGE-SCORER-A17-20261008.md). Gate 207/8 @ 5967f24. Operational note: live runs must use --seed 20261010. |
| H5 — reference_truth leak guard | A6 test 1 | **MERGED** (p08/leak-guard @ ae68211; CLI-level redaction + regression test @ d269a15): two-layer fix (fallback→INCONCLUSIVE, harness+CLI redaction of reference_truth AND seeded_fault) + 10 tests incl. leaky-vs-clean canary. Gate 202/8 @ d269a15. |
| H2 — evidence in verdict prompt | A4 | **MERGED @ 80a3f4e** (p08/prompt-evidence @ 13c9500 by worker 6079ec46 + full-prompt-guard hardening @ df311ec): machine-verified evidence view in RESOLVE verdict prompt + `evidence_cited` + oracle-free full-prompt guard; goldens proven pre-branch by independent regeneration from clean dc0e78f worktree. Code judge MERGE-OK 10/10 (CODE-JUDGE-A4-PROMPT-EVIDENCE-20261008.md). Gate 213/8 @ 80a3f4e. |
| Judge sign-off + human two-key | §9 | **SCIENCE-JUDGE v1.2 SIGN-OFF = NOT-APPROVE** (SCIENCE-JUDGE-V12-SIGNOFF-NOT-APPROVE-20261008.md, persisted). New BLOCKING RC-1 (S7/S9): P1 = S5 (live LLM) vs S4 (deterministic, NOT in LIVE_KEYS) = cross-executor comparison the prereg §3.1 `[v1.1: B]` declares "invalid regardless of the statistics"; unregistered + unguarded (score.py:450-455 checks envelope-hash only, not model). Plus RC-2 (S3 docstring relabel), RC-3 (S3 agent undercount via min() clamp + A7 rationale), RC-4 (score.py:462 comment). **A8 amendment (live S4/S0/S3 + scorer model-parity guard) is the next gated step.** |
Non-blocking (report/audit): H3 autonomy framing (A5 applied @ f2657d1), H4 S3 relabel (A3 in amendment), H6 effective treatment (A4/A6 + runner CLI metadata), H7 RandomPolicy (**DONE @ dc0e78f** — stream-preserving fix merged, order-identity proven, no A3 re-pin needed).

**Code-judge residual resolved (2026-10-08):** item 2's "S3 structural defect_class=None → M1=0" concern does NOT hold: S3 (AdaptiveCentralManager, managers.py:46-57) runs the full RepliClawProtocol investigator pipeline with the same diagnosis output shape (defect_class/target_artifact) as the other arms — no special M1 handling needed; the scorer treats all arms uniformly. The judge's item 2 deliverable (exact relabel string) is already in amendment A3.

## Completed this segment (post-compaction recovery)
- floor-tests-port (ddf44a39): tests/test_measure_live_token_floor.py 16 tests, commit cd678e2, full suite green (4 failures = dead-worker WIP tests only).
- random-policy-fix (ee467dab): d38e502 → merged @ dc0e78f (167 passed/8 skipped, ruff+mypy clean on committed tree).
- science-judge-redflags2 (ddf44a39): report committed @ a30b77d; its P1 string adopted as canonical.
- prereg-v12-amendment (a90304fb): drafted → reconciled to judge string @ a30b77d.
- **Effective engineering model:** all 7 active workers run on the orchestrator default (this Copilot SDK session model). No per-worker thinking-level control exists in this VS Code agent interface — the task tool exposes no thinking-effort parameter, so the requested low/medium/high/xhigh split is **NOT claimable**; recorded as unsupported, not faked. (Historical idle workers show `sigma2.no-NonThinking/Qwen3.8-27B` was used when explicitly selected for mechanical tasks.)
- **Scientific arms (frozen, unchanged):** LLMClient sends model="default", base_url=simulachat.sushant.pp.ua/api/v1, temperature=0.2, max_tokens=4096, NO reasoning_effort (R6). This treatment is frozen for all P08 arms; no thinking claim in the application.
- **Pi PoC: NOT RUN** — Pi CLI is not installed on this machine (`which pi` empty). Installing an unfamiliar CLI mid-campaign is not a safe reversible default; the optional PoC is skipped and recorded. Python RepliClaw remains the sole scientific execution runtime (per AGENT_HARNESS_DECISION).
- p07/integration @ 7ccfbaa PUSHED; p08/s5-arm @ 14a485d PUSHED; p06 @ 859aa4e (merged)
- p08/live-eess @ 9022138 MERGED (d0cb054); p08/scorer @ 8f4d284 MERGED (3f3928b); p08-prereg @ b0e95e4 MERGED
- .worktrees/p08-runner (p08/runner-cli @ f78b119, worker in flight) + .worktrees/p08-tokenfloor (p08/token-floor, live-key measurement in flight)
- backup/pre-rebase-20261010: KEEP until final submission
- simpleaudit: editable install from /Users/sushantgautam/Documents/SimpleAudit @ 9783293 (0.3.3) in root + p07 + p08-s5 venvs

## Next actions (critical path to window)
1. Collect token-floor (1670f65f) → verify measured floor.json + gate → merge p08/token-floor into repl-claw-dev → fill PREREG §5.1 with measured floor + re-derived budget/ceiling, commit before two-key start.
2. Collect code-judge-live-eess (466e3ae5) → fix any BLOCKER/MAJOR findings on p08/live-eess → re-merge + re-gate.
3. runner-cli-usage (e7ac1011-6231): collect → verify §10.1 CLI commands execute offline + same-task (case_loader) + usage-invalidation + D-10 hyperparameter pin (λ=μ=0.5, max_cycles=6, TTL=120s wired + pre-flight assertion) → full gate → merge.
4. Re-submit PREREG-2026-10-v1.1.md (erratum d4c6f6b) to science judge ca89d310 for approval.
5. Two-key start: judge approval + HUMAN AUTHORIZATION recorded here before ANY live run. Window 2026-10-10→23, shortenable not extendable.
6. After window: scorer → scorecard (counterevidence-first), application/submission readiness (deadline Oct 16), push everything.

## Environment note (verified)
- Anaconda system python breaks pip build isolation → ALWAYS `.venv/bin/*` inside the worktree. rdkit + simpleaudit installed in root, p07, p08-s5 venvs.
- Gate commands (from INSIDE worktree): `.venv/bin/python -m pytest -o addopts="" -q`, `.venv/bin/ruff check src tests scripts`, `.venv/bin/mypy src`.
- Live LLM key exists in env; fleet workers FORBIDDEN; live runs P08-only under envelope.

## State update contract
Only the orchestrator/integration owner updates this file, after verifying branch/tests. Never mark COMPLETE without G6 + real-science evidence. No fabricated results, novelty, approvals, or success.

## What completion really requires
Real frozen SimpleAudit counterfactual interventions (DONE @ P02/P07); verified pre-outcome independent commitments (DONE @ P03 + slice); unscripted locally selected+claimed experiments (DONE @ P04 + slice choice_trace); final auditable evidence (scorer in flight); matched-budget strong adaptive-manager comparisons (arms+parity DONE offline; live runs gated); science/code reviews (DONE, see verdicts); clean replay (replay.sh pinned); exact official hand-in + human submission (P09, deadline Oct 16).
