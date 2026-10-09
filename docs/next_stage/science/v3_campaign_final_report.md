# RepliClaw Stage 2 — V3 Campaign Final Report (feasibility series)

**Scope:** the V3 telemetry-arm feasibility series (rounds 1, 2, 4, the
V3.3-repair round 5, and the V3.4 envelope-raise round 6) under the SimulaChat
`default` MODEL-SUBSTITUTION. This is a **record-and-hold** report. It reports
**feasibility facts only** — no effect size, no power claim, no
superiority/inferiority statement, and no heldout reuse (frozen
no-confirmatory-reuse clause).

**Verdict (one line):** across five rounds (V3 → V3.1 → V3.2 → V3.3-repair →
V3.4; 60K → 90K → 150K → 150K-with-repair → 300K per-run envelope) and two model
ids, the decentralized arm (D-E-TELEM) completed **0 runs through round 4**; on
the repaired V3.3 instrument (round 5) it completed **exactly 1/9 runs — and
that run executed the full decentralized mechanism end-to-end and was correct**;
on the V3.4 symmetric 300K envelope (round 6) it completed **6/12 ledgered runs,
all 6 correct** — while the centralized control (C-EQ-TELEM) completed every one
of its reached runs (all hits; 0 crashes on V3.3/V3.4). **No measurable
advantage of decentralization, evidence escrow, or adaptive selection over a
same-tools central manager has been demonstrated under the substituted model.**
The refined characterization after round 6: D-E non-completion is
**partially envelope-bound** (the abort class rose with the cap) **with an
envelope-invariant crash class (33%) that is mechanism/model-bound** — and
D-E completions cost ~3.2× (up to 3.8× per-case) the control's tokens, "same
budget" holding at the per-run cap only. It remains a feasibility/negative
record, not an effect estimate.

---

## 1. Question under test

Whether **decentralized scientific agents + evidence escrow + adaptive
experiment selection** produce a measurable benefit over a **central manager
with the same tools, budgets, agent opportunities, information, and evidence
access** (the C-EQ-TELEM control), on the frozen 10-case RCAEval telemetry
pilot.

## 2. Rounds (actual, from ledgers/STOP.json — no rounding)

| Round | Instrument | Model id | D-E-TELEM (of 12; cohort n=20) | C-EQ-TELEM (of 12) | Tokens / ceiling | Stop |
|---|---|---|---|---|---|---|
| 1 | V3 (60K/run, 24 tools) | `default` (Qwen3.8-27B) | 0/6: 4× aborted_budget, 2× crashed | 2/6 completed (both hit=true); 2× aborted; 2× crashed (volume-band) | 663,214 / 2,880,000 | stop-2 |
| 2 | V3.1 (90K/run, 24 tools) | `Borealis2-preview` (same Qwen base class) | 0/6: 6× aborted_budget, **0 protocol violations** | 3/6 completed (all hit=true); 2× aborted; 1× crashed (volume-band) | 713,441 / 2,880,000 | stop-2 |
| 4 | **V3.2 (150K/run, 48 tools, band 1.40)** | `default` (Qwen3.8-27B) | **0/12: 8× aborted_budget, 2× malformed-output, 2× per-tool sub-budget** | **3/8 completed (all hit=true); 5× crashed by the volume canary** | 1,744,526 / 7,200,000 (1,132,481 at stop time) | stop-2 (D-E) [+ stop-1, a defect — see §6] |
| **5** | **V3.3 (150K/run, 48 tools, anti-loop cache, no sub-caps, volume demoted)** | `default` (Qwen3.8-27B) | **1/9 completed (hit=true; full mechanism executed); 4× budget-abort, 4× malformed-output** | **7/7 completed (all hit=true); 0 crashes (2 out-of-band → logged flag)** | 1,264,453 / 7,200,000 (at trip) | stop-2 (D-E 8/20 = 0.40 > 0.25) |
| **6** | **V3.4 (300K/run shared envelope, 12M ceiling; otherwise identical to V3.3)** | `default` (Qwen3.8-27B) | **6/12 completed (ALL hit=true, 121K–283K tok); 4× malformed-output (18–27K, envelope-invariant); 2× budget-abort (277K/300K)** | **9/9 completed (all hit=true, 55–79K); 0 crashes** | 2,389,175 / 12,000,000 | **stop-1 (C-EQ sat 3/10 = 0.30 > 0.25)** — pre-empted a D-E stop-2 that the full cohort (6/20 = 0.30) would have tripped |
| **7** | **V3.5-D (300K/run shared envelope, 12M ceiling; + B forced-JSON, C tolerant discriminant, D unbounded envelope-bounded retry — shared path, both arms)** | `default` (Qwen3.8-27B) | **6/14 completed (ALL hit=true, 232K–295K tok); 0 crash-class crashes; 8× budget-abort (4× token-cap ≥300K + 4× phase-2 tool-cap, D-E-only pre-existing); 2 drift-form terminals RECOVERED by (C)** | **10/10 completed (all hit=true, 49–77K); 0 crashes** | 4,311,893 / 12,000,000 (22-run snapshot at trip; 24 final) | **stop-1 (C-EQ sat) + stop-2 (raw D-E non-compl 6/20 = 0.30 > 0.25)** — the raw stop-2 counts all non-completions; adjudicated crash-class is 0 (see §2d) |
| **8** | **V3.6 (600K/run shared envelope, 24M ceiling; everything else byte-identical to V3.5-D)** | `default` (Qwen3.8-27B) | **9/14 completed (ALL hit=true, 180K–325K tok); 0 crash-class crashes; 0 drift-emissions; 5× budget-abort — 5/5 phase-2 tool-cap (sub-envelope: 216K–363K tok, 84–133s; 0 true token-cap, 0 wall)** | **9/9 completed (all hit=true, 55–72K); 0 crashes** | 4,084,520 / 24,000,000 (18-run snapshot 2,640,155 at trip; 23 final) | **stop-1 (C-EQ sat 3/10 = 0.30 > 0.25 at 18-run snapshot)** — STOP `per_arm_crashes D-E=2` = 2 `aborted_budget` under the /20 full-cohort denominator, **not 2 crashes** (see §2f) |

Round 3 (V3.1, `default`) tripped stop-2 earlier (D-E 0/6) and is the trigger
that produced the V3.2 amendment. All rounds are feasibility-only.

### 2b. Round 5 — V3.3 (the repaired instrument; the pivotal feasibility data)

Round 5 is the first round run on the **repaired instrument** (V3.3: symmetric
anti-loop cache in both arms, per-tool sub-caps removed → total-budget-only, and
the C-EQ volume canary demoted from crashing-gate to logged non-crashing flag).
Two fresh independent pre-run judges (code + science) PASSed the repair, and it
was frozen at commit `520f6859` (hashes verified). Result:

- **D-E-TELEM: 1/9 ledgered runs COMPLETED — and for the first time in the whole
  V3 series the decentralized machinery executed end-to-end.** The completed run
  (P-01 s12, 138,126 tok, **hit=true**, within the 150K envelope) contains
  **phase-1 sealed forecasts AND phase-2 commit-reveal final rankings from all
  three investigators** (inv-a/b/c) in its escrow ledger. The 8 non-completions
  split 4× budget-abort (150,397–154,253 tok — distinct-call non-convergence,
  *not* repeat loops, which the anti-loop cache now makes free) + 4×
  AgentProtocolError (two consecutive malformed action outputs, ~21–22K tok).
- **C-EQ-TELEM: 7/7 completed, all 7 hits, zero crashes** (54,943–71,866 tok).
  Two runs (P-05/P-06 s11) exceeded the 1.40 volume band (1.71/1.74) and were
  **logged `volume_band_violation=true` but NOT crashed** — direct live evidence
  that the demotion works and removes the arm-specific crash instrument.
- **Stop-2** correctly tripped on D-E crash-equiv 8/20 = 0.40 > 0.25 after 16
  ledgered runs; stop-1 (seed-saturation, now computed at case level) correctly
  did NOT trip; spend 1.26M < 7.2M ceiling.

