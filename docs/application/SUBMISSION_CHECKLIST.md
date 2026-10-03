# P09 — Submission Checklist (for the human team)

Everything a human must do to turn `DRAFT_ANSWERS.md` into a submitted application.
**Deadline: 2026-10-16** (event window Oct 30 – Nov 1; decisions ~Oct 19 — per
`docs/APPLICATION_V2.md` @ `1fe944c`; **re-confirm dates on the official site**).

Do the steps **in order**. Each step ends with ✅ when done.

---

## Step 0 — Read the two companion docs first (5 min)

1. Open `FACT_CHECK_LIST.md`. It lists every claim with its source + status: **F1–F17/F19** (the
   historical per-module checkpoints P02/P03/P04 + G0 + prior art/team/rubric) and **F20–F29**
   (the run-branch state: 149/8 full gate, offline 4-arm parity campaign, EESS slice, Tox21 case,
   oracle-gated scorer + passing self-test, live arm *implemented + tested*, live window, novelty
   positioning). It also records a **critical test-count discrepancy** (P09 re-verified the
   historical module counts **78 / 73 / 74**, not the 62 / 69 / 74 the old checkpoint docs record).
2. Note the distinction that carries the whole application: **offline** (runnable now) vs
   **implemented + tested** (the live arm) vs **scheduled live** (not yet executed). The headline
   live matched-budget result is `[PENDING: P08 live]`; the offline parity numbers are feasibility
   evidence only, not the live result.
✅ _discrepancy + tested-vs-executed distinction understood_

---

## Step 1 — Resolve every `[PENDING: …]` placeholder

Find them all: `grep -n 'PENDING' docs/application/DRAFT_ANSWERS.md`

| Placeholder | Who resolves | What to do |
|---|---|---|
| `[PENDING: TEAM]` (Fields 2, 4) | human team | Insert real names, roles, and confirm each Field-4 capability box is true. **Tick only boxes you can stand behind** — the draft already warns against over-ticking. |
| `[PENDING: F17]` / team built SimpleAudit at SimulaMet | human team | Confirm true before submit (FACT_CHECK_LIST F17 = UNVERIFIED). |
| `[PENDING: ORGANIZER]` (Field 1) | human + form | Pick the challenge area on the live form (see Step 6 questions). |
| `[PENDING: P08 live]` (Field 3) | P08 live runs (window 2026-10-10→23) | The **live** matched-budget numbers do not exist yet (live runs are scheduled, not executed — F26/F27). At submit time (deadline 2026-10-16) they will almost certainly still be running, so state honestly: "the live matched-budget comparison is scheduled for the run window; the live arm, scorer and offline parity campaign are already built and tested." Do **not** invent live numbers, and do **not** paste the offline parity numbers (F21/F23) as the live result. |
| `[PENDING: P11/external-reuse]` (Field 5) | P11 ticket | Only claim external reuse if a real team used it; otherwise write "no external reuse yet (as of 2026-10-08)". |

**Now built and tested — no longer pending (do NOT re-mark as PENDING):**
- **Offline 4-arm parity campaign** (S0/S3/S4 + offline-S5, one shared envelope, `parity` report) —
  runnable now (F21/F23).
- **EESS vertical slice** (H_R/H_P/H_J, pre-outcome commit → real SimpleAudit execution → evidence
  re-rank) — runnable now, `scripts/demo_slice.py` → `DEMO OK` (F22).
- **Tox21 AR-agonist** deterministic secondary case (F24).
- **Oracle-gated scorer** `repliclaw.p08.score` + passing P02 replay self-test (F25).
- **Live-LLM arm** `repliclaw.eess_live` (S5/A1/A3) — **implemented + contract-tested offline under
  a fake client** (F26). Say exactly that: *implemented + tested*, **not** "live runs executed."

If any of the now-built items regressed by submit time, re-mark it honestly as in progress — but as
of 2026-10-08 (`repl-claw-dev` @ `1012ff7`) all are green in the 149/8 run-branch gate (F20).

**Rule:** a `[PENDING]` that cannot be resolved with a *verified* result must become an honest
"not yet measured / in progress" sentence — never a fabricated number.
✅ _all placeholders resolved or honestly reworded_

---

## Step 2 — Re-verify the test gates you will cite (run these, don't assume)

**Primary gate now lives on the run branch, not the module worktrees.** The application cites the
run-branch full gate (149 passed, 8 skipped; ruff clean; mypy clean, 54 files) and the scorer
self-test (F20/F25). Run **this first** — it is the number the draft actually makes:

