# FF-06 Independent Critical Review — AMEND_NULL_MODEL_CORRECTION_20261011.md

**Date:** 2026-10-12
**Reviewer:** independent review via `rc-review` subagent (model: default/Qwen3.8-27B thinking, Sigma2 simulachat BYOK), RepliClaw worktree `RepliClaw-ff05res`, branch `ff06-nullmodel-review`.
**Artifact reviewed:** `docs/next_stage/AMEND_NULL_MODEL_CORRECTION_20261011.md` (status "DRAFT — pending independent science signoff"), introduced by commits `5b6fb7e` + `1f2e29e`.
**Repo HEAD at review:** `c1fe7f9` (`git rev-parse HEAD`).

## §1 Scope and method

Checked the amendment's three load-bearing claims against source of record:
(1) the statistical correction itself; (2) that frozen files are untouched and its empirical
claims about code are true; (3) that the canary evidence it pastes is reproducible now.

Commands run (all in `/home/susan/projects/RepliClaw-ff05res`):
- `git status --short && git branch --show-current && git rev-parse HEAD` → clean tree (untracked `uv.lock` only), HEAD `c1fe7f9`.
- `grep -rn "ERRATUM (2026-10-11, FF-03)" docs/` → pointer present at exactly one live location: `docs/next_stage/EXPERIMENT_PROTOCOL_V3_DRAFT.md:65`, verbatim matching the doc's quoted text.
- Read `docs/next_stage/design/v3_prereg_final_freeze.md` lines 180–200: S-sat guard note ("the one-arm s = 0.25 ceiling-saturation trip probability at Δ=0 is the reason S-sat exists") present **unchanged**; SIMULATION-ONLY labels intact (lines 181, 297).
- Read `docs/next_stage/design/g3_pilot_spec_draft.md` §5 rule 1 (lines ~254–268): flawed phrasing "one-arm s=0.25 already gives ~30–40% false-fire at Δ=0" still present in-file, corrected only by reference — as the amendment discloses.
- Read `scripts/mc_rule015.py`: `SAT_NULL_CELLS = [("both",0.50),("both",0.75),("de_only",0.50)]` (line 87); `original_grid()` places a `de_only, delta=0.0` cell in the 254-cell grid; `generate_data()` confirms `de_only` sets `p_de=1.0` on the mask while `p_ceq=q` → realized effect ≈ s·(1−q̄) > 0 at nominal Δ=0. `slice_cells()` (N=24, k=4, 40 cells) uses `sat="none"` or `"both"` only for d=0 rows — claim verified.
- Ran `uv run python src/repliclaw/benchmarks/common/cluster_bootstrap.py` → `self-test PASSED`; Case 2 null case CI95=(−0.069, 0.194) includes 0 → generator/pinned-L5 implementation matches the amendment's §2 specification.
- Ran `uv run python -m pytest tests/benchmarks tests/experiments --tb=no` → **`192 passed, 23 skipped, 2 xfailed in 6.23s`**, exit 0. The amendment (and commit `1f2e29e`) report `180 passed, 23 skipped, 3 xfailed` from 2026-10-11. No failure either way; the count drift is attributable to pilot-harness test additions between runs (see FF06-F5).
- Grepped `docs/next_stage/science/monte_carlo_power_v3.md` for the same phrasing → found two additional unflagged occurrences (see FF06-F2).
- Confirmed `docs/next_stage/design/v31_prereg_freeze.md` and `v32_prereg_freeze.md` contain no "false-fire"/"type-I at Δ=0" phrasing (grep empty) — nothing missed there.
- `git show 5b6fb7e --stat` → FF-03 commit touched only the amendment doc (+69) and the one-line erratum in `EXPERIMENT_PROTOCOL_V3_DRAFT.md` (+1). Frozen files and `docs/next_stage/reviews/*` untouched. Verified.

## §2 Findings