This round changes the *characterization* of the negative, not its direction:
the contrast is now cleanly instanced (the mechanism demonstrably runs and can be
correct), but the decentralized arm still completes only 1/9 of the time under the
substituted model, while the same-tools centralized control completes 7/7 at lower
cost. **No advantage of decentralization/escrow is demonstrated** — the finding is
refined from "the mechanism never executed" to "the mechanism executes but is
model-limited under substitution." See §4b and disclosure 12.

**Throughput-gap characterization (science-judge round-5, mandatory label):** the
C-EQ 7/7 (54–72K tok) vs D-E 1/9 (138K tok) difference is a **feasibility /
throughput observation, NOT a reliability, capability, or "decentralization is
worse" verdict.** It is an **architecture × fixed-envelope** product: D-E's
3-parallel-investigator design issues ~3× the LLM/tool turns and thus hits the
same 150K per-run token envelope at ~2.4× C-EQ's token cost, and this is further
inflated by the substituted model's tool-call verbosity. The **anti-loop cache
asymmetry is in practice pro-D-E, not against D-E**: the cache makes D-E's
identical repeat-calls free (D-E audits show 1–20 free `repeated_cached` calls
per sandbox; C-EQ 0–1), so the cache *helps* D-E; the binding constraint is the
token envelope, not repeats. C-EQ's 7/7 is partly a product of the
preregistered volume-crash demotion (2 of its 7 would have crashed under V3.2) —
a deliberate, disclosed fairness fix, not a C-EQ outcome advantage.

### 2c. Round 6 — V3.4 (the 300K symmetric envelope; the disambiguation round)

Round 6 ran the V3.4 instrument (single symmetric amendment: shared per-run
envelope 150K → 300K via the A1-parity-guarded constant; round ceiling
7.2M → 12M; **nothing else changed** — freeze `v34_prereg_freeze.md` FINAL,
code `6e32153`, 2 fresh pre-run judges PASSed). Preregistered purpose
(anti-post-hoc): disambiguate whether round-5 D-E's 1/9 was
**envelope-bound** (architecture × cap) or **mechanism/model-bound**. Result:

- **D-E-TELEM: 6/12 ledgered runs COMPLETED, and ALL 6 were correct**
  (hit=true; 121,236–282,525 tok, mean 194,742). Per the preregistered A3
  denominator (completions ÷ D-E runs **ledgered**, vs round-5's 1/9), the
  D-E completion rate rose 11% → 50% at double the envelope, with 100%
  accuracy on completions. The 6 non-completions split into **two distinct
  classes**: 4× AgentProtocolError malformed-action crashes (18,445–26,698
  tok, 14–21 s — **envelope-INVARIANT**: byte-identical class to round 5,
  6–9% of the 300K cap) and 2× budget-aborts at 277,097 / 300,732 tok.
  **P-05 is direct counter-evidence to a clean "needs more tokens" reading**:
  it aborted at 152,364 (round 5, 150K cap) and again at 277,097 (round 6,
  300K cap) — ~1.8× more tokens, still no submission → **budget-truncated
  non-convergence**, not a clean budget wall. The 2 aborts are
  non-completions either way and are NOT booked as latent successes.
- **C-EQ-TELEM: 9/9 completed, all 9 hits, zero crashes** (54,759–78,652 tok).
  Per A4 this is a **reproducibility check, not a new reference**: 6 of 9
  per-case counts match round 5 within <0.5%; P-05/P-06 s11 drift +9.4%/+9.5%
  (backend nondeterminism on the substituted model — case_sha256 identical, so
  data-side is clean; round-5 C-EQ@150K 7/7 remains the reference).
- **Stop: stop-1 (C-EQ seed-saturation 3/10 = 0.30 > 0.25) at 16 ledgered
  runs; 21 runs in the final ledger** (5 in-flight runs finished post-trip,
  including 2 D-E completions — P-07 s11 @229,708, P-04 s12 @185,905).
  **Snapshot gap matters**: at the snapshot D-E was 4/9 and its crash-equiv
  was 5/20 = 0.25 (not > 0.25); on the FULL ledger D-E non-completion is
  6/20 = 0.30 > 0.25, which **would have tripped stop-2** — the C-EQ
  saturation stop pre-empted it. The round's terminal state therefore reads
  as a **D-E-favorable transient** (fast crashes land in the snapshot; slow
  completions arrive in flight), not a full-cohort rate. 19 of 40 planned
  runs (P-08 s12 … P-10) never launched.

**Characterization (judge-mandated wording, §4c):** D-E non-completion is
**partially envelope-bound** (the abort class moved with the cap) **with an
envelope-invariant crash class (33%) that is mechanism/model-bound** — not a
single "envelope-bound" story. Disambiguation of genuine budget-need vs
burn-through for the abort class requires a 600K round (not yet authorized).
See §4c and disclosure 13.

### 2d. Round 7 — V3.5-D (the crash-class-targeted instrument repair; instrument-reliability round)

Round 7 ran the V3.5-D instrument (freeze `v35_prereg_freeze.md` amendment v3
@ `9369b5b8` + R2 tool-cap completion @ `8b8bda5`; code `11e7e63a`, instrument
blob `telemetry_arms.py = 1b33c002…`; 2 fresh pre-run judges: code **PASS**,
science **CONDITIONAL PASS** with all R1–R3 + A1–A5 applied). The three coupled
fixes are on the **shared** action-protocol path, **both arms** (A1 parity):
**(B)** forced-JSON `response_format` (secondary output-discipline hardening),
**(C)** tolerant `_OBS_TOOLS`-validated discriminant + mode-aware correction
prompt (the transcript-backed primary fix), **(D)** unbounded
envelope-bounded retry-until-valid so a never-valid model terminates as an
honest `aborted_budget`, **never `crashed`**. Preregistered purpose: measure
whether the repaired instrument lets D-E complete at 300K **without the
round-6 parse-drift crash class**. It is an **instrument-reliability**
measurement, **not** a mechanism experiment (§4d). Result:

- **D-E-TELEM: 6/14 ledgered runs COMPLETED, ALL 6 hit=true** (232,273–295,234
  tok). **0 crash-class crashes** (`status=="crashed"` = 0 across all 24 runs,
  vs 4/12 in round 6). The 8 non-completions are **all `aborted_budget`**,
  splitting into two **orthogonal, pre-existing** classes (neither the crash
  class): **4× token-cap abort** (≥300,000 tok: P-05 s11/s12, P-06 s11, P-07
  s11) + **4× phase-2 tool-cap abort** (sub-envelope 178–275K tok / 57–86
  tool_calls, `DE_PHASE2_TOOL_CAP=4`, `telemetry_arms.py:1041`, **D-E-only,
  pre-existing in V3.4** — P-02 s12, P-04 s11, P-06 s12, P-08 s11).
- **CRITICAL (science-judge round-7 REQUIRED, machine-verified): the
  round-6 crash class is 0, but "0 parse-drift" would be a false statement.**
  Two D-E runs (P-04 s11 / inv-c, P-06 s12 / inv-c) **did emit the
  canonical crash-class drift form as their terminal action**
  (`{"action":"service_metrics", ...}` — the tool name in the `action` field).
  Under **(C)** the tolerant discriminant **recovers** these into a valid
  `tool_call` without raising, so parse_action does not raise, **(D) retry
  never fires**, the run **continues**, and only later aborts on the orthogonal
  phase-2 tool cap. These are therefore **drift-form *emissions recovered by
  (C)* — direct live evidence that (C) works — NOT crashes and NOT fix
  failures.** The defensible, machine-verified headline is **"0 crash-class
  crashes"** (`status=crashed`), **not** "0 parse-drift emissions" (2 were
  emitted, 2 were recovered).
- **C-EQ-TELEM: 10/10 completed, ALL 10 hit=true, 0 crashes** (49,030–77,228
  tok). Under the repaired instrument this is a **same-instrument
  reproducibility check**, not a new reference (round-6 C-EQ 9/9, round-5 7/7
  remain the references).
