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

## 6. Mandatory disclosure riders (13)

Items 1–7 (freeze-stamp list), 8–11 (round-4 outcome-judge list), 12
(round-5 / V3.3), 13 (round-6 / V3.4). Any report or claim citing any V3
round must carry these.

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

## 7. Decision point (HUMAN GATE)

**Status: (i)→(ii) has now been IMPLEMENTED and RUN twice** — round 5 (V3.3,
§2b/§4b), then the human-authorized **(ii) symmetric 300K raise** = **round 6
(V3.4, §2c/§4c)**. The current gate is what to do with the round-6 result:

- **(i) Accept the round-6 refined negative as the V3 record** — the series now
  has the cleanest-possible feasibility characterization: mechanism proven
  executable + correct at both 150K (1/9) and 300K (6/12 all-hit), control
  robust (7/7 then 9/9, 0 crashes), non-completion taxonomized into
  envelope-bound (abort) vs mechanism/model-bound (crash) classes, no
  advantage demonstrated at any cost level tried. No further live runs; close
  out.
- **(ii) Round 7 at 600K** — the judge-mandated disambiguation for the abort
  class (genuine budget-need vs burn-through; P-05/P-08-style runs). This is a
  **new instrument configuration** → new prereg freeze + 2 fresh judges + human
  approval of scope/spend (no-confirmatory-reuse: round 7 cannot confirm
  round 6). Note the crash class (33%, envelope-invariant) will NOT respond to
  any envelope raise — only the abort class can be disambiguated.
- **(iii) Stop the series.**
- **(c) Model change** (e.g., the official published baseline) — **not
  authorized** per D-V3-017; would additionally void all substitution caveats
  and require a full re-preregistration. Also note: the crash class is
  mechanism/model-bound, so only a model/protocol change (not an envelope
  change) can address it.

The turnkey specs that were implemented:
`design/amendment_v33_both_arms_repair_DRAFT.md` (V3.3); V3.4 freeze:
`v34_prereg_freeze.md` (in the `RepliClaw-stg2-v34` worktree, FINAL,
code `6e32153`).

## 8. Evidence pointers

- Rounds: `.artifacts/rcaeval/pilot/run/round{1,2}/`,
  `.artifacts/rcaeval/pilot/run_v32/round4/` (rounds 1–4),
  **`.artifacts/rcaeval/pilot/run_v33/round5/`** (round 5 / V3.3; in the
  `RepliClaw-stg2-v33` worktree), and
  **`.artifacts/rcaeval/pilot/run_v34/round6/`** (round 6 / V3.4; in the
  `RepliClaw-stg2-v34` worktree) — all gitignored: STOP.json, ledger.jsonl,
  per-run status/escrow/audit_llm/audit_sandboxes/score,
  `pilot_report_round{4,5,6}.json/.md`, `parallel_meta.json`.
- Freeze stamps: `design/v3_prereg_final_freeze.md`, `design/v31_prereg_freeze.md`,
  `design/v32_prereg_freeze.md`, **`design/v33_prereg_freeze_DRAFT.md`**
  (round 5, commit `520f6859`), and **`v34_prereg_freeze.md`** (round 6 /
  V3.4, FINAL, code `6e32153`; in the `RepliClaw-stg2-v34` worktree).
- Judge reports: round-4 outcome (code + science) — I4.13; round-5 pre-run
  (code + science) — I4.16; round-5 outcome (code + science) — I4.19;
  round-6 (V3.4) pre-run (code + science) — I4.21; round-6 outcome (code +
  science) — I4.22.
- State: `EXECUTION_STATE.md` I4.7–I4.22; `DECISIONS.md` D-V3-013–D-V3-018.