```bash
cd /Users/sushantgautam/Documents/ScienceClawHackathon
git rev-parse --short HEAD          # expect 1012ff7 (or the current run-branch tip)

.venv/bin/python -m pytest -o addopts="" -q     # expect: 149 passed, 8 skipped
.venv/bin/ruff check src tests scripts          # expect: All checks passed!
.venv/bin/python -m mypy src                    # expect: Success: no issues found in 54 source files
.venv/bin/python -m repliclaw.p08.score --self-test   # expect: SELF-TEST: PASS (exit 0)
```

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
above, `repl-claw-dev` @ `1012ff7`). The `.worktrees/p07` "112 passed @ 251dead" line from the
original checklist is **superseded** — run the primary gate above instead. If you must re-check a
specific module worktree, the per-module block above is still valid at its checkpoint commits.

Note: `-q` is already in each tree's `pyproject.toml` (`addopts`), so **do not add another `-q`**
— that suppresses the "N passed" summary line.
✅ _green output matches the table (or a newer, understood count)_

---

## Step 3 — Fact-check the draft once, top to bottom

1. For every `[F#]` tag in `DRAFT_ANSWERS.md`, confirm a matching row exists in
   `FACT_CHECK_LIST.md` and its status is `RE-VERIFIED` / `SOURCE-ONLY` (or you've explicitly
   accepted a `UNVERIFIED`/`NO-NETWORK` item for this submission).
2. Grep for leftover scaffolding that must **not** reach the form:

```bash
grep -nE '\[PENDING|\[F[0-9]+\]|<sub>|FACT_CHECK_LIST' docs/application/DRAFT_ANSWERS.md
```

Everything that hits must be handled: `[F#]` tags and `<sub>…</sub>` basis notes are **stripped**
before pasting (they are for the team, not the reviewer). `[PENDING]` tokens must be replaced per
Step 1.

✅ _no stray tags reach the final text_

---

## Step 4 — Assemble the final text

1. Copy each Field from `DRAFT_ANSWERS.md` **with the `<sub>…</sub>` basis lines and `[F#]` tags
   removed.**
2. Keep the **global honesty constraints** section's spirit (no firstness / superiority /
   reviewer-approval claims) — it is *not* pasted, but the body must already comply.
3. Confirm the body never says "first", "novel", "state of the art", "reviewer approved", or
   "will win". The only novelty wording allowed is the scoped: *"as of 2026-10-08, across the
   surveyed prior art, we are not aware of …; we do not claim firstness."*
4. Confirm the **tested-vs-executed** wording survived stripping: the live arm must read as
   "implemented + unit/contract-tested offline (no live run executed)", and the offline parity
   numbers must not be labelled as the live matched-budget result (A8 / F26 / F27).