- **JSON-mode parity (science-judge #5, machine-checkable): SYMMETRIC.** Every
  prompt in every session ran in JSON mode — C-EQ 176/176, D-E 1210/1210,
  **0 plain-mode drops in either arm**. The (B) permissive-fallback parity risk
  never materialized on live `default`.
- **Stop: stop-1 (C-EQ seed-saturation) + stop-2 (raw D-E non-completion) at
  the 22-run snapshot** (4 completed cases). **Snapshot gap:** STOP.json
  records 12 D-E / 10 C-EQ (`runs_recorded=22`); **2 D-E aborts (P-07 s11,
  P-08 s11) landed post-trip under concurrency 6**, giving the final 24-run
  ledger (14 D-E / 10 C-EQ). Token delta reconciles exactly: STOP cumulative
  3,734,441 + (302,152 + 275,300) = **4,311,893** = final 24-run total. 16 of 40
  planned runs (P-08 s12 … P-10) never launched.

**The freeze-mandated dual-count (raw stop-2 vs adjudicated crash-class):**

| Quantity | D-E (of 24-run ledger) | C-EQ | Note |
|---|---|---|---|
| **Raw non-completion (stop-2)** | **8/14 = 0.57** (full-cohort 8/20 = 0.40; snapshot 6/12 = 0.50) | 0/10 | STOP.json `rate 0.3` is the full-cohort /20 at snapshot; STOP does NOT distinguish crash class |
| **Adjudicated crash-class (`status=crashed`)** | **0/14 = 0.00** | 0/10 | **the round-6 class; vs 4/12 = 0.33 in round 6** |
| **… of which assert-commit (pre-existing)** | 0 | 0 | R1 branch; none observed |
| **Drift-form EMISSIONS recovered by (C)** | 2 (P-04 s11/inv-c, P-06 s12/inv-c) | 0 | NOT crashes — recovered, run continued to orthogonal abort |
| **Orthogonal aborts (token + tool-cap)** | 8 (4 token + 4 tool-cap) | 0 | pre-existing classes, NOT the crash class |

**Reading the dual count:** the raw stop-2 number (8 D-E non-completions)
looks like a crash-rate, but adjudication shows **0 are the crash class** —
all 8 are orthogonal budget/tool-cap aborts, and 2 of those additionally
showed a recovered drift emission. The crash class (round-6's 4/12) is
**machine-verified gone (0/14)**. This is a **valid, honest
instrument-reliability result**: the repaired action protocol eliminated the
crash class. It is **NOT** a mechanism benefit for decentralization, and it
does **not** change the standing negative finding (§4d).

### 2e. What round 7 does and does not change

- **Changes (reliability):** the round-6 D-E parse-drift crash class (4/12) is
  **0/14 in round 7** — the instrument repair worked as designed, machine-
  verified, with (C) recovering 2 live drift emissions.
- **Does NOT change (mechanism):** the contrast of interest is unchanged. D-E
  still completes only **6/14** (43%) at **~5× C-EQ's token cost** (241–295K
  vs 49–77K per completion) with **case-level 2/8** (only P-01 and P-03 had
  both seeds complete; P-02 s12 and P-04 s11 aborted), while C-EQ completes
  **10/10** at **case-level 6/6**. The residual D-E
  non-completions are now **orthogonal budget/tool-cap** (envelope-bound and
  D-E-mechanism-bound respectively), **not** the crash class. **No advantage of
  decentralization/escrow is demonstrated**; the finding is refined again (from
  "mechanism executes but is model-limited" to "crash class eliminated, but D-E
  remains completion-limited and ~5× costlier than the same-tools control").

### 2f. Round 8 — V3.6 (the 600K envelope; the budget-need-vs-burn-through disambiguation round)

Round 8 ran the V3.6 instrument (freeze `v36_prereg_freeze.md` @ frozen HEAD
`cff7d748`; exactly **two constants** changed from V3.5-D:
`MAX_TOKENS_PER_RUN` 300K → 600K and `ROUND_TOKEN_CEILING` 12M → 24M, both
A1-parity-guarded and shared by both arms; 4 value-pinned tests updated; 483
passed / 11 skipped / 3 xfailed + ruff/mypy clean at the frozen gate).
**2 fresh pre-run judges: code CONDITIONAL-PASS, science CONDITIONAL-PASS —
all REQUIRED + RECOMMENDED items applied (doc-only).** Human gate cleared
2026-10-11 (option (ii) of §7 at the time): round 8 @600K authorized,
unlimited spend on SimulaChat `default`; **model change NOT authorized.**
Purpose (frozen): disambiguate **H-budget** (D-E's 300K token-cap aborts
reflect a genuine need for more than 300K) vs **H-burn** (the substituted
model burns tokens without converging; more budget buys nothing) — and, by
extension, whether the standing negative finding extends to 600K. Result:

- **D-E-TELEM: 9/14 ledgered runs COMPLETED, ALL 9 hit=true** (180,020–324,901
  tok). **0 crash-class crashes** (`status=="crashed"` = 0; the round-6 class
  stays gone). **0 drift-form emissions** (round 7 had 2, both recovered).
  The 5 non-completions are `aborted_budget`. **Code-judge REQUIRED (machine-
  verified):** all **5/5 are the phase-2 tool-cap class** (sub-envelope:
  215,927 / 258,083 / 270,226 / 328,161 / 362,587 tok, all < 600K; wall
  83.8–132.7s, all ≪ 899). The token-cap gate (`telemetry_arms.py:893`,
  `tokens > 600,000`) is the **same quantity** as the ledgered token total
  (`telemetry_arms.py:936`), so a true token-cap abort **must** record > 600K —
  none do. Hence **0 true token-cap aborts, 0 wall aborts** in round 8:
  **the entire round-7 token-cap abort class (4 runs at ≥300K) is GONE at
  600K**, and the residual non-completions are all in the D-E-only
  `DE_PHASE2_TOOL_CAP=4` / protocol-overhead class. The classification stands
  on the **frozen R4 exhaustive enumeration** (D-E arm ∧ tokens < 600K ∧ wall
  < 899 → phase-2 tool-cap, per `v36_prereg_freeze.md`); transcript/escrow
  evidence is **corroborating context only** and does not carry the
  classification. Mechanic (per-investigator, then arm-wide): each
  investigator may issue at most 4 phase-2 tool calls after the
  commit-reveal; the **5th** `tool_call` raises `_BudgetAbort`
  (`telemetry_arms.py:1052`), which **terminates the whole arm run at the
  first investigator (inv-a→inv-b→inv-c) to cross the cap** — e.g. P-02 s12:
  inv-a + inv-b committed, inv-c cut off mid-loop, run aborted; all 5
  aborts' escrow ledgers show incomplete `phase2-final` sets. **Crucially, 2
  of the 5 (328,161 and 362,587 tok) are the only runs in the entire 5-round
  campaign to exceed 300K — and with 600K of headroom they STILL aborted, on
  the tool-cap, not the token budget.**
- **C-EQ-TELEM: 9/9 completed, ALL 9 hit=true** (54,759–71,865 tok), 0
  crashes. The 5 post-snapshot runs were all D-E; **7 of 16 C-EQ slots never
  launched** (P-03 s12, P-05 s12, P-06 s12, P-07 s11, P-07 s12, P-08 s11,
  P-08 s12) because the stop halted dispatch and case-completion ordering
  drove D-E first. **C-EQ's 6/8 case-hit below is therefore a CEILING LOWER
  BOUND, not a measured 6** (see §4e/§2g).
- **Stop: stop-1 (C-EQ seed-saturation 3/10 = 0.30 ≥ 0.25) at the 18-run
  snapshot** (2,640,155 cumulative tok; `per_arm_crashes` D-E = 2). **STOP
  wording (code-judge REQUIRED):** the "2 crashes" is the stop rule's
  `status != "completed"` counting with the full-cohort /20 denominator
  (`pilot_run.py:202-214`) — i.e. **2 non-completions (both `aborted_budget`),
  NOT 2 `status=crashed`**; the final ledger has 0 crashed. **Snapshot gap
  (class of riders 9/13/14):** 5 post-snapshot in-flight/queued D-E runs
  (P-03 s12 260,734 · P-05 s12 258,083 · P-06 s12 292,735 · P-07 s11 362,587 ·
  P-08 s11 270,226; sum **1,444,365 = 4,084,520 − 2,640,155 exactly**, unique
  subset) → **final 23-run ledger** (14 D-E / 9 C-EQ), 4,084,520 tok. 9 of 32
  planned runs never launched; `cases_completed: 3` in STOP.json is a
  snapshot-time value (final: 6 full cases both arms). Relaunch refused by the
  closed-round guard (and scientifically invalid for a frozen round).
- **Case-level paired hit (frozen full-cohort rule R3, FINAL COMPLETE LEDGER
  primary):** **D-E 6/8 vs C-EQ 6/8 — TIE.** Both arms hit P-01…P-06; both
  non-hit on P-07/P-08 (D-E: s11 aborted + s12 never launched; C-EQ: no runs
  at all). Completing-run support: D-E 6/6, C-EQ 6/6. Every completion in both
  arms was hit (accuracy on completions: D-E 9/9, C-EQ 9/9).
- **H-budget vs H-burn (frozen rule + R2 guard, science-judge adjudicated):**
  ALL 9 D-E completions settled at ≤ 324,901 tok — far under the ~400K
  gray-zone floor, no pile-up at the cap → **H-burn on the mass criterion**
  (NOT the gray zone, NOT H-budget). The repeat-rate guard (recomputed this
  closeout, per-run within-completion repeats across the 9 completions:
  **76.0%** — 637 tool calls, 153 per-run-unique, i.e. 484/637 per-run
  repeats; globally only **39 distinct (tool, args) pairs** appear across all
  9 runs, a global repeat rate of 93.9%) is **higher** than the 48.1%
  round-4 baseline (same within-run definition: 195/378 D-E tool calls),
  rules out H-budget, and is consistent with H-burn. Per the R2 amendment the
  verdict must be labeled: **H-burn on the envelope axis, with non-convergence
  persisting at higher budget (mechanism-negative)** — NOT a "clean/efficient"
  H-burn.
  The two highest-mass completions (P-05 s11 324,901; P-06 s12 292,735) sit on
  the same cases whose OTHER seed aborted — a case-difficulty confound that
  weakens any residual H-budget reading further.
- **Integrity (all machine-verified):** JSON-mode parity **0 plain drops in
  both arms** (D-E 1,186 / C-EQ 156 responses, all JSON); all 8
  `case_sha256` values match round 7 (identity preserved); 14 D-E escrow
  ledgers (commit-reveal intact); envelope `600000` + git_rev `cff7d748`
  uniform across all 23 status.json; ground-truth isolation scan of all agent-
  facing transcripts + sandbox audits + escrows: **0 GT leaks** (non-vacuous:
  161 file opens, 0 `root_cause` opens); scorer_sha 4-way split = per-
  true_service content hash by design (round 7 had the identical 4 SHAs).

### 2g. What round 8 does and does not change

- **Changes (envelope axis CLOSED):** the §4c "budget-need vs burn-through"
  question is **machine-answered**: doubling 300K → 600K **eliminated the
  entire token-cap abort class** (round 7: 4 runs at ≥300K; round 8: 0 runs
  > 600K, max completion 324,901) while the residual non-completions **did
  NOT move with the envelope** — they are the tool-cap/protocol class,
  orthogonal to token mass (2 of them ran PAST 300K and still aborted there).
  **More token budget does not buy D-E completions.** The token-envelope axis
  is **closed**; a 1.2M round is a **predictable null** (science-judge Q5:
  do not run it).
- **Does NOT change (mechanism):** the contrast of interest is **still
  unresolved, and the standing negative finding EXTENDS to 600K** — the fifth
  envelope. D-E 6/8 vs C-EQ 6/8 (full-cohort, FINAL LEDGER) is a **tie that is
  the most favorable-to-D-E reading of the round** (C-EQ was never launched on
  2 of the 8 cases; its 6/8 is a lower bound). D-E still costs ~3.7× per
  completion (225.9K median vs 59.6K median), and its residual failures are a
  D-E-only mechanism property (`DE_PHASE2_TOOL_CAP=4` + committee overhead)
  that a token doubling cannot touch. **No advantage of decentralization/
  escrow is demonstrated at any envelope (60/90/150/300/600K).** The
  non-convergence signature **persists** (76% repeat rate > 48.1% baseline) —
  under the substituted model, D-E's investigators keep re-fetching the same
  evidence instead of converging, at every budget level tested.

## 3. What the rounds DID establish (feasible facts)

1. **The per-run token envelope is the structural binding constraint on D-E-
   TELEM, and it is model-invariant** — 0/6 on two model ids at 60K and 90K, and
   0/12 at 150K. Every budget-abort lands within ~8% of the cap, mid-investigation.
2. **The D-E failure mode is a non-convergent repeating-tool-call loop, not a
   single-point budget wall** — at 150K/48 (round 4) one investigator re-issued
   the *same* `(tool, args)` calls 2–4× (48.1% of all 378 D-E tool calls were
   identical repeats) and burned the shared envelope before handing off.
3. **The decentralized machinery never executed.** In all 12 round-4 D-E runs the
   phase-2 commit-reveal consultation and phase-3 committee sandbox were never
   reached (the third agent made 0 LLM calls in most runs). So D-E's measured
   cost is dominated by **phase-1 agent non-convergence under the substituted
   model** (~60–75% of the 1.21M D-E tokens per the science judge), with
   **~0% attributable to the decentralized mechanism's own overhead**.
4. **C-EQ-TELEM is feasible** and its completions are correct (all 3/3 round-4
   hits; scorer_sha-verified). Its non-completions are crashes of its *own
   instrument*, not diagnostic failures (see §6, disclosure 11).
5. **The centralized control completes at lower token cost** (54–77K) than the
   envelope cap, whereas D-E exhausts the full envelope without submitting.

## 4. The honest negative (strongest supportable statement)

> Under the substituted live model (SimulaChat `default` → Qwen3.8-27B, **not**
> the official published baseline) and the V3.2 frozen envelope (150K tokens /
> 48 tools / 1.40 volume band / 7.2M round ceiling), the pilot stopped after
> 20/40 runs when the D-E-TELEM crash rate (8/20 = 0.40) exceeded the frozen
> 25% stop-2 threshold. D-E-TELEM completed 0/12 runs on the 6 cases reached —
> 8 aborted at the token cap in non-convergent repeated-identical-tool-call
> loops, 2 died on malformed action outputs, 4 on frozen per-tool (logs/traces)
> sub-caps — and in **no run did it reach its commit-reveal or committee
> phases**. C-EQ-TELEM completed 3/8 runs, all hits; its 5 non-completions were
> crashes of the post-hoc-recalibrated prompt-volume canary, not diagnostic
> failures. **Therefore, under this substituted model and this envelope, no
> measurable advantage of decentralization, evidence escrow, or adaptive
> selection over a same-tools central manager has been demonstrated.** The
> contrast was not cleanly instanced: the decentralized mechanism under test
> never executed, and the control arm carried an asymmetric, over-sensitive
> crash instrument.

### 4b. Refined negative (round 5 / V3.3 — the current strongest statement)

> On the repaired instrument (V3.3, frozen `520f6859`; two fresh pre-run judges
> PASS) under the same substituted model (`default` → Qwen3.8-27B, **not** the
> official baseline) and same 150K envelope, the run stopped at stop-2 after 16
> ledgered runs (1.26M / 7.2M tokens) on the D-E crash-equiv 8/20 = 0.40 > 0.25.
> **D-E-TELEM completed exactly 1/9 runs (P-01 s12, hit=true, 138K tok), and in
> that run the full decentralized mechanism executed end-to-end for the first
> time — phase-1 sealed forecasts plus phase-2 commit-reveal from all three
> investigators.** Its 8 non-completions were 4 budget-aborts (distinct-call
> non-convergence under the substituted model) and 4 malformed-action protocol
> violations. **C-EQ-TELEM completed 7/7 runs, all hits, with zero crashes**
> (the 2 out-of-band runs were logged, not crashed). **Therefore no measurable
> advantage of decentralization, evidence escrow, or adaptive selection over a
> same-tools central manager is demonstrated under the substituted model.** The
> contrast is now cleanly instanced (the mechanism provably runs and can be
> correct); the refined characterization is that the decentralized arm is
> **model-limited under substitution** — it completes 1/9 of runs at higher cost
> (138K) versus the centralized control's 7/7 at lower cost (55–72K). This is a
> **feasibility/negative record, not an effect estimate.**

### 4c. Refined negative (round 6 / V3.4 — the current strongest statement)

> **Round 6 (V3.4, 300K shared envelope; substituted model, feasibility-only):**
> on a truncated D-E cohort (12 of 20 runs launched before the C-EQ-saturation
> stop), D-E completed **6/12** runs and **all 6 were correct** (vs 1/9 at
> 150K), while 4 crashed on malformed actions (18–27K tok, envelope-invariant)
> and 2 aborted at the token cap. We characterize D-E non-completion as
> **partially envelope-bound** (the completion-abort class rose with the cap)
> **but with an envelope-invariant crash class (33%) that is
> mechanism/model-bound**, not a single envelope-bound story. This does
> **not** demonstrate any advantage of decentralization over the same-tools
> control: on the only fully-paired case (P-03) C-EQ was 2/2 and D-E 0/2, and
> on the only fully-paired seed (P-06 s11) both were correct with **D-E at
> 3.8× the tokens**; D-E completions now cost ~3.2× (up to 3.8× per-case) the
> control, "same budget" being true only at the per-run cap, not realized
> spend. C-EQ reproduced round 5 (9/9 all-hit, 55–79K), confirming it is not
> envelope-bound. The standing negative therefore stands — refined from
> "model-limited" to "partially envelope-bound (abort class) +
> mechanism/model-bound (crash class)" — and a 600K round (round 7) would be
> required to disambiguate genuine budget-need from burn-through. This is a
> **single-arm D-E feasibility readout on a truncated cohort** (n=12,
> in-flight-inclusive), **not** a rate comparison or statistical test
> (no-confirmatory-reuse).

### 4d. Refined negative (round 7 / V3.5-D — the current strongest statement)

> **The crash class is eliminated; the mechanism question is unchanged and the
> standing negative stands.** Round 7 (V3.5-D, 300K envelope, 24-run ledger,
> single-arm D-E feasibility + C-EQ reproducibility) machine-verified the
> **0/14 crash-class crashes** (vs 4/12 in round 6): the round-6
> parse-drift `AgentProtocolError` class no longer occurs, and the two live
> drift-form emissions (P-04 s11/inv-c, P-06 s12/inv-c) were **recovered by (C)**
> into valid tool_calls rather than crashing — direct evidence the repair works.
> **This is an instrument-reliability result, not a mechanism result.** It does
> **not** demonstrate any advantage of decentralization/escrow over the
> same-tools control, for three independent reasons:
>
> 1. **Completion is still D-E-limited and ~5× costlier.** D-E completed 6/14
>    (43%) at 241–295K tok per completion vs C-EQ 10/10 at 49–77K. The residual
>    8 D-E non-completions are now **orthogonal** classes — 4 token-cap (the
>    envelope-bound class) + 4 phase-2 tool-cap (**D-E-only, pre-existing**
>    mechanism property) — **not** the crash class. Removing the crash class
>    did not make D-E complete as well as the control; it made D-E fail in a
>    *different, more instrument-defined* way.
> 2. **The fix is arm-asymmetric in effect** (applies to the shared path, but
>    D-E issues ~4× the `ask()` calls), so a D-E crash-rate drop is
>    structurally reliability-only for D-E and **no same-instrument D-E-vs-C-EQ
>    crash-rate comparison is valid** this round.
> 3. **Accuracy is cross-instrument** (V3.5 changed the instrument for both
>    arms); no round-7 accuracy number is causally comparable to rounds 5/6,
>    and the D-E "100% of completions" is on a denominator truncated by 8
>    aborts.
>
> **Standing finding UNCHANGED:** no demonstrated advantage of decentralization
> or escrow beyond access to counterfactual interventions, at any envelope
> (60/90/150/300K). Round 7 refines the *reliability* story (crash class gone)
> while leaving the *mechanism* question unresolved. The §4c "600K
> disambiguation round" (genuine budget-need vs burn-through for the token-cap
> class) is **still open and NOT what round 7 was** — round 7 was the 300K
> crash-class repair. Whether D-E's remaining non-completions reflect a true
> need for more than 300K, or burn-through under the substituted model,
> remains unanswered; a higher-envelope round (600K, not yet authorized) or a
> model change (not authorized) would be required. **This is a single-round,
> truncated-cohort (24/40), instrument-reliability readout, not a rate
> comparison, superiority/inferiority claim, or statistical test**
> (no-confirmatory-reuse).

### 4e. Refined negative (round 8 / V3.6, 600K — the current strongest statement)

> **The 600K disambiguation round is machine-answered, and the standing
> negative now extends across FIVE envelopes (60/90/150/300/600K).** Round 8
> (V3.6, 600K envelope, 23-run ledger; 2 fresh pre-run judges: code
> CONDITIONAL-PASS, science CONDITIONAL-PASS, all REQUIRED applied)
> machine-verified: (i) **the round-7 token-cap abort class is GONE** —
> 0 runs exceed 600K, max D-E completion 324,901 tok; (ii) **0 crash-class
> crashes, 0 drift emissions** (the repaired reliability held); (iii) the 5
> residual D-E non-completions are **5/5 phase-2 tool-cap / protocol-overhead
> (sub-envelope: 215,927–362,587 tok; 83.8–132.7s)** — and **2 of them
> (328,161 and 362,587 tok) ran PAST the round-7 300K cap and STILL aborted
> on the tool-cap, not the token budget**. H-budget is machine-refuted (H-
> burn on the mass criterion; per R2, labeled "with non-convergence
> persisting at higher budget — mechanism-negative", NOT clean/efficient;
> repeat rate 76.0% per-run / 93.9% global vs 48.1% round-4 — non-convergence
> persists at every envelope tested).
>
> **Why this is still a negative (not a D-E win), three independent
> reasons:**
>
> 1. **The case-level paired result is a TIE, and it is the most
>    favorable-to-D-E reading of the round.** Full-cohort (frozen R3, FINAL
>    ledger): D-E 6/8 vs C-EQ 6/8; both arms hit P-01…P-06 and both missed
>    P-07/P-08. C-EQ's 6/8 is a **ceiling lower bound** — 7 of 16 C-EQ slots
>    never launched (P-03/P-05/P-06 s12, P-07 and P-08 both seeds), so a
>    completed C-EQ cohort could only have scored **6/8 or 8/8**; the tie
>    cannot be distinguished from C-EQ dominance, and only C-EQ dominance or
>    a true tie are compatible with the evidence. A tie at ~3.7× D-E per-
>    completion cost (225.9K vs 59.6K median tokens) demonstrates **no advantage
>    of decentralization/escrow**, and it is the *least* adverse outcome D-E
>    could have produced this round.
> 2. **The residual D-E failures are a D-E-only mechanism property that no
>    token budget can fix.** `DE_PHASE2_TOOL_CAP=4` (D-E arm only) + committee
>    overhead: the first investigator to issue a 5th phase-2 tool call after
>    the commit-reveal aborts the entire arm run (telemetry_arms.py:1052).
>    Raising the envelope to 600K changed nothing about it — 2 of the 5
>    aborts had already passed 300K. **More token budget does not buy D-E
>    completions; the binding constraint on D-E completeness is protocol
>    overhead, not token mass.**
> 3. **The token-envelope axis is now CLOSED, and spending more on it is a
>    predictable null.** 5 envelopes (60/90/150/300/600K) show the same
>    pattern: D-E non-completion persists, C-EQ completes cheaply, no
>    demonstrated advantage. A 1.2M round is machine-predicted to reproduce
>    the tool-cap aborts (science-judge Q5: do NOT run it); any further
>    envelope experiment requires a new freeze + 2 fresh judges + human
>    re-approval and would add no mechanism information.
>
> **Standing finding UNCHANGED and EXTENDED:** no demonstrated advantage of
> decentralization or escrow beyond access to counterfactual interventions,
> at any envelope (60/90/150/300/600K). **This is a single-round,
> truncated-cohort (23/32), feasibility readout — a tie on a lower-bound
> control, not a superiority/inferiority claim or statistical test**
> (no-confirmatory-reuse; case-level paired hit per frozen R3). The one open
> mechanism hypothesis is now **specific and separately testable** (the
> phase-2 tool-cap / protocol-overhead class), and a new freeze for that
> hypothesis would be a different experiment, not a continuation of the
> envelope axis.

## 5. What MUST NOT be claimed from this series

- No effect size, power, or significance statement (frozen §6 no-confirmatory-reuse).
- No D-E-vs-C-EQ superiority **or** inferiority (rounds stopped early; C-EQ has
  an arm-specific crash instrument — §6/11).
- No model-robustness or "the official baseline would behave the same" claim
  (model substitution throughout).
- No causal attribution of D-E non-completion to "decentralization overhead"
  (rounds 1–4: the machinery never ran — §6/10; **round 5: in the 1 completion
  the mechanism DID run and was correct, but the 8 non-completions are still
  phase-1 non-convergence/malformed-output under the substituted model — the
  non-completions cannot be attributed to mechanism cost**).
- No "model capability" verdict from the crash causes (they are instrument +
  non-convergence outcomes under a substituted model).
- No reliability/reproducibility claim from the single D-E round-5 completion
  (n=1, single case, single seed).
- No blanket "D-E is envelope-bound" claim (round 6): 4/12 D-E crashes are
  envelope-INVARIANT (18–27K tok, present at both 150K and 300K) → that class
  is mechanism/model-bound; only the abort class moved with the cap.
- No "would-have-completed / latent success" booking of the two D-E
  budget-aborts (P-05 277K, P-08 300K); P-05 consumed ~1.8× more tokens across
  rounds and still did not submit → budget-truncated non-convergence.
- No reading of round-6 D-E 6/12 as a full-cohort completion rate or a
  D-E-favorable terminal state: the cohort is truncated (12/20 launched),
  in-flight-inclusive (2 post-trip completions), and the C-EQ stop pre-empted
  a D-E stop-2 the full cohort (6/20 = 0.30) would have tripped.
- No "clean mechanism test / equal-cost" framing of round 6: raising the
  envelope to let D-E complete is a **resource subsidy**, and "same budget"
  holds at the per-run cap only — D-E completions cost 3.2× (up to 3.8×) the
  control's realized spend.
- No "the crash class is fixed therefore decentralization is now viable /
  comparable" reading of round 7: the crash-class elimination is an
  **instrument-reliability** result. D-E still completes only 6/14 at ~5× C-EQ
  cost with case-level 2/8; the residual non-completions are orthogonal
  (token-cap + D-E-only phase-2 tool-cap). **No superiority, no
  comparability, and no "0 crash = 0 disadvantage" inference.**
- No reading of the round-7 raw stop-2 (8 D-E non-completions; full-cohort
  8/20 = 0.40) as a crash-rate: adjudication shows **0 are the crash class**;
  the raw and adjudicated numbers are different quantities and both are stated
  (§2d dual-count).
- No reading of the round-8 **6/8 vs 6/8 "tie"** as a balanced comparison or
  as D-E non-inferiority: C-EQ's 6/8 is a **ceiling lower bound** (7/16 slots
  never launched); the compatible outcomes are only tie-or-D-E-inferior, and
  the tie was achieved at ~3.7× per-completion cost. The correct statement is
  **no demonstrated advantage**, full stop.
