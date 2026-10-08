# EESS minimal interface contracts v0.1 (frozen 2026-10-08)

Frozen BEFORE parallel editing (P02/P03/P04 worktrees). Superseded only by a
numbered revision recorded in DECISIONS.md. Every builder codes to this file;
deviations require orchestrator sign-off. Source docs:
docs/EVIDENCE_ESCROW_SWARM.md, docs/EXPERIMENT_PROTOCOL_V2.md (artifact
contract), docs/FLAGSHIP_CASE.md (hero case), docs/design/NEED_DISPATCH.md
(F04 design, already merged — P04 implements it).

## 1. Prediction packet + escrow commitment (P03)
Canonical JSON, `schema: "repliclaw.prediction_packet/v1"`:
- packet_id (str, uuid4 hex), case_id, agent_id,
- hypothesis_id (e.g. "H_R"), hypothesis_version (int >= 1),
- hypothesis_statement (falsifiable sentence),
- intervention_id (e.g. "I_R"), predicted_outcome (concrete observable),
- refutation_criterion (concrete observable that would refute),
- estimated_cost {tokens: int|None, wall_s: float},
- competing_explanation (str), prior_evidence_snapshot_sha256 (str).
Canonical form: `json.dumps(obj, sort_keys=True, separators=(",", ":"))`, UTF-8.
**Commitment** = SHA-256 of the canonical bytes. `commitments.jsonl` (append-only):
{packet_id, agent_id, case_id, commitment_sha256, committed_at (ISO UTC), phase}.
**Reveal** (post phase-boundary): publish full packet; verification =
recomputed canonical hash == commitment. A mismatch is an INTEGRITY event,
never silently repaired. Public content before reveal is ONLY
(packet_id, commitment_sha256, committed_at, agent_id, hypothesis_id,
intervention_id) — never statement/prediction.

## 2. Events (events.jsonl, all phases)
{seq: int strictly monotonic, ts: ISO UTC, phase: str, worker_id: str,
kind: str, payload: object}. Kinds v1: commitment, reveal, reveal_verified,
reveal_mismatch, run_started, run_completed, run_failed, evidence_published,
need_published, need_claimed, need_released, need_expired, choice_ranked,
choice_changed, abstained, resolved, budget_exhausted.
Files are append-only; a crashed writer must not rewrite history.

## 3. Evidence observation (shared ledger)
{observation_id, case_id, producer_id, run_id, kind: "verified_run"|"derived",
summary (str), data: object (machine outputs only), provenance:
{intervention_id, config_sha256, run_hash, reproducible: bool,
independent: bool}, published_at, status: "public"|"retracted"}.
Only objective runner output may enter `data`; interpretations stay in
hypothesis revisions, never in `data`.

## 4. Need + atomic lease (P04; implements NEED_DISPATCH.md M1–M7)
Need {need_id, schema "repliclaw.need/v1", case_id, title, description,
proposer_id, proposed_at, required_capability, cost_estimate, status:
open|leased|done|cancelled|expired, lease: {holder_id, acquired_at,
expires_at, generation} | null}.
Claim = O_EXCL file create of `state/needs/<need_id>.lock` (atomic,
cross-process); expiry = monotonic deadline; retry = new generation on
expired lease. The broker ENFORCES lease/dedup/budget only — it NEVER ranks
scientific options or assigns questions; agents propose/rank themselves.

## 5. Counterfactual run (P02)
Interface: `run_case(case: CaseSpec, intervention: InterventionSpec,
seed: int, out_root: Path) -> InterventionRun`.
InterventionRun fields: run_id, case_id, intervention_id, case_sha256
(frozen case bytes), config_sha256 (scenario + target spec + judge spec +
intervention spec), model_id (e.g. "deterministic-rag-assistant/v1"),
seed, engine {name: "simpleaudit", version, git_sha}, started_at,
finished_at, target_output (str), conversation (trace list), judgment
(object), severity (str), token_counts, exit_code, stdout_log, artifact_hashes.
Persisted under `artifacts/science/<run_id>/interventions/<intervention_id>/`
with `manifest.json` per EXPERIMENT_PROTOCOL_V2.
**Replay rule**: same (case_sha256, config_sha256, seed) must yield
byte-identical target_output + hashes. **Single-factor rule**: each
intervention spec differs from the base case in exactly ONE declared factor
(retrieved context / policy-conflict rendering / judge reference rubric /
model prompt) — asserted in a test.

## 6. Leakage rules (ALL builders, enforced by tests)
Oracle fields (`true_cause`, `seeded_fault`, `reference_truth`,
evaluator notes) live ONLY in `oracle.json` under the sealed evaluator path
(`experiments/<case>/oracle/`), excluded from case files, investigator
prompts, intervention configs, target inputs, agent-visible tool outputs,
and logs. A judge-reference RUBRIC is a legitimate intervention variable
(I_J) and is labeled as such — it is not oracle leakage because the
intervention itself is the public experiment. Tests must prove none of the
oracle keys appear in investigator-visible artifacts (grep-level negative
test over the artifact tree).

## 7. Artifact layout (per run) — from EXPERIMENT_PROTOCOL_V2
`artifacts/science/<run_id>/{manifest.json, events.jsonl, claims.jsonl,
interventions/<intervention_id>/{config.json, inputs/, outputs/, stdout.log,
stderr.log, hashes.json}, metrics.json, comparison.md}`.
