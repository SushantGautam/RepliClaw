# RepliClaw — Progress Log

Append-only. Each entry: what changed / commands run / observed result / artifacts / next action.

## 2026-10-07 — M0 reconnaissance complete
- What changed: Established durable state (`EXECUTION_STATE.md`), git baseline (branch `repl-claw-dev`), and the reuse matrix + 8 decisions in `DECISIONS.md`.
- Commands/evidence:
  - LLM endpoint probe: `POST https://simulachat.sushant.pp.ua/api/v1/chat/completions` model=`default` → correct t-test answer; `usage {prompt:71, completion:66}`; HTTP 200, <1s.
  - ScienceClaw import probe: `artifacts.artifact`, `artifacts.needs`, `artifacts.reactor` import in 0.09s (stdlib+pydantic only); `core.skill_registry.get_registry()` → 334 skills, 0.58s.
  - `ArtifactStore` hardcodes `~/.scienceclaw` (artifact.py:593); `rank_needs` hardcodes `~/.scienceclaw/artifacts` (pressure.py:199) → run-local subclass required.
  - SimpleAuditStudio = Django + hatchet-sdk + postgres; `audits/agentic/schema_v2.py` absent → OTLP integration target, not a core dependency.
  - `score_need = 2*novelty + 1*centrality + 0.5*depth + 0.2*log1p(age_min)` (pressure.py:197).
- Result: Substrate confirmed import-safe; reuse-first path viable without forking ScienceClaw.
- Artifacts: `/tmp/scienceclaw-upstream` (upstream checkout), `DECISIONS.md`.
- Next: Scaffold `repliclaw` package + vendored ScienceClaw; M1 domain model + vertical smoke.

## 2026-10-07 — M1–M4 core built + 3-way verdict path VERIFIED (offline, hermetic)
- What changed: Full `src/repliclaw/` package (canonical, models, runstore, isolation, scienceclaw_adapter, investigators, evidence, verdict, protocol) + vendored `deps/scienceclaw/{artifacts,core}` + pyproject + 3 known-answer fixtures. Tuned `insufficient_evidence` (a directional+executable piece is sufficient) and the conflict gate (a decisive executable follow-up ADJUDICATES a surviving independent conflict → recovery, AC12).
- Commands/evidence:
  - `python artifacts/dev/e2e_3way.py` (deterministic backend, no network):
    - clean_supported → **SUPPORTED** conf 0.98 (3 support/0 contradict, no conflict).
    - clean_refuted → **REFUTED** conf 0.534 (single directional-executable falsifier is now sufficient; replication need fired).
    - misleading_wrong_test → **REFUTED** conf 0.256 (2 support vs falsifier → independent conflict → falsifier-lens follow-up adjudicates → recovery AC12; conflict surfaced + broken).
  - Confidence ordering well-calibrated: 0.98 > 0.534 > 0.256 (clean > clean-null > recovered-misleading).
  - Earlier (same milestone): commit→reveal→tamper→replay→record-tamper integrity cycle passes (AC04); one-shot reveal blocks re-reveal after rejection (fake-independence hole closed).
- Result: The full blind→commit→reveal→evidence→followup→verdict loop is executable and produces correct, evidence-calibrated verdicts for supported / refuted / misleading paths, fully offline.
- Artifacts: `artifacts/dev/e2e_3way.py`, `tests/fixtures/*.json`, `src/repliclaw/*`.
- Next: formal pytest suite (AC14/15) → M5 strategies baselines → M6 benchmark → M8 CLI → M9 live-LLM demo → M10 harden + COMPLETE.