- No "0 crashes" claim from the round-8 STOP.json `per_arm_crashes D-E = 2`
  wording without the correction: those are **2 non-completions
  (`aborted_budget`) counted over the /20 full-cohort denominator**, not 2
  `status=crashed`; the final ledger has 0 crashed runs.
- No "token-budget was the binding constraint on D-E" claim after round 8:
  the 600K envelope produced **0 runs > 600K**, and 2 runs that PASSED the
  round-7 300K abort threshold (328,161 / 362,587 tok) aborted on the
  **phase-2 tool-cap**. The binding constraint on D-E completeness is the
  D-E-only protocol overhead (`DE_PHASE2_TOOL_CAP=4`), not token mass.
- No "clean/efficient H-burn" claim: the R2-mandated label is "H-burn on the
  envelope axis, **with non-convergence persisting at higher budget
  (mechanism-negative)**" (repeat rate 76.0% per-run, up from 48.1% round-4).
- No "the 76.0%-vs-48.1% repeat-rate comparison is a same-denominator
  controlled metric" claim: both use the within-run identical-(tool,args)
  definition, but the cohorts differ (round 8 = 9 completions only, 637
  calls; round 4 = 12 D-E runs, 378 calls) — it is corroborating, not a
  controlled comparison.
- No "0 parse-drift" claim for round 7: **2 drift-form emissions occurred**
  (P-04 s11/inv-c, P-06 s12/inv-c) and were **recovered by (C)** — the correct
  statement is **0 crash-class crashes** (`status=crashed`), not 0 drift
  emissions.

