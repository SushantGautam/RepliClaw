# P09 — Release Checklist (for the human team)

Everything a human must do to turn `DRAFT_ANSWERS.md` into the **public project
presentation** (README/website/paper source, public repo, demo video, evidence archive,
license, citation) of the independent RepliClaw research project
(https://github.com/SushantGautam/RepliClaw). This is a public release, not a competition
submission; there is no external deadline.

Do the steps **in order**. Each step ends with ✅ when done.

---

## Step 0 — Read the two companion docs first (5 min)

1. Open `FACT_CHECK_LIST.md`. It lists every claim with its source + status: **F1–F17/F19** (the
   historical per-module checkpoints P02/P03/P04 + G0 + prior art/team/rubric) and **F20–F29**
   (the run-branch state: 240/8 full gate at the run-branch tip `945986f` — 235/8 at A9 tip
   `3491032` — offline 4-arm parity campaign, EESS slice, Tox21 case,
   oracle-gated scorer + passing self-test, live arm *implemented + tested*, live window, novelty
   positioning). It also records a **critical test-count discrepancy** (P09 re-verified the
   historical module counts **78 / 73 / 74**, not the 62 / 69 / 74 the old checkpoint docs record).
2. Note the distinction that carries the whole presentation: **offline** (runnable now) vs
   **implemented + tested** (the live arm) vs **scheduled live** (not yet executed). The headline
   live matched-budget result is `[PENDING: P08 live]`; the offline parity numbers are feasibility
   evidence only, not the live result.
✅ _discrepancy + tested-vs-executed distinction understood_

---

## Step 1 — Resolve every `[PENDING: …]` placeholder

Find them all: `grep -n 'PENDING' docs/application/DRAFT_ANSWERS.md`

| Placeholder | Who resolves | What to do |
|---|---|---|
| `[PENDING: TEAM]` (sections 2, 4) | human team | Insert real names, roles, and confirm each section-4 capability is true. **List only capabilities you can stand behind** — the draft already warns against over-listing. |
| `[PENDING: F17]` / team built SimpleAudit at SimulaMet | human team | Confirm true before release (FACT_CHECK_LIST F17 = UNVERIFIED). |
| `[PENDING: ORGANIZER]` (section 1) | — | REMOVED-as-superseded: there is no event form or challenge-area field; the focus area is stated in the presentation. |
| `[PENDING: P08 live]` (section 3) | P08 live runs (window 2026-10-10→23) | The **live** matched-budget numbers do not exist yet (live runs are scheduled, not executed — F26/F27). At release time they will almost certainly still be running, so state honestly: "the live matched-budget comparison is scheduled for the run window; the live arm, scorer and offline parity campaign are already built and tested." Do **not** invent live numbers, and do **not** present the offline parity numbers (F21/F23) as the live result. |
| `[PENDING: P11/external-reuse]` (section 5) | P11 ticket | Only claim external reuse if a real team used it; otherwise write "no external reuse yet (as of 2026-10-08)". |

**Now built and tested — no longer pending (do NOT re-mark as PENDING):**
- **Offline 4-arm parity campaign** (S0/S3/S4 + offline-S5, one shared envelope, `parity` report) —
  runnable now (F21/F23).
- **EESS vertical slice** (H_R/H_P/H_J, pre-outcome commit → real SimpleAudit execution → evidence
  re-rank) — runnable now, `scripts/demo_slice.py` → `DEMO OK` (F22).
- **Tox21 AR-agonist** deterministic secondary case (F24).
- **Oracle-gated scorer** `repliclaw.p08.score` + passing P02 replay self-test (F25).
- **Live-LLM arms** `repliclaw.eess_live` + live S4/S3/S0 (all six primary arms) — **implemented + contract-tested offline under
  a fake client** (F26). Say exactly that: *implemented + tested*, **not** "live runs executed."

If any of the now-built items regressed by release time, re-mark it honestly as in progress — but as
of 2026-10-09 (`repl-claw-dev` @ `945986f`) all are green in the 240/8 run-branch gate
(235/8 at A9 tip `3491032`) (F20).

**Rule:** a `[PENDING]` that cannot be resolved with a *verified* result must become an honest
"not yet measured / in progress" sentence — never a fabricated number.
✅ _all placeholders resolved or honestly reworded_

---

## Step 2 — Re-verify the test gates you will cite (run these, don't assume)

**Primary gate now lives on the run branch, not the module worktrees.** The presentation cites the
run-branch full gate (**240 passed, 8 skipped** at the run-branch tip `945986f`; 235/8 at A9
tip `3491032` — the current verified count, F20)
and the scorer self-test (F20/F25). Run **this first** — it is the number the draft actually makes:

```bash
cd /Users/sushantgautam/Documents/ScienceClawHackathon
git rev-parse --short HEAD          # expect 945986f (the current run-branch tip)

.venv/bin/python -m pytest -o addopts="" -q     # expect: 240 passed, 8 skipped (at 945986f; 235/8 at A9 tip 3491032)
.venv/bin/ruff check src tests scripts          # expect: All checks passed!
.venv/bin/python -m mypy src                    # expect: Success (source-file count grows as A8 lands)
.venv/bin/python -m repliclaw.p08.score --self-test   # expect: SELF-TEST: PASS (exit 0)
```

> **Re-run note (2026-10-08):** the gate was re-verified at `617b329` after the leak-guard
> (`ae68211`/`a934a48`), runner CLI (`d269a15`) and preflight gate 5 (`6a9f2b7`) merges — the
> count moved from 149/8 (54 files) at `1012ff7` to **202/8 (55 files)**; the run branch has
> since advanced (A4 merge `80a3f4e`, scorer-alignment `5967f24`, A8 amendment `d5c6701`,
> A8 merged `a708523`, A9 merged `3491032`) and the current verified count is
> **240/8 at the run-branch tip `945986f`** (235/8 at A9 tip `3491032`; the +5 are the
> campaign-harness tests in `tests/test_p08_campaign.py`) (F20; the 213/8 @ `d5c6701` count was
> independently confirmed by the science-judge re-run in
> `docs/fleet/reviews/SCIENCE-JUDGE-V12-SIGNOFF-NOT-APPROVE-20261008.md`).
> If the tip has moved again by release time (e.g. the campaign-harness commit lands), re-run
> this block there and trust the fresh number, not this one.

The per-module counts below (P02 78 / P03 73 / P04 74) are **historical module checkpoints**
cited in the draft for provenance; they still reproduce at their exact clean checkpoint commits,
but the run-branch gate above is the number to trust. **Check which commit you are on before
trusting a number** (`git rev-parse --short HEAD` on the run branch;
`git -C .worktrees/<n> rev-parse --short HEAD` for a module worktree).

```bash
cd /Users/sushantgautam/Documents/ScienceClawHackathon

# Sanity: confirm each worktree is at the expected commit and clean.
git -C .worktrees/p02 rev-parse --short HEAD   # expect 3f452b2
git -C .worktrees/p03 rev-parse --short HEAD   # expect ba71a4d
git -C .worktrees/p04 rev-parse --short HEAD   # expect 1b48ac2

# Per-module gate (use the per-worktree venv; do NOT use system python).
for wt in p02 p03 p04; do
  echo "=== .worktrees/$wt ==="
  ( cd ".worktrees/$wt" && \
    echo -n "  pytest: " && .venv/bin/python -m pytest 2>&1 | grep -E '[0-9]+ passed' | tail -1 && \
    echo -n "  ruff:   " && .venv/bin/ruff check src tests 2>&1 | tail -1 && \
    echo -n "  mypy:   " && .venv/bin/python -m mypy src 2>&1 | tail -1 )
done

# Expected at the checkpoint commits:
#   p02 -> 78 passed, 8 skipped | ruff: All checks passed! | mypy: 21 source files
#   p03 -> 73 passed, 8 skipped | ruff: All checks passed! | mypy: 20 source files
#   p04 -> 74 passed, 8 skipped | ruff: All checks passed! | mypy: 22 source files
```

The p07/p05/p08 branches have since been **merged into the run branch** (see the primary gate
above, `repl-claw-dev` @ `945986f`). The `.worktrees/p07` "112 passed @ 251dead" line from the
original checklist is **superseded** — run the primary gate above instead. If you must re-check a
specific module worktree, the per-module block above is still valid at its checkpoint commits.

Note: `-q` is already in each tree's `pyproject.toml` (`addopts`), so **do not add another `-q`**
— that suppresses the "N passed" summary line.
✅ _green output matches the table (or a newer, understood count)_

---

## Step 3 — Fact-check the draft once, top to bottom

1. For every `[F#]` tag in `DRAFT_ANSWERS.md`, confirm a matching row exists in
   `FACT_CHECK_LIST.md` and its status is `RE-VERIFIED` / `SOURCE-ONLY` (or you've explicitly
   accepted a `UNVERIFIED`/`NO-NETWORK` item for this release).
2. Grep for leftover scaffolding that must **not** reach the published text:

```bash
grep -nE '\[PENDING|\[F[0-9]+\]|<sub>|FACT_CHECK_LIST' docs/application/DRAFT_ANSWERS.md
```

Everything that hits must be handled: `[F#]` tags and `<sub>…</sub>` basis notes are **stripped**
before publishing (they are for the team, not the audience). `[PENDING]` tokens must be replaced
per Step 1.

✅ _no stray tags reach the final text_

---

## Step 4 — Assemble the final text

1. Copy each numbered section from `DRAFT_ANSWERS.md` **with the `<sub>…</sub>` basis lines and
   `[F#]` tags removed.**
2. Keep the **global honesty constraints** section's spirit (no firstness / superiority /
   reviewer-approval claims) — it is *not* published, but the body must already comply.