| ID | Severity | Claim examined | Verdict | Evidence |
|----|----------|----------------|---------|----------|
| FF06-F1 | MAJOR (adversarial) | §4 asserts a complete inventory of "live (non-frozen, non-archive) documents carrying defective wording" in the bound search set, listing only three locations. | UNSUPPORTED | `docs/next_stage/science/monte_carlo_power_v3.md:49` ("decision rule still fires MEANINGFUL_POSITIVE 83% … with true Δ = 0") and `:112` ("s=0.5 → 83% false-fire at N=24") carry the very same defective "Δ=0" label on the single-arm upper-bound cell, yet this file was never flagged. It also functions as the *power authority* cited by the protocol, so an unsuppressed misleading statement inside it survives sign-off. Mitigating context: line 49 opens with "(not type-I in the usual sense, a design-level one)", which hedges the error; the omission looks like scope discipline (science/ treated as frozen-authority material), but the amendment does not state this boundary anywhere. |
| FF06-F2 | MINOR | "The original 254-cell grid's de_only Δ=0 cell must not be cited as a type-I/null condition." | SUPPORTED (claim correct; fix incomplete) | `mc_rule015.py:87` `SAT_NULL_CELLS` includes `("de_only",0.50)` and `original_grid()` emits it at `delta=0.0`; `generate_data()` shows the realized effect is positive. The code comment/docstring around those cells does not mark the cell as a *non-null diagnostic*, so future readers could re-cite it. Doc-only amendment cannot fix code comments; acceptable for this gate, flag for next MC pass. |
| FF06-F3 | MINOR | Canary 1 evidence "180 passed, 23 skipped, 3 xfailed" (2026-10-11). | PARTIALLY-SUPPORTED (stale) | Independent rerun today: `192 passed, 23 skipped, 2 xfailed in 6.23s` (exit 0). All canaries still pass; counts drifted because `tests/experiments/test_pilot_driver.py` gained tests after FF-03 ran (commits db5c6e5, 5f78c82, c1fe7f9). The DRAFT quotes 10-11 output without a "snapshot as of 2026-10-11" caveat; a reader auditing at sign-off time will see different numbers. |
| FF06-F4 | NIT | Erratum pointer placement and "single line only" claim. | SUPPORTED | Exactly one insertion, `EXPERIMENT_PROTOCOL_V3_DRAFT.md:65`, verbatim identical to the doc's quoted text; `git show 5b6fb7e --stat` shows no other file edits. Frozen S-sat rule text above it is byte-identical to pre-amendment. |
| FF06-F5 | NIT | "Frozen files unchanged." | SUPPORTED | v3/v31/v32 freeze greps show the S-sat guard note and SIMULATION-ONLY labels intact; no freeze file appears in FF-03's diff. P08 statements out of my read budget — accepted on stated basis (documented limitation). |
| FF06-F6 | NIT | Location #2 (g3_pilot_spec_draft §5 rule 1) corrected "by reference to this document (no in-file edit)." | PARTIALLY-SUPPORTED | Disclosed honestly, but the phrase "false-fire at Δ=0" remains unmarked in the pilot spec, whose §5 rules get carried into prereg per the document's own "(S-W2-4, verbatim to carry into the prereg)" convention. Sign-off should explicitly decide whether that sentence is grandfathered or needs its own pointer before G4. |

## §3 Statistical-correctness assessment

(a) **Correction core — CORRECT.** Forcing arm A to p=1.0 on fraction s of cases while arm B keeps per-case p_c makes the realized per-case contrast on ceiling cases 1−p_c, so the population estimand becomes E[contrast] ≈ s·(1−p̄_c) > 0 under nominal δ=0. A rule rejecting H0:contrast=0 in that setup is detecting a real (design-induced) effect, not committing a type-I error. Identifying the valid type-I cell as "equal per-case probabilities across arms, no upper bound (or symmetric upper bounds)" is the standard exchangeability argument and is exactly what the pinned L5 self-test Case 2 implements (verified run: null CI includes 0). The distinction "nominal δ parameter ≠ realized per-case difference" is precise. One residual imprecision: the doc says a significant contrast under such a setup "is not by itself a type-I error" — strictly, calling it "a correctly detected nonzero realized effect" presumes the generator model is right; the safer statement is "not interpretable as type-I *under the intended null*". Not material.

(b) **Correct null generation — PROPERLY SPECIFIED AND IMPLEMENTABLE.** "Per case p_c(D-E)=p_c(C-EQ), symmetric upper bounds on identical masked cases" is fully implementable in `generate_data()` (it already has the machinery: `sat="both"` applies p=1.0 to both arms on the same mask). Minor gap: the spec does not say whether asymmetric ceiling *rates* (s_A ≠ s_B) or non-shared masks are also forbidden; under the equal-probabilities-per-case criterion they would violate H0 too. Worth one clarifying sentence before this text is copied into a prereg appendix.

(c) **Simulation-only labeling — CORRECT.** N=24/k=4/MDE=0.20 stays labeled SIMULATION-ONLY in the frozen doc (v3 freeze lines 181, 297) and the amendment restates it; no confirmatory guarantee claimed; G4 recomputation with pilot σ̂_D required. The "24×4×2 rollouts ≠ 192 independent cases; unit of inference is the case" statement is correct given the cluster-bootstrap resampling scheme.

(d) **Residual errors:** none in the mathematics. Two documentation-hygiene issues: the Monte Carlo power authority file itself still presents the 83% figure adjacent to "true Δ = 0" without the erratum pointer (FF06-F1), and the stale canary count (FF06-F3) undermines audit reproducibility if left unfootnoted. Neither invalidates the correction; both should be cleared before the amendment leaves DRAFT status.

## §4 Sign-off recommendation

**CONDITIONAL (2)**

1. **C1 (clears FF06-F1):** add one sentence to the amendment's §4 scope section stating whether `docs/next_stage/science/monte_carlo_power_v3.md` is inside or outside the bound search set; if outside (frozen-authority), record that decision explicitly and note lines 49/112 as known unamended legacy text pending any future versioned amendment; if inside, add the one-line erratum pointer there too.
2. **C2 (clears FF06-F3):** footnot the Canary-1 summary line as "snapshot 2026-10-11; re-verified 2026-10-12 as 192 passed, 23 skipped, 2 xfailed, exit 0" (or equivalent), so the evidence is auditable at sign-off time.

Optional (does not block): mark `SAT_NULL_CELLS`'s `de_only` entry as a non-null diagnostic in code comments (FF06-F2); explicit decision on g3_pilot_spec §5 "false-fire" sentence carry-forward (FF06-F6); add one sentence forbidding asymmetric ceiling rates/masks in the null-generation spec (§3(b)).

This review does not itself constitute signoff; signoff is a human decision.