## 6. Mandatory disclosure riders (15)

Items 1–7 (freeze-stamp list), 8–11 (round-4 outcome-judge list), 12
(round-5 / V3.3), 13 (round-6 / V3.4), 14 (round-7 / V3.5-D), 15
(round-8 / V3.6). Any report or claim citing any V3 round must carry these.

1. **MODEL-SUBSTITUTION** — the live rounds used SimulaChat `default` (echoes
   Qwen3.8-27B) / `Borealis2-preview`, not the official published baseline.
2. **B3 post-hoc recalibration** — the 1.40 volume band was recalibrated after
   observing deterministic exceedances; it is not part of the original prereg.
3. **Completion gaps may be canary-constructed** — some completion evidence
   predates the live runs and came from offline canaries.
4. **D-E infeasibility is multi-resource** — rounds are feasibility-only; **no
   effect estimate** may be drawn.
5. **Parallel execution provenance** — round 4 ran through `pilot_parallel.py`
   (threads, concurrency 6, retry-once), recorded in `parallel_meta.json`.
6. **Stop trip → cause decomposition + human gate** — provided (§3, §6).
7. **Live-canary non-convergence + composite-overhead caveat** — the composite
   of decentralization-overhead + agent non-convergence is dominated by the
   non-convergence term under this model.