3. Confirm the body never says "first", "novel", "state of the art", "reviewer approved", or any
   winning/superiority claim. The only novelty wording allowed is the scoped: *"as of 2026-10-08,
   across the surveyed prior art, we are not aware of …; we do not claim firstness."*
4. Confirm the **tested-vs-executed** wording survived stripping: the live arm must read as
   "implemented + unit/contract-tested offline (no live run executed)", and the offline parity
   numbers must not be labelled as the live matched-budget result (A8 / F26 / F27).
5. Fill the **project title** (use the Naming block's fallback unless you pick a better one).
✅ _clean, release-ready text drafted_

---

## Step 5 — Prepare team materials

- **Biographies / profiles** for each named teammate (the draft's `[PENDING: TEAM]` spots).
- Confirm every listed capability is backed by a named, capable person.
- Keep team size / institution consistent with the biographies and the SimuMet AI Safety
  department attribution.
✅ _bios attached and consistent_

---

## Step 6 — Prepare the public repo, README, demo and evidence links

REMOVED-as-superseded: the old application-portal steps (check the
`scienceclawhack.ai/apply.html` form for field order/character limits, challenge-area
selection, organizer questions, and deadline) no longer apply — this is a public release, not a
form submission.

**Repo publish + evidence link:** use the **public** repo
`https://github.com/SushantGautam/RepliClaw`. Before sharing, confirm it is set to
**public** and pin the link to the **run branch `repl-claw-dev` at a specific commit** (as of this
rework, `945986f` — current verified gate 240/8 (235/8 at A9 tip `3491032`); re-run the Step-2
gate at the pinned SHA before
publishing) so the reader sees exactly what the test counts were measured on. The full
P02–P08 stack now lives on that branch; the old feature branches (`p02/…`, `p03/…`, `p04/…`,
`p07/integration`) are merged and historical. The README must state the project's focus:
decentralized scientific collectives for causal diagnosis of AI failures, and link the evidence
archive (see below).

**What to attach / point at as reproducible evidence (all runnable offline, 0-token, no key):**
- The **offline 4-arm parity campaign** (S0/S3/S4 + offline-S5 under one shared `BudgetEnvelope`,
  `parity` report) — see `src/repliclaw/comparators/runner.py` + `tests/test_comparators.py` (F21/F23).
- The **EESS slice demo** — `scripts/demo_slice.py` → `DEMO OK` + independent re-execution (F22).
- The **scorer self-test** — `.venv/bin/python -m repliclaw.p08.score --self-test` → `SELF-TEST: PASS` (F25).
- The **full run-branch gate** — `pytest`/`ruff`/`mypy` (240/8 @ `945986f`; 235/8 @ `3491032`) (F20).
Do **not** attach live-LLM run artifacts — none exist yet (live runs are scheduled, F26/F27).

**Release package (public):**
- **README** presenting the project as independent research (repo: `https://github.com/SushantGautam/RepliClaw`).
- **Demo video** (or recorded `scripts/demo_hero.py` session) of the one-command offline demo.
- **Evidence archive** link pinned to the run-branch SHA (artifacts under `artifacts/`).
- **License** file and a **citation** block (project name, authors, repository URL, commit SHA,
  date).
✅ _repo public; README/demo/evidence-archive/license/citation ready and pinned_

---

## Step 7 — Final pre-release review

- [ ] No `[PENDING]`, no `[F#]`, no `<sub>` tokens in the text you publish.
- [ ] Every number in the presentation matches a green row in `FACT_CHECK_LIST.md` (or is honestly
      marked "in progress / not yet measured").
- [ ] No firstness / superiority / approval / winning claims.
- [ ] Title, team names, and capabilities are consistent.
- [ ] Evidence/demo link is public and pinned.
- [ ] Someone who was **not** the one drafting re-reads it once.

✅ _review sign-off_

---

## Step 8 — Publish the release (human, in a browser — do not automate)

1. Set `https://github.com/SushantGautam/RepliClaw` to **public** and verify the run branch
   `repl-claw-dev` is pushed at the pinned commit.
2. Publish the assembled presentation text (README and any website/paper pages); add the demo
   video, evidence archive link, license, and citation block.
3. Double-check the rendered README/pages (no markdown artifacts, no stray tags).
4. **Save a release record** (date + pinned commit SHA) in `PROGRESS.md` so the citation and
   evidence links stay traceable.

✅ _released; record saved_

---

## Step 9 — If/when the live window is authorized (independent of the public release)

The live campaign is **scheduled** for the run window (2026-10-10 → 2026-10-23) and is **not**
part of release verification. It may only start under a **two-key start** (F27/F28): science-judge
approval of prereg **v1.1 + v1.2-AMENDMENT** (the amendment is DRAFT and unsigned — no live run on
v1.1 alone while it is unsigned) **and** human (project-lead) authorization, both recorded in
`EXECUTION_STATE.md`. **The science key is SATISFIED: sign-off round 3 (2026-10-09) =
APPROVE-WITH-CONDITIONS @ `c0e92ea`, and all round-3 conditions are met at `c0e92ea`**
(history: round 1 (2026-10-08) = NOT-APPROVE, raising BLOCKING item **RC-1** — P1 pair = S5
live-LLM vs S4 deterministic, a cross-executor comparison v1.1 §3.1 declares invalid — plus
RC-2/RC-3/RC-4 (`docs/fleet/reviews/SCIENCE-JUDGE-V12-SIGNOFF-NOT-APPROVE-20261008.md`; F30);
round 2 (2026-10-09) = NOT-APPROVE, finding the M-1 task-interface asymmetry). RC-1 was fixed by
amendment section **A8 (executor parity)**, **merged @ `a708523`** (code-judge MERGE-OK; F31/F32);
M-1 was fixed by amendment section **A9**, **merged @ `3491032`** (code-judge MERGE-OK; 8 new
tests in `tests/test_r2_parity.py`; F33). The two-key requirement is **unchanged and not
weakened**: round-3 science sign-off (satisfied @ `c0e92ea`) + human (project-lead)
authorization, both recorded in `EXECUTION_STATE.md`. The **human two-key authorization is the
only true remaining blocker** (external); before the window opens, the **R-2 S4/S3/S0
live-token floors** must also be measured
(`docs/experiments/R2_TOKEN_FLOOR_PREFLIGHT_PROTOCOL.md`). If the human key is in place at
window start:

1. **Pre-flight (all must be green before run 1):** the primary run-branch gate (F20), the scorer
   `--self-test` (F25), P02 leakage test, the P05 parity suite (F23), and — before the window can
   open — the **R-2 S4/S3/S0 live-token floors** measured and recorded
   (`docs/experiments/R2_TOKEN_FLOOR_PREFLIGHT_PROTOCOL.md`), plus the
   **round-3 v1.2-AMENDMENT science-judge sign-off on A1–A9** (satisfied @ `c0e92ea`;
   F25/F27/F28/F33).
   Already landed and pinned: the A4 evidence-in-verdict-prompt fix (merged `80a3f4e`,
   code-judge MERGE-OK 10/10 per `docs/fleet/reviews/CODE-JUDGE-A4-PROMPT-EVIDENCE-20261008.md`),
   the measured live token floor (§5.1 filled; `artifacts/p08/live_token_floor/`),
   the `score.py` P1-rule alignment to the v1.2 canonical rule (merged `5967f24`, code-judge
   MERGE-OK, F25), the runner CLI, same-task `case_loader`, usage-invalidation and the D-10
   hyperparameter pin (λ=μ=0.5, max_cycles=6, offer TTL=120s) (`d269a15`);
   `experiments/policy_rag/preflight.sh` runs all 5 gates (including the runner CLI smoke, gate 5,
   added at `6a9f2b7`).
2. **Run the preregistered arms** (S5 live EESS, S3 adaptive central, S4 open-sharing, S0
   single-agent, and the A1 no-escrow / A3 random-select ablations) under the shared frozen
   `BudgetEnvelope`, same task/case/oracle. **Per A8 (merged @ `a708523`; F31), all SIX primary
   arms run as LIVE LLM arms on the same `LLMConfig`+`harness_seed`** (S0 `single_agent`,
   S3 `adaptive_central`, S4 `open_sharing_swarm`, S5 `eess`, A1 `eess_no_escrow`,
   A3 `eess_random_select` — all six in `LIVE_KEYS`, `runner.py`; the P1 pair is S5 vs S4 with
   the SAME executor / identical envelope). The arms
   already exist on the run branch (`repliclaw.eess_live` + `comparators`) and are contract-tested
   offline (F26); the runner CLI wires them to a real client under the shared envelope.
3. **Score with the oracle-gated scorer** (`repliclaw.p08.score`) → scorecard; it reads the oracle
   only after every run dir is verified complete (F25).
4. **Report the live matched-budget result honestly** — including null/negative results — and
   record any mid-window changes as prereg amendments, not silent edits.
5. If any pre-flight item is still red — **including the R-2 S4/S3/S0 live-token floors not
   measured, or the human two-key authorization not recorded** — **do not start live runs**; run
   the offline parity campaign + slice + scorer self-test as the demonstrable offline evidence
   instead, and say so.

**Do NOT** present live results as if they exist. The window runs 2026-10-10 → 2026-10-23;
complete *scored* live results will not be available before the window ends (2026-10-23). If the
public release happens before the window closes, live numbers will be `[PENDING: P08 live]` —
report the offline evidence (F20–F26) and say the live comparison is scheduled (and that sign-off
rounds 1 and 2 were NOT-APPROVE, fixed by A8 @ `a708523` and A9 @ `3491032`, and round 3 =
APPROVE-WITH-CONDITIONS @ `c0e92ea` — F30–F33).
✅ _live runs executed only under two-key authorization (round-3 science sign-off — satisfied @ `c0e92ea` — + human key), or offline evidence reported instead_

---

## Do NOT

- Do **not** run a live model or make network calls as part of *release verification* —
  verification is the offline pytest/ruff/mypy + scorer self-test gates above. (A live run is a
  *separate, authorized run-window* action under Step 9's two-key start, not a verification step.)
- Do **not** write "implemented + tested" as "live runs executed" for the live arm (A8 / F26).
- Do **not** paste the offline parity numbers (F21/F23) as the live matched-budget result.
- Do not `git add -A` or commit this presentation package on behalf of other workers; this package
  is owned under `docs/application/**` and is committed by the orchestrator.
- Do not claim novelty, reviewer approval, or competition success anywhere in the presentation.
