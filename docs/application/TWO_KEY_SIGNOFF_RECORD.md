# RepliClaw — Two-Key Sign-Off Record (MUST M7)

This document is the **two-key start record** required by the prereg
(`PREREG-2026-10-v1.2-AMENDMENT.md` §9 and v1.1 §9.2) and by science-judge MUST item
**M7** (`SCIENCE-JUDGE-CAMPAIGN-RESULTS-20261009.md`): *"the run must not be treated as
fully authorized until the two-key record is produced."*

The prereg §9 **Sign-off 2 (Human operator)** row is intentionally left blank in the
frozen amendment (it is a signature line the human operator fills by hand; the frozen
document is not edited by the orchestrator). This record captures the **actual**
authorization events from the session so the two-key gate is verifiable from artifacts.
Nothing here is a fabricated signature — each human line is the verbatim statement the
human made, with timestamp and scope as recorded at the time.

---

## Key 1 — Independent science judge (SATISFIED)

- **Name:** Independent RepliClaw Science Judge (VS Code background agent, read-only) — agent `713aa9b8-ae26-46ec-8980-0f1b160d764b`
- **Round:** 3 (on amendments A1–A9)
- **Report:** `docs/reviews/SCIENCE-JUDGE-A1-A9-ROUND3-APPROVE-WITH-CONDITIONS-20261009.md`
- **Date:** 2026-10-09
- **Verdict:** **APPROVE-WITH-CONDITIONS** — the SCIENCE KEY for the two-key live-run gate is SATISFIED. Rounds 1–2 = NOT-APPROVE (driven by RC-1, then M-1); both resolved and independently reproduced before round 3.
- **Conditions (MUST, pre-live):** (1) disclosures folded into the application before any P1 result is reported; (2) R-2 token floors measured + committed pre-window; (3) human two-key authorization (independent of this science key).
- **Post-live re-review:** `docs/reviews/SCIENCE-JUDGE-CAMPAIGN-RESULTS-20261009.md` — **APPROVE-WITH-CONDITIONS** on the actual 120-run result (P1 statistic valid + prereg-consistent; bootstrap independently reproduced bit-for-bit). BLOCKING B1 (attribution) + B2 (M3 schema artifact) — **B2 remediated** by the `severity` scorer fix; B1 enforced by the result statement below. MUST M1–M7 (incl. this M7 record).

## Key 2 — Human operator (SATISFIED)

- **Role:** Project lead; holds one of the two start keys per v1.1 §9.2.
- **Authorization 1 — pre-flight test scope** (recorded 2026-10-09T12:56 local):
  > "I authorize test — USE sigma2 endpoint for test!"
  - Scope: the R-2 pre-flight live measurement (3 arms × 1 run per `R2_TOKEN_FLOOR_PREFLIGHT_PROTOCOL.md`), NOT the 120-run campaign. Consumed by the R-2 pre-flight run (`artifacts/p08/token_floor_r2_20261009T105739Z/`, `floor_r2.json` verdict OK).
- **Authorization 2 — FULL-EXPERIMENT scope** (recorded 2026-10-09T14:25 local):
  > "i do full-experiment authorization!!"
  - Scope: the **full 120-run live campaign** on the sigma2 `Qwen3.8-27B` endpoint, superseding the test-scope key. Consumed by the launch of `runs/p08-live-20261009T122444Z/`.
- **Scope interpretation note (for the record):** the two authorizations were distinct — the first covered the pre-flight test only; the second (14:25 local) explicitly escalated to the full experiment. The 120-run campaign launched **after** Authorization 2, with both the science key (round 3) and the human full-experiment key in hand.

---

## Two-key gate — satisfied (2026-10-09)

| Gate item | Status | Evidence |
|---|---|---|
| A1+A2+A3+A4+A7+A8+A9 signed by science judge | ✅ | round-3 report (above) |
| Mandated code merged + green | ✅ | A8 @ `a708523`, A9 @ `3491032`, R-2 @ `79c8f7a`; gate 248 passed/8 skipped pre-launch |
| Pre-flight FakeLLM six-arm parity re-run (C7) | ✅ | recorded pre-window |
| R-2 live token floors measured + committed | ✅ | `floor_r2.json` (S4 16,300 / S3 15,993 / S0 8,588; max fraction 0.2717 < 0.60) |
| R-1 pin run tree to actual HEAD | ✅ | preflight ALL 5 GATES PASS, printed pin = actual HEAD at launch |
| **Science key** (Sign-off 1) | ✅ | APPROVE-WITH-CONDITIONS, round 3 |
| **Human key** (Sign-off 2) | ✅ | verbatim authorizations 1 + 2 (above) |

**Result:** both keys were in hand before the 120-run campaign launched. This record
closes MUST M7. The frozen prereg §9 Sign-off 2 signature line remains blank by design
(the human fills it by hand); this document is the artifact-level record of the
authorization.

**Provenance (for the public claim):** the campaign spans three run-start HEADs
(`de77fba` n=7, `484dc66` n=44, `1df4c71` n=69). `git diff de77fba..1df4c71 -- scripts src tests`
is **EMPTY** (docs-only), so the public claim cites the code-identical range
`de77fba..1df4c71`, not a single pin. Per-run `run_metadata.json.tree_sha` is the
authoritative per-run code identity.