8. **Stop-1 miscalculation** — round 4's stop-1 co-trip is a seed-level
   saturation implementation defect (0.30 from 3 one-seed successes;
   spec-correct sat = 0.0). The halt is justified by stop-2 (D-E 0.40) alone.
   Defect fixed in code (commit 57d1e1f); STOP.json is an unaltered artifact.
9. **STOP.json vs ledger snapshot gap** — STOP.json reflects 16 runs / 1,132,481
   tokens at trip; 4 in-flight D-E runs finished afterward (by design). Final
   ledger = 20 runs / 1,744,526 tokens (both < 7.2M). Both numbers stated.
10. **D-E phase-2/3 never executed** — in all 12 round-4 D-E runs the
    commit-reveal and committee phases were never reached; D-E non-completion
    is phase-1 non-convergence under the substituted model, not the mechanism's cost.
11. **Asymmetric volume-gate instrument** — the crash-on-band gate existed only
    on C-EQ-TELEM, set 0.05 above the observed deterministic maximum, with
    demonstrated live-model variance (P-01 1.235→1.601) exceeding it; C-EQ
    crashes are instrument outcomes, not diagnostic failures, and left in place
    would bias any D-E-vs-C-EQ contrast **in favor of** D-E.
12. **Round 5 / V3.3 — repair + single D-E completion** — round 5 ran on the
    repaired instrument (symmetric anti-loop cache, per-tool sub-caps removed,
    volume canary demoted to a logged flag) after 2 fresh independent pre-run
    judges PASSed it and it was frozen at `520f6859`. The **C-EQ volume
    demotion was validated live**: 2 out-of-band runs (ratio 1.71/1.74) were
    logged `volume_band_violation=true` and **not** crashed → C-EQ 0 crashes.
    The **anti-loop cache's effect on D-E is disclosed, not neutral**: it made
    identical repeat-calls free (so D-E no longer dies on repeats) and thereby
    **unmasked** the true D-E failure mode — distinct-call non-convergence +
    malformed actions under the substituted model. The **single D-E completion
    is n=1** (P-01 s12, one case, one seed) and **must not** be read as a
    reliability or effect estimate. The stop-2 trip (D-E 8/20 = 0.40) occurred
    at 16 ledgered runs; **P-05 s12, P-07–P-10 (both arms) never executed**.