5. Fill the **project title** (use the Naming block's fallback unless you pick a better one).
✅ _clean, submission-ready text drafted_

---

## Step 5 — Attach team materials

- **Biographies / profiles** for each named teammate (the draft's `[PENDING: TEAM]` spots).
- Confirm every Field-4 capability box is backed by a named, capable person.
- If the form asks for team size / institution, make it consistent with the biographies.
✅ _bios attached and consistent_

---

## Step 6 — Prepare answers for the official form / organizer

Check the live form (`scienceclawhack.ai/apply.html`) for: exact field order, character limits,
required media (video? demo link? slides?), and whether a **challenge area** is a real field.
Recommended questions to the event (email/form) if anything is unclear:

1. Which challenge area / track does this submission fall under?
2. Are all five fields in the brief required, or only the three long-form answers?
3. Is a live demo / video link mandatory by 2026-10-16, or can it be a link that updates later?
4. Confirm the exact application deadline (date + timezone) and the decisions date.
5. Is a public repo + reproducible-run link the expected "evidence" link?

**Demo / evidence link:** use the **public** repo
`https://github.com/SushantGautam/ScienceClawHackathon`. Before sharing, confirm it is set to
**public** and pin the link to the **run branch `repl-claw-dev` at a specific commit** (as of this
rework, `1012ff7`) so the reviewer sees exactly what the test counts were measured on. The full
P02–P08 stack now lives on that branch; the old feature branches (`p02/…`, `p03/…`, `p04/…`,
`p07/integration`) are merged and historical.

**What to attach / point at as reproducible evidence (all runnable offline, 0-token, no key):**
- The **offline 4-arm parity campaign** (S0/S3/S4 + offline-S5 under one shared `BudgetEnvelope`,
  `parity` report) — see `src/repliclaw/comparators/runner.py` + `tests/test_comparators.py` (F21/F23).
- The **EESS slice demo** — `scripts/demo_slice.py` → `DEMO OK` + independent re-execution (F22).
- The **scorer self-test** — `.venv/bin/python -m repliclaw.p08.score --self-test` → `SELF-TEST: PASS` (F25).
- The **full run-branch gate** — `pytest`/`ruff`/`mypy` (149/8) (F20).
Do **not** attach live-LLM run artifacts — none exist yet (live runs are scheduled, F26/F27).
✅ _questions asked (or confirmed from the form); demo link ready and public_

---

## Step 7 — Final pre-submit review

- [ ] No `[PENDING]`, no `[F#]`, no `<sub>` tokens in the text you paste.
- [ ] Every number in the submission matches a green row in `FACT_CHECK_LIST.md` (or is honestly
      marked "in progress / not yet measured").
- [ ] No firstness / superiority / approval / winning claims.
- [ ] Title, team names, and boxes are consistent.
- [ ] Evidence/demo link is public and pinned.
- [ ] Someone who was **not** the one drafting re-reads it once.

✅ _review sign-off_

---

## Step 8 — Submit (human, in a browser — do not automate)

1. Open `scienceclawhack.ai/apply.html` in a browser (the draft's notes are not a network action;
   only a human completes this step).
2. Paste the assembled text into the matching fields; attach bios/media.
3. Select the challenge area (or leave as the form defaults if Step 6 got an answer).
4. Double-check the rendered submission (no markdown artifacts, no stray tags).
5. Submit **before 2026-10-16** (leave margin — don't submit on the deadline hour).
6. **Save the confirmation / receipt** (email or screenshot) to a **private** location; do not
   paste it into the repo.

✅ _submitted; receipt saved privately_

---

## Step 9 — If/when the live window is authorized (event-time, AFTER submission)

The live campaign is **scheduled** for the run window (2026-10-10 → 2026-10-23) and is **not**
part of application verification. It may only start under a **two-key start** (F27/F28): science-judge
approval of prereg v1.1 **and** human (project-lead) authorization, both recorded in
`EXECUTION_STATE.md`. If both keys are in place at the event:

1. **Pre-flight (all must be green before run 1):** the primary run-branch gate (F20), the scorer
   `--self-test` (F25), P02 leakage test, the P05 parity suite (F23), and — before the window can
   open — the in-flight pieces must be landed and pinned: the runner CLI, the same-task
   `case_loader`, usage-invalidation, the D-10 hyperparameter pin (λ=μ=0.5, max_cycles=6, offer
   TTL=120s), and a measured live token floor committed to git (F27).
2. **Run the preregistered arms** (S5 live EESS, S3 adaptive central, S4 open-sharing, S0
   single-agent, and the A1 no-escrow / A3 random-select ablations) under the shared frozen
   `BudgetEnvelope`, same task/case/oracle. The arms already exist on the run branch
   (`repliclaw.eess_live` + `comparators`) and are contract-tested offline (F26); the runner CLI
   wires them to a real client under the shared envelope.
3. **Score with the oracle-gated scorer** (`repliclaw.p08.score`) → scorecard; it reads the oracle
   only after every run dir is verified complete (F25).
4. **Report the live matched-budget result honestly** — including null/negative results — and
   record any mid-window changes as prereg amendments, not silent edits.
5. If any pre-flight item is still red, **do not start live runs**; run the offline parity
   campaign + slice + scorer self-test as the demonstrable offline evidence instead, and say so.

**Do NOT** present live results in the application if they do not yet exist. The window runs
2026-10-10 → 2026-10-23 and the application deadline is 2026-10-16 — so even once the window has
started, complete *scored* live results will not be available before the deadline (the window ends
2026-10-23). Live numbers will almost certainly be `[PENDING: P08 live]` at submit time; report the
offline evidence (F20–F26) and say the live comparison is scheduled.
✅ _live runs executed only under two-key authorization, or offline evidence reported instead_

---

## Do NOT

- Do **not** run a live model or make network calls as part of *application verification* —
  verification is the offline pytest/ruff/mypy + scorer self-test gates above. (A live run is a
  *separate, authorized event-time* action under Step 9's two-key start, not a verification step.)
- Do **not** write "implemented + tested" as "live runs executed" for the live arm (A8 / F26).
- Do **not** paste the offline parity numbers (F21/F23) as the live matched-budget result.
- Do not `git add -A` or commit this application on behalf of other workers; this package is
  owned under `docs/application/**` and is committed by the orchestrator.
- Do not claim novelty, reviewer approval, or competition success anywhere in the submission.
