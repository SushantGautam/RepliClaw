# P09 — Submission Checklist (for the human team)

Everything a human must do to turn `DRAFT_ANSWERS.md` into a submitted application.
**Deadline: 2026-10-16** (event window Oct 30 – Nov 1; decisions ~Oct 19 — per
`docs/APPLICATION_V2.md` @ `1fe944c`; **re-confirm dates on the official site**).

Do the steps **in order**. Each step ends with ✅ when done.

---

## Step 0 — Read the two companion docs first (5 min)

1. Open `FACT_CHECK_LIST.md`. It lists every claim (F1–F17, F19) with its source + status, plus
   a **critical test-count discrepancy** (P09 re-verified **78 / 73 / 74**, not the 62 / 69 / 74
   the checkpoint docs record).
2. Decide, as a team, whether to (a) cite the **re-verified 78 / 73 / 74** (recommended — they
   reproduce on a clean re-run today) or (b) fix CP-P02/CP-P03 at the source and keep 62 / 69.
   Whichever you choose, DRAFT_ANSWERS.md and the checklist must agree.
✅ _decision recorded_

---

## Step 1 — Resolve every `[PENDING: …]` placeholder

Find them all: `grep -n 'PENDING' docs/application/DRAFT_ANSWERS.md`

| Placeholder | Who resolves | What to do |
|---|---|---|
| `[PENDING: TEAM]` (Fields 2, 4) | human team | Insert real names, roles, and confirm each Field-4 capability box is true. **Tick only boxes you can stand behind** — the draft already warns against over-ticking. |
| `[PENDING: F17]` / team built SimpleAudit at SimulaMet | human team | Confirm true before submit (FACT_CHECK_LIST F17 = UNVERIFIED). |
| `[PENDING: ORGANIZER]` (Field 1) | human + form | Pick the challenge area on the live form (see Step 6 questions). |
| `[PENDING: P05/P08]` (matched-budget numbers) | P05 + P08 tickets | **Only fill once P05/P08 are DONE and the numbers exist.** If still running at submit time, state honestly: "matched-budget comparison is in progress; the mechanism is implemented and the comparison will be reported at the event." Do **not** invent numbers. |
| `[PENDING: P06]` (secondary held-out case) | P06 ticket | Same rule — only fill when the case exists and is verified. |
| `[PENDING: P07]` (wired end-to-end run) | P07 ticket | Only fill when the wired run is committed + verified. |
| `[PENDING: P08]` (token/cost metering, live model) | P08 ticket | Same rule. |
| `[PENDING: P11/external-reuse]` (Field 5) | P11 ticket | Only claim external reuse if a real team used it; otherwise write "no external reuse yet (as of 2026-10-08)". |

**Rule:** a `[PENDING]` that cannot be resolved with a *verified* result must become an honest
"not yet measured / in progress" sentence — never a fabricated number.
✅ _all placeholders resolved or honestly reworded_

---

## Step 2 — Re-verify the test gates you will cite (run these, don't assume)

Counts below are what P09 reproduced on **2026-10-08 at the exact clean checkpoint commits**.
If the orchestrator has merged the branches into `repl-claw-dev`/p07 since then, the merged tree
will differ — that is expected (see the merged-tree row). **Check which commit you are on before
trusting a number** (`git -C .worktrees/<n> rev-parse --short HEAD`).

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

Optional — the **merged** tree (only if p07 integration has been merged/advanced):

```bash
# The merged p07 tree (base + p02+p03+p04+p05) currently shows:
( cd .worktrees/p07 && .venv/bin/python -m pytest 2>&1 | grep -E '[0-9]+ passed' | tail -1 )
#   P09 observed 112 passed, 8 skipped at 251dead (2026-10-08). Count will change as P05–P08 land.
```

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
4. Fill the **project title** (use the Naming block's fallback unless you pick a better one).
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
**public** and that the branch/commit you point to contains the code (feature branches
`p02/…`, `p03/…`, `p04/…`, and `p07/integration`). Pin the link to a specific commit so the
reviewer sees exactly what the test counts were measured on.
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

## Do NOT

- Do not run a live model or make network calls as part of "verifying" — verification is the
  pytest/ruff/mypy gates above (offline).
- Do not `git add -A` or commit this application on behalf of other workers; this package is
  owned under `docs/application/**` and is committed by the orchestrator.
- Do not claim novelty, reviewer approval, or competition success anywhere in the submission.