13. **Round 6 / V3.4 — 300K symmetric envelope + snapshot gap** — round 6
    raised the SHARED per-run envelope 150K → 300K (A1-parity-guarded; both
    arms) with the 12M round ceiling; nothing else changed. **Snapshot gap
    (class of rider 9):** STOP.json = 16 runs at the stop-1 trip (C-EQ
    saturation 3/10 = 0.30); final ledger = 21 runs; the D-E 6/12 includes 2
    **post-trip in-flight completions** (P-07 s11, P-04 s12); on the full
    ledger D-E non-completion is 6/20 = 0.30 > 0.25, which **would have
    tripped stop-2** — the C-EQ stop pre-empted it, so the terminal state is a
    **D-E-favorable transient**, not a full-cohort rate. The **two D-E
    budget-aborts (P-05 277K, P-08 300K) are non-completions and must not be
    booked as "would-have-completed"** — P-05 (152K→277K across rounds) is
    direct counter-evidence (more tokens, still no submission). Cost must be
    stated as **3.2× mean / up to 3.8× per-case** (not "4×"), and "same
    budget" is true at the **per-run cap only**, not realized spend. D-E
    `prompt_volume_ratio` is **not measured** by the D-E arm (status.json
    hardcodes null — code-judge round-6 SHOULD-FIX, recorded as a known
    instrument gap; the A1 volume-parity metric is C-EQ-observed only).
14. **Round 7 / V3.5-D — crash-class repair; reliability-only; raw-vs-adjudicated**
    — round 7 ran the B+C+D instrument (freeze `v35_prereg_freeze.md` @
    `9369b5b8`/`8b8bda5`, code `11e7e63a`, blob `1b33c002…`, 2 fresh pre-run
    judges: code PASS / science CONDITIONAL-PASS with all items applied). (i)
    **The crash-class elimination is machine-verified and reliability-only:**
    0/14 `status=crashed` (vs 4/12 round 6); **2 live drift-form emissions
    (P-04 s11/inv-c, P-06 s12/inv-c) were RECOVERED by (C)** into valid
    tool_calls — NOT crashes, and evidence (C) works. The correct statement is
    **0 crash-class crashes**, **not "0 parse-drift"** (2 were emitted). (ii)
    **The 8 D-E non-completions are orthogonal, NOT the crash class:** 4
    token-cap (≥300K) + 4 phase-2 tool-cap (`DE_PHASE2_TOOL_CAP=4`, D-E-ONLY,
    pre-existing V3.4, sub-envelope). The tool-cap is a D-E mechanism property
    that HINDERS D-E completeness and is disclosed as such; it is NOT
    attributed to the crash fix. (iii) **Raw-vs-adjudicated dual count is
    mandatory:** raw stop-2 = 8/14 (0.57; full-cohort 8/20 = 0.40; STOP
    `rate 0.3` is full-cohort /20 at the 22-run snapshot); adjudicated
    crash-class = 0/14. Both are stated side by side (§2d). (iv) **Snapshot
    gap (class of riders 9/13):** STOP.json = 22 runs / 3,734,441 tok; 2
    post-trip D-E aborts (P-07 s11, P-08 s11) → final 24-run ledger /
    4,311,893 tok (delta reconciles exactly); 16 of 40 planned runs never
    launched. (v) **The fix is arm-asymmetric in effect** (D-E ~4× the
    `ask()` calls), so round 7 is structurally reliability-only for D-E and
    **no same-instrument D-E-vs-C-EQ crash-rate comparison is valid**;
    accuracy is cross-instrument for both arms. (vi) **JSON-mode parity held:**
    0 plain-mode drops in either arm (C-EQ 176/176, D-E 1210/1210). (vii)
    **The §4c 600K budget-need-vs-burn-through disambiguation is STILL OPEN** —
    round 7 was the 300K crash-class repair, not the 600K round.
15. **Round 8 / V3.6 — 600K envelope; the disambiguation round; tie at lower
    bound** — round 8 ran the V3.6 instrument (freeze `v36_prereg_freeze.md`
    @ `cff7d748`, exactly two constants changed: `MAX_TOKENS_PER_RUN` 300K →
    600K, `ROUND_TOKEN_CEILING` 12M → 24M; 2 fresh pre-run judges: code
    CONDITIONAL-PASS / science CONDITIONAL-PASS, all REQUIRED + RECOMMENDED
    applied doc-only; human gate cleared 2026-10-11). (i) **H-budget is
    machine-refuted:** 0 runs > 600K; max D-E completion 324,901 tok; 2
    aborts (328,161 / 362,587 tok) PASSED the round-7 300K threshold and
    STILL aborted — on the phase-2 tool-cap. Verdict label per R2: **H-burn
    on the envelope axis, with non-convergence persisting at higher budget
    (mechanism-negative)** — not "clean/efficient". (ii) **The 5 D-E
    non-completions are 5/5 phase-2 tool-cap / protocol-overhead** (0 true
    token-cap, 0 wall; token gate `telemetry_arms.py:893` compares the SAME
    quantity as the ledgered total `:936`, so a token-cap abort would record
    > 600K); classification stands on the frozen R4 enumeration — transcript
    and escrow evidence are corroborating only. (iii) **The STOP.json
    `per_arm_crashes D-E = 2` is 2 non-completions (`aborted_budget`) over
    the /20 full-cohort denominator, NOT 2 crashes**; final ledger 0
    `status=crashed`. (iv) **The case-level 6/8 vs 6/8 is a TIE and the most
    favorable-to-D-E reading:** C-EQ never launched on 7 of 16 slots (P-03
    s12, P-05 s12, P-06 s12, P-07 s11/s12, P-08 s11/s12), so C-EQ's 6/8 is a
    **ceiling lower bound**; compatible outcomes are tie-or-D-E-inferior.
    No superiority, no non-inferiority, no "balanced comparison". (v)
    **Snapshot gap (class of riders 9/13/14):** STOP.json = 18 runs /
    2,640,155 tok (stop-1 C-EQ sat 3/10); 5 post-snapshot D-E runs (sum
    1,444,365 = 4,084,520 − 2,640,155 exactly) → final 23-run ledger /
    4,084,520 tok (14 D-E / 9 C-EQ); 9 of 32 planned runs never launched;
    `cases_completed: 3` is snapshot-time (final: 6 full cases). (vi)
    **Cost:** D-E completions 180K–325K (median 225.9K) vs C-EQ 55K–72K
    (median 59.6K) — ~3.7× per-completion; "same budget" holds at the per-run
    cap only. (vii) **JSON-mode parity held** (D-E 1,186 / C-EQ 156, 0 plain
    drops); GT isolation scan 0 leaks (161 file opens, 0 `root_cause`
    opens); case_sha256 all 8 match round 7. (viii) **Two UNVERIFIABLE flags
    remain open in the record** (science-judge, outcome): **f1 — the "0
    drift emissions" claim is structural only** (0 tool-name-in-action
    fields in the 9 completed + 5 aborted D-E transcripts); it does NOT
    prove 0 drift-recoveries via the (C) repair path, which is not logged in
    the current instrument — the round-7 `drift-recovered` marker has no
    round-8 equivalent, so the strongest defensible statement is "**0
    crash-class crashes; 0 raw drift-form emissions; drift-recovery events
    not instrumented**". **f2 — the 76.0% vs 48.1% repeat-rate pair is
    corroborating only**: same within-run identical-(tool,args) definition,
    but different cohorts (9 completions / 637 calls vs 12 runs / 378 calls)
    and no matched denominator; the R2 guard's formal trigger (≥ baseline)
    is met under the as-computed values and a matched-denominator
    re-derivation would not be expected to reverse it, but the pair must not
    be quoted as a controlled comparison.

## 7. Decision point (HUMAN GATE)

**Status: rounds 5, 6, 7, AND 8 have now been IMPLEMENTED and RUN** — round
5 (V3.3, §2b/§4b), round 6 (V3.4 300K, §2c/§4c), round 7 (V3.5-D 300K crash-
class repair, §2d/§4d), and **round 8 (V3.6 600K envelope, §2f/§4e)** — the
judge-mandated budget-need-vs-burn-through disambiguation round, now complete.
Round 8 **machine-answered the open question**: the token-cap abort class is
GONE at 600K (0 runs > 600K); H-budget is machine-refuted (H-burn on the
envelope axis, non-convergence persisting — mechanism-negative); the residual
D-E non-completions are 5/5 phase-2 tool-cap / protocol-overhead, and the
case-level result is a **6/8 vs 6/8 tie at a ceiling lower bound** (C-EQ 7/16
slots never launched). The standing negative finding now **extends across
FIVE envelopes (60/90/150/300/600K)**: no demonstrated advantage of
decentralization/escrow at any token budget tested. The token-envelope axis
is **CLOSED**. The current gate is what to do next:

- **(i) Accept the round-8 refined negative as the V3 record (RECOMMENDED by
  the round-8 outcome judges)** — the series now has the complete
  reliability + feasibility + envelope characterization: mechanism proven
  executable + correct; the crash class repaired and verified gone (rounds
  7/8: 0/14, 0/14); control robust (rounds 5/6/7/8: 7/7, 9/9, 10/10, 9/9,
  0 crashes); D-E non-completion fully taxonomized (crash class [gone] +
  token-cap [envelope axis now closed] + D-E-only phase-2 tool-cap [the
  residual binding constraint]); no advantage demonstrated at any cost level
  tried. No further live runs on the envelope axis; close out.
- **(ii) A NEW experiment for the phase-2 tool-cap / protocol-overhead
  hypothesis (science-judge Q5: the only open, specific, testable mechanism
  hypothesis left)** — e.g. raising/relaxing `DE_PHASE2_TOOL_CAP` (D-E-only
  instrument constant) under a NEW prereg freeze + 2 fresh judges + human
  approval of scope/spend (no-confirmatory-reuse: it cannot confirm round
  8). It would answer whether D-E's residual non-completion is the cap
  itself or the deeper non-convergence (repeat rate 76% suggests the latter,
  but that is not yet controlled). Note it changes the instrument's
  mechanism-relevant constant, so it is a different experiment, not an
  envelope continuation.
- **(iii) Stop the series.**
- **(c) Model change** (e.g., the official published baseline) — **not
  authorized**; would additionally void all substitution caveats and require a
  full re-preregistration. Under the substituted model, D-E's investigators
  re-fetch the same evidence (76% per-run repeat rate) at every envelope —
  a model change is the only remaining lever that could plausibly change the
  mechanism readout.
- **Explicitly NOT recommended (round-8 outcome judges, science Q5): a 1.2M
  round** — machine-predicted null: the binding constraint is the tool-cap /
  protocol overhead, which is orthogonal to token mass; 2 aborts already ran
  past 300K with 600K of headroom and aborted on the tool-cap.

The turnkey specs that were implemented:
`design/amendment_v33_both_arms_repair_DRAFT.md` (V3.3); V3.4 freeze:
`v34_prereg_freeze.md` (in the `RepliClaw-stg2-v34` worktree, FINAL,
code `6e32153`); V3.5 freeze: `v35_prereg_freeze.md` (round 7 / V3.5-D,
FINAL, code `11e7e63a` blob `1b33c002…`; in the `RepliClaw-stg2-v35`
worktree); **V3.6 freeze: `v36_prereg_freeze.md` (round 8 / V3.6 600K,
FINAL, code `cff7d748`; in the `RepliClaw-stg2-v36` worktree).**

## 8. Evidence pointers

- Rounds: `.artifacts/rcaeval/pilot/run/round{1,2}/`,
  `.artifacts/rcaeval/pilot/run_v32/round4/` (rounds 1–4),
  **`.artifacts/rcaeval/pilot/run_v33/round5/`** (round 5 / V3.3; in the
  `RepliClaw-stg2-v33` worktree), and
  **`.artifacts/rcaeval/pilot/run_v34/round6/`** (round 6 / V3.4; in the
  `RepliClaw-stg2-v34` worktree) and
  **`.artifacts/rcaeval/pilot/run_v35/round7/`** (round 7 / V3.5-D; in the
  `RepliClaw-stg2-v35` worktree) and
  **`.artifacts/rcaeval/pilot/run_v36/round8/`** (round 8 / V3.6; in the
  `RepliClaw-stg2-v36` worktree) — all gitignored: STOP.json, ledger.jsonl,
  per-run status/escrow/audit_llm/audit_sandboxes/score,
  `pilot_report_round{4,5,6,7}.json/.md`, `parallel_meta.json`.
- Freeze stamps: `design/v3_prereg_final_freeze.md`, `design/v31_prereg_freeze.md`,
  `design/v32_prereg_freeze.md`, **`design/v33_prereg_freeze_DRAFT.md`**
  (round 5, commit `520f6859`), **`v34_prereg_freeze.md`** (round 6 / V3.4,
  FINAL, code `6e32153`; in the `RepliClaw-stg2-v34` worktree),
  **`v35_prereg_freeze.md`** (round 7 / V3.5-D, FINAL, code `11e7e63a` blob
  `1b33c002…`; in the `RepliClaw-stg2-v35` worktree) + the 4-point probe
  artifact `design/v35_probe_all4points.json`, and
  **`v36_prereg_freeze.md`** (round 8 / V3.6 600K, FINAL, code `cff7d748`; in
  the `RepliClaw-stg2-v36` worktree).
- Round-7 / round-8 adjudication (offline): the dual-count tables in §2d/§2f
  are reproducible from the run dirs (status.json `status`/`tokens`/`wall_s`
  + audit_llm.json per-session `role=="response"` payloads); the round-8
  repeat-rate and case-level paired numbers are reproducible from the round-8
  audit files + ledger.jsonl as described in §2f/§4e.
- Judge reports: round-4 outcome (code + science) — I4.13; round-5 pre-run
  (code + science) — I4.16; round-5 outcome (code + science) — I4.19;
  round-6 (V3.4) pre-run (code + science) — I4.21; round-6 outcome (code +
  science) — I4.22; round-7 pre-run + outcome — I4.24/I4.26; **round-8 (V3.6)
  pre-run (code CONDITIONAL-PASS / science CONDITIONAL-PASS) and outcome
  (code CONDITIONAL-PASS → resolved PASS on artifact integrity, science
  CONDITIONAL-PASS — all REQUIRED + RECOMMENDED applied) — I4.27.**
- State: `EXECUTION_STATE.md` I4.7–I4.27; `DECISIONS.md` D-V3-013–D-V3-020.
