"""G3 pilot driver — V3 track-O-R (RCAEval) stage-2 pilot execution CLI.

Implements the G3 pilot driver over the W3a/W3b telemetry modules
(``repliclaw.experiments.v3.telemetry`` / ``telemetry_arms``):

* frozen 10-case pilot roster (opaque ids RCA-P-01..10, assigned by the registry in sorted
upstream-id order — the registry is the single mapping authority), k=2 seeds
  {20261011, 20261012}, 2 arms (D-E-TELEM, C-EQ-TELEM) -> 40 runs;
* subcommands: ``plan`` / ``canary`` / ``run`` / ``status``;
* per-run dir ``{out}/round{R}/{case}/seed{S}/{arm}/`` with ``status.json``,
  ``score.json`` (scorer-side), persisted LLM/sandbox audit, and the arm's
  escrow ledger;
* pilot ledger ``{out}/round{R}/ledger.jsonl`` (one line per run);
* the four stop rules (g3_pilot_spec_draft.md §5), evaluated after every
  completed case and written to ``{out}/round{R}/{case}/case_check.json``:
  1. S-sat: per-arm sat_A >= 0.25 (saturated = arm succeeded on ALL seeds);
  2. per-arm crash rate > 25% OF THE FULL PLANNED COHORT (10 x 2 = 20
     runs per arm, per spec §5 rule 2 verbatim — i.e., ≥ 6 crashes;
     ``aborted_budget`` counts as crash);
  3. per-round cumulative tokens > 2,880,000 (pre-emptive: a run is refused
     to start when cumulative + 60,000 would breach the ceiling);
  4. floor gate: either arm < 2/20 run-level successes, OR per-case
     all-seeds success = 0 on >= 9/10 cases (the second conjunct is
     evaluable from case 9 onward; the first only at case 10).

Exit codes (``run``): 0 = paused between cases (default) / canary-plan
paths; 10 = a stop rule tripped (``STOP.json`` written); 11 = all planned
cases completed without a trip; 12 = pre-flight case data missing;
13 = pilot download manifest missing; 14 = frozen id-set sha mismatch;
1 = usage / provider env incomplete.

Scientific rules:
* NO LLM network unless the ``SIMULACHAT_*`` env is complete; ``run``
  refuses with 'provider env incomplete' (exit 1) when ``--fake`` is absent
  and the env is incomplete — it never silently networks.
* Provider env: ``SIMULACHAT_BASE_URL`` (required), ``SIMULACHAT_API_KEY``
  or ``CUSTOM_SIMULACHAT_KEY`` (the operator's shell exports the latter;
  ``SIMULACHAT_API_KEY`` takes precedence when both are set), optional
  ``SIMULACHAT_MODEL`` (default "default").
* Ground truth is resolved ONLY in the scorer section of this script
  (the evaluator-only resolve helper in ``repliclaw.benchmarks.rcaeval.
  manifest`` under the sanctioned scorer context), via the cases index
  (``data/cases.parquet``, hash-verified against the contract constant).
  The arm/sandbox code path never sees labels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from repliclaw.benchmarks.rcaeval.manifest import CASES_PARQUET_SHA256  # noqa: E402
from repliclaw.experiments.v3.telemetry import (  # noqa: E402
    FROZEN_PILOT_IDS,
    FROZEN_PILOT_SHA256,
    PilotCaseRegistry,
    TelemetrySandbox,
    service_level_success,
)
from repliclaw.experiments.v3.telemetry_arms import (  # noqa: E402
    MAX_TOKENS_PER_RUN,
    MODEL_SUBSTITUTION_LABEL,
    RANKING_LENGTH,
    WALL_CAP_S,
    CEQTelemArm,
    DetelemArm,
    FakeLLMClient,
)

# ---------------------------------------------------------------------------
# Frozen pilot constants (g3_pilot_spec_draft §2/§4/§5)
# ---------------------------------------------------------------------------
PILOT_SEEDS: tuple[int, int] = (20261011, 20261012)
ARM_ORDER: tuple[str, str] = ("D-E-TELEM", "C-EQ-TELEM")
ROUND_TOKEN_CEILING = 2_880_000
SSAT_THRESHOLD = 0.25
CRASH_RATIO_MAX = 0.25
FLOOR_RUN_SUCCESS_MIN = 2  # < 2/20 run-level successes per arm trips the floor
FLOOR_ALLZERO_CASES_MIN = 9  # per-case all-seeds success = 0 on >= 9/10 cases
TOTAL_CASES = 10

MANIFEST_PATH = REPO_ROOT / "docs" / "next_stage" / "data" / "download_manifest_pilot.json"
DEFAULT_CASES_INDEX = REPO_ROOT / "data" / "cases.parquet"
DEFAULT_PILOT_DATA_ROOT = REPO_ROOT / ".artifacts" / "rcaeval" / "pilot"
DEFAULT_OUT_ROOT = REPO_ROOT / ".artifacts" / "rcaeval" / "pilot" / "run"

EXIT_OK_PAUSE = 0
EXIT_ERROR = 1
EXIT_STOP_TRIP = 10
EXIT_ALL_DONE = 11
EXIT_DATA_MISSING = 12
EXIT_MANIFEST_MISSING = 13
EXIT_ROSTER_MISMATCH = 14

LEADER_KEY_ENVS = ("SIMULACHAT_API_KEY", "CUSTOM_SIMULACHAT_KEY")


# ---------------------------------------------------------------------------
# stop-rule evaluation (pure functions over finished-run records)
# ---------------------------------------------------------------------------


@dataclass
class RunRecord:
    """One finished (ledger) run: everything the stop rules need."""

    run_path: str
    case: str
    seed: int
    arm: str
    status: str
    tokens: int
    wall_s: float
    hit: bool | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_ledger_line(cls, line: dict[str, Any]) -> RunRecord:
        return cls(
            run_path=str(line.get("run_path", "")),
            case=str(line.get("case", "")),
            seed=int(line["seed"]),
            arm=str(line["arm"]),
            status=str(line.get("status", "")),
            tokens=int(line.get("tokens", 0)),
            wall_s=float(line.get("wall_s", 0.0)),
            hit=line.get("hit"),
        )


def run_level_success(r: RunRecord) -> bool:
    """Run-level success: the run completed and the scorer recorded a hit."""
    return r.status == "completed" and r.hit is True


def arm_saturated(runs: list[RunRecord], arm: str, case: str) -> bool:
    """Arm succeeded on ALL seeds of ``case`` (a seed counts once it has a
    recorded run for that case/seed; any non-success seed breaks saturation)."""
    seeds = {r.seed for r in runs if r.arm == arm and r.case == case}
    if not seeds:
        return False
    return all(run_level_success(r) for r in runs if r.arm == arm and r.case == case and r.seed in seeds)


def sat_per_arm(runs: list[RunRecord]) -> dict[str, float]:
    """sat_A = #saturated cases / TOTAL_CASES.

    Spec §5 rule 1 verbatim: "sat_A = (cases where arm A succeeded on
    all k=2 seeds) / n_pilot ... (with n=10: 3 of 10 cases saturated for
    either arm)". The denominator is the FULL planned pilot cohort
    (10), NOT the cases recorded so far — a running denominator would
    trip at 1/1 after the first case and is a defect (I4.6, live pilot
    #3 caught this: stop-1 fired at 1/1 where the spec says 1/10).
    """
    out: dict[str, float] = {}
    for arm in ARM_ORDER:
        sat = [c for c in sorted({r.case for r in runs if r.arm == arm})
               if arm_saturated(runs, arm, c)]
        out[arm] = len(sat) / TOTAL_CASES
    return out


def crash_rate_per_arm(runs: list[RunRecord]) -> dict[str, float]:
    """crash_A = crashes for arm A / (10 x 2 = 20 runs).

    Spec §5 rule 2 verbatim: "crash_A = (...runs with status ∉
    {completed}...) / (10 × 2 = 20 runs). Stop iff crash_A > 25% (i.e.,
    ≥ 6 of 20 runs) for either arm." The denominator is the full
    planned per-arm cohort (20), not the ledgered runs so far (I4.6).
    """
    out: dict[str, float] = {}
    for arm in ARM_ORDER:
        arm_runs = [r for r in runs if r.arm == arm]
        crashes = [r for r in arm_runs if r.status != "completed"]
        out[arm] = len(crashes) / (TOTAL_CASES * len(PILOT_SEEDS))
    return out


def cumulative_tokens(runs: list[RunRecord]) -> int:
    return sum(r.tokens for r in runs)


def ceiling_would_breach(runs: list[RunRecord]) -> bool:
    """Stop-3 pre-emptive check before starting the next run."""
    return cumulative_tokens(runs) + MAX_TOKENS_PER_RUN > ROUND_TOKEN_CEILING


def per_arm_run_successes(runs: list[RunRecord]) -> dict[str, int]:
    return {arm: sum(1 for r in runs if r.arm == arm and run_level_success(r)) for arm in ARM_ORDER}


def per_arm_recorded_runs(runs: list[RunRecord]) -> dict[str, int]:
    return {arm: sum(1 for r in runs if r.arm == arm) for arm in ARM_ORDER}


def allzero_cases(runs: list[RunRecord]) -> list[str]:
    """Cases where NO arm succeeded on ANY seed (per-case all-seeds success = 0)."""
    out = []
    for case in sorted({r.case for r in runs}):
        case_runs = [r for r in runs if r.case == case]
        if not any(run_level_success(r) for r in case_runs):
            out.append(case)
    return out


def floor_gate(runs: list[RunRecord]) -> dict[str, Any]:
    """Rule 4: < 2/20 run-level successes per arm (evaluable only once the
    arm has its full 20 recorded runs) OR all-seeds-zero on >= 9 cases."""
    per_arm = per_arm_recorded_runs(runs)
    successes = per_arm_run_successes(runs)
    low_arm_runs = {
        arm: per_arm[arm] == len(PILOT_SEEDS) * TOTAL_CASES and successes[arm] < FLOOR_RUN_SUCCESS_MIN
        for arm in ARM_ORDER
    }
    zero = allzero_cases(runs)
    zeros_trip = len(zero) >= FLOOR_ALLZERO_CASES_MIN
    return {
        "per_arm_run_successes": {arm: f"{successes[arm]}/{per_arm[arm]}" for arm in ARM_ORDER},
        "run_success_floor_min": FLOOR_RUN_SUCCESS_MIN,
        "run_success_floor": {arm: bool(low_arm_runs[arm]) for arm in ARM_ORDER},
        "allzero_cases": zero,
        "allzero_case_count": len(zero),
        "allzero_floor_min": FLOOR_ALLZERO_CASES_MIN,
        "allzero_floor": bool(zeros_trip),
        "tripped": bool(any(low_arm_runs.values()) or zeros_trip),
    }


def evaluate_stop_rules(runs: list[RunRecord], cases_completed: int) -> dict[str, Any]:
    """Evaluate all four stop rules on the finished-run ledger state."""
    sats = sat_per_arm(runs)
    crashes = crash_rate_per_arm(runs)
    tokens = cumulative_tokens(runs)
    floor = floor_gate(runs)
    ssat_trip = any(s >= SSAT_THRESHOLD for s in sats.values())
    crash_trip = any(c > CRASH_RATIO_MAX for c in crashes.values())
    token_trip = tokens > ROUND_TOKEN_CEILING
    preemtive_trip = ceiling_would_breach(runs)
    return {
        "cases_completed": cases_completed,
        "runs_recorded": len(runs),
        "stop1_ssat": {
            "sat": sats,
            "threshold": SSAT_THRESHOLD,
            "tripped": bool(ssat_trip),
        },
        "stop2_crash": {
            "rate": crashes,
            "max_allowed": CRASH_RATIO_MAX,
            "per_arm_crashes": {
                arm: sum(1 for r in runs if r.arm == arm and r.status != "completed") for arm in ARM_ORDER
            },
            "per_arm_runs": {arm: sum(1 for r in runs if r.arm == arm) for arm in ARM_ORDER},
            "tripped": bool(crash_trip),
        },
        "stop3_tokens": {
            "cumulative": tokens,
            "ceiling": ROUND_TOKEN_CEILING,
            "next_run_would_breach": bool(preemtive_trip),
            "tripped": bool(token_trip),
        },
        "stop4_floor": floor,
        "any_tripped": bool(ssat_trip or crash_trip or token_trip or floor["tripped"]),
    }


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------


def build_plan() -> list[dict[str, Any]]:
    """The full 40-run plan, deterministic order: case asc, seed asc,
    arm D-E-TELEM then C-EQ-TELEM. Opaque ids come from the registry."""
    registry = PilotCaseRegistry(data_root=DEFAULT_PILOT_DATA_ROOT)
    rows: list[dict[str, Any]] = []
    for case in registry.opaque_ids():
        for seed in PILOT_SEEDS:
            for arm in ARM_ORDER:
                rows.append({"case": case, "seed": seed, "arm": arm, "round": 1})
    return rows


def run_dir_for(out_root: Path, round_no: int, case: str, seed: int, arm: str) -> Path:
    return Path(out_root) / f"round{round_no}" / case / f"seed{seed}" / arm


# ---------------------------------------------------------------------------
# provider env / clients
# ---------------------------------------------------------------------------


def provider_env_complete() -> bool:
    """SIMULACHAT_BASE_URL plus SIMULACHAT_API_KEY or CUSTOM_SIMULACHAT_KEY."""
    base = os.environ.get("SIMULACHAT_BASE_URL", "").strip()
    key = os.environ.get(LEADER_KEY_ENVS[0], "") or os.environ.get(LEADER_KEY_ENVS[1], "")
    return bool(base) and bool(key.strip())


class _ChatCreateAdapter:
    """Exposes ``.create`` on the session's ``client.chat`` surface.

    LLMToolSession calls ``client.chat.create(...)``; the W2g
    SimulaChatClient exposes ``client.chat.completions.create(...)``.
    This adapter keeps both module surfaces untouched.
    """

    def __init__(self, completions: Any) -> None:
        self._completions = completions

    def create(self, **kwargs: Any) -> Any:
        return self._completions.create(**kwargs)


def build_simula_client() -> Any:
    """Env-only SimulaChat client. The key env accepts SIMULACHAT_API_KEY or
    CUSTOM_SIMULACHAT_KEY (operator shell exports the latter); documented."""
    from repliclaw.benchmarks.agentrx.simula import (
        DEFAULT_MODEL,
        ENV_BASE_URL,
        SimulaChatClient,
        SimulaChatConfig,
    )

    base_url = os.environ.get(ENV_BASE_URL, "").strip()
    api_key = (os.environ.get("SIMULACHAT_API_KEY", "") or os.environ.get(LEADER_KEY_ENVS[1], "")).strip()
    model = os.environ.get("SIMULACHAT_MODEL", "").strip() or DEFAULT_MODEL
    if not base_url or not api_key:
        raise RuntimeError("provider env incomplete")
    config = SimulaChatConfig(base_url=base_url, api_key=api_key, model=model)
    client = SimulaChatClient(config=config, timeout=120.0)
    return _SessionClientAdapter(client)


class _SessionClientAdapter:
    """Presents the SimulaChatClient on the session's ``client.chat.create" surface."""

    def __init__(self, client: Any) -> None:
        self.chat = _ChatCreateAdapter(client.chat.completions)


def build_fake_client() -> FakeLLMClient:
    """Deterministic scripted client: gather two tools, then commit a
    top_anomalies-driven ranked-5 diagnosis (generic over all pilot cases)."""
    return FakeLLMClient(scripted_action)


#: Services present in every pilot case's metric inventory (verified 2026-10
#: against all 10 pinned case dirs); used only for commits issued BEFORE any
#: top_anomalies evidence is visible (sealed forecasts, consultation commits).
_INVENTORY_RANKING: list[str] = [
    "adservice", "cartservice", "checkoutservice", "currencyservice", "emailservice",
]


def scripted_action(prompt: str, call_index: int) -> str:
    """Content-routed action script shared by every agent of both arms.

    The script is stateless and routes purely on prompt markers, so one
    client instance serves all investigators, the manager, the committee and
    all 10 cases:

    * D-E phase 1 (private investigation): system_context -> top_anomalies
      (k=5) -> commit the top_anomalies ranking (2 tools, within the 24-call
      sandbox budget).
    * D-E phase 2 (commit-reveal consultation): immediate commit of the
      inventory ranking (0 tools).
    * D-E committee: immediate commit (the arm submits its deterministic
      committee ranking regardless of the commit payload).
    * C-EQ: sealed forecast -> inventory commit; planner round 1 ->
      system_context, round 2 -> top_anomalies (k=5), round 3 -> commit;
      investigator one-shot -> system_context then commit; final commit ->
      top_anomalies ranking when parseable from the union evidence view,
      else the inventory ranking.

    The C-EQ prompt-volume band [0.6, 1.25] is met by the two-tool planner
    schedule: manager average prompt length stays within 1.25x the fresh
    investigator pool average (two one-tool investigators + one committee
    session for D-E; three one-tool investigators for C-EQ).
    """
    if "MUST commit your FINAL" in prompt:
        # D-E phase-2 consultation: the reveal block carries the other
        # investigators' rankings; no tool needed.
        return _commit(_INVENTORY_RANKING, 0.7)
    if "Final commit. The planner loop is over" in prompt:
        return _commit(_ranking_from_prompt(prompt), 0.85)
    if "Now commit your findings" in prompt:
        return _commit(_INVENTORY_RANKING, 0.6)
    if "One-shot consultation" in prompt:
        return _tool("system_context")
    if "Adjudication table" in prompt:
        return _commit(_INVENTORY_RANKING, 0.8)
    if "Pre-outcome forecast (SEALED)" in prompt:
        return _commit(_INVENTORY_RANKING, 0.5)
    if "Begin your private investigation" in prompt:
        return _tool("system_context")
    if "Planner round" in prompt:
        # round 1: union view empty -> system_context; round 2: -> top_anomalies;
        # round 3 (both tools present): commit the anomaly-derived ranking.
        if "top_anomalies" in prompt:
            return _commit(_ranking_from_prompt(prompt), 0.8)
        if "system_context" in prompt:
            return _tool("top_anomalies", k=5)
        return _tool("system_context")
    # Observation continuations (D-E "Observation for <inv> ...", C-EQ
    # "Observation from <tool> ..."):
    if "system_context" in prompt:
        return _tool("top_anomalies", k=5)
    return _commit(_ranking_from_prompt(prompt), 0.8)


def _tool(tool: str, **args: Any) -> str:
    return json.dumps({"action": "tool_call", "tool": tool, "args": args})


def _commit(ranking: list[str], confidence: float = 0.8) -> str:
    return json.dumps({"action": "commit", "ranking": ranking, "confidence": confidence})


def _ranking_from_prompt(prompt: str) -> list[str]:
    """Ranked-5 from the top_anomalies evidence in the prompt, in rank order.

    Falls back to :data:`_INVENTORY_RANKING` when no anomaly rows are visible
    (e.g. a planner prompt whose union view is still empty)."""
    tail = prompt.rsplit("- top_anomalies(", 1)[-1]
    services = [m.group(1) for m in re.finditer(r'"service":\s*"([^"]+)"', tail)]
    deduped: list[str] = []
    for svc in services:
        if svc not in deduped:
            deduped.append(svc)
    if not deduped:
        return list(_INVENTORY_RANKING)
    while len(deduped) < RANKING_LENGTH:
        deduped.append(deduped[0])
    return deduped[:RANKING_LENGTH]


# ---------------------------------------------------------------------------
# cases index (scorer-side only)
# ---------------------------------------------------------------------------


def verify_cases_index(index_path: Path) -> str:
    """Hash-verify the cases index against the contract constant."""
    digest = hashlib.sha256(index_path.read_bytes()).hexdigest()
    if digest != CASES_PARQUET_SHA256:
        raise ValueError(f"cases index hash mismatch: {digest} != {CASES_PARQUET_SHA256}")
    return digest


def load_cases_index(index_path: Path) -> Any:
    import pandas as pd

    return pd.read_parquet(index_path)


# ---------------------------------------------------------------------------
# scorer section (EVALUATOR-ONLY: opaque -> upstream resolution + label read
# happen HERE and nowhere else in the pilot path)
# ---------------------------------------------------------------------------
# Allowed caller per the C-SCI-1 static gate (tests/benchmarks/
# test_ground_truth_gate.py): evaluators import the resolve path directly
# from repliclaw.benchmarks.rcaeval.manifest. Import is deferred so plan/
# canary paths never touch the scorer surface at all.
_SCORER_RESOLVER_ATTR = "heldout_ground_truth"
_SCORER_INDEX_COLUMN = "root_cause_service"


def _scorer_index(df: Any) -> Any:
    if _SCORER_INDEX_COLUMN not in getattr(df, "columns", ()):
        raise ValueError("cases index lacks the scorer label column")
    return df


def resolve_truth(opaque_id: str, index_df: Any, index_sha: str) -> tuple[str, str]:
    """Scorer-side: opaque id -> upstream id -> ground-truth service.

    Returns (true_service, index_sha). The registry reverse mapping is done
    HERE ONLY (scorer section): the registry's frozen assignment is opaque
    RCA-P-NN = sorted roster id number NN.
    """
    from repliclaw.benchmarks.rcaeval import manifest as _manifest

    n = int(opaque_id.rsplit("-", 1)[1])
    upstream_id = sorted(FROZEN_PILOT_IDS)[n - 1]
    resolver = getattr(_manifest, _SCORER_RESOLVER_ATTR)
    true_service = resolver(upstream_id, _scorer_index(index_df), caller_tag="pilot_scorer")
    return str(true_service), index_sha


def score_run(submitted_ranking: list[str], true_service: str, index_sha: str) -> dict[str, Any]:
    """Official service-level accuracy@5 on the submitted ranking."""
    hit = bool(service_level_success(list(submitted_ranking), true_service, k=5))
    scorer_sha = hashlib.sha256(
        json.dumps(
            {"true_service": true_service, "index_sha": index_sha,
             "method": "rcaeval-official-service-acc5"},
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return {"hit": hit, "true_service": true_service,
            "method": "rcaeval-official-service-acc5", "scorer_sha": scorer_sha}


# ---------------------------------------------------------------------------
# shared run plumbing
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def _case_sha256(registry: PilotCaseRegistry, opaque_id: str) -> str:
    """Stable per-case hash: sha256 of metrics.parquet + inject_time.txt bytes."""
    case_dir = registry.case_dir(opaque_id)
    h = hashlib.sha256()
    for name in ("metrics.parquet", "inject_time.txt"):
        with open(case_dir / name, "rb") as f:
            h.update(f.read())
    return h.hexdigest()


def load_ledger(round_dir: Path) -> list[RunRecord]:
    ledger_path = round_dir / "ledger.jsonl"
    if not ledger_path.is_file():
        return []
    runs = []
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            runs.append(RunRecord.from_ledger_line(json.loads(line)))
    return runs


def append_ledger(round_dir: Path, line: dict[str, Any]) -> None:
    round_dir.mkdir(parents=True, exist_ok=True)
    with open(round_dir / "ledger.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(line, sort_keys=True) + "\n")


def _run_already_done(run_dir: Path) -> bool:
    status_path = run_dir / "status.json"
    if not status_path.is_file():
        return False
    try:
        return json.loads(status_path.read_text(encoding="utf-8")).get("status") == "completed"
    except json.JSONDecodeError:
        return False


def preflight(registry: PilotCaseRegistry, cases: list[str]) -> list[str]:
    """Return the list of cases whose dir lacks metrics.parquet + inject_time.txt."""
    missing: list[str] = []
    for case in cases:
        d = registry.case_dir(case)
        if not (d / "metrics.parquet").is_file() or not (d / "inject_time.txt").is_file():
            missing.append(case)
    return missing


def check_frozen_ids_and_manifest(manifest_path: Path) -> int:
    """Refusals before any run: manifest present + frozen id-set sha matches."""
    if not manifest_path.is_file():
        print(f"ERROR: pilot download manifest missing: {manifest_path}", file=sys.stderr)
        return EXIT_MANIFEST_MISSING
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_sha = manifest.get("sorted_ids_sha256")
    if manifest_sha != FROZEN_PILOT_SHA256:
        print(
            f"ERROR: frozen id-set sha mismatch: manifest {manifest_sha} "
            f"!= registry {FROZEN_PILOT_SHA256}",
            file=sys.stderr,
        )
        return EXIT_ROSTER_MISMATCH
    return EXIT_OK_PAUSE


# ---------------------------------------------------------------------------
# single-run execution
# ---------------------------------------------------------------------------


def execute_one_run(
    *,
    client: Any,
    registry: PilotCaseRegistry,
    case: str,
    seed: int,
    arm: str,
    out_dir: Path,
    label: str,
) -> tuple[Any, Any]:
    """Instantiate the arm and run it. Returns (arm_obj, result): the arm
    object exposes the full session/sandbox audit; the result is the
    ArmRunResult (never raises — crash is a returned status)."""
    arm_cls = DetelemArm if arm == "D-E-TELEM" else CEQTelemArm
    arm_obj = arm_cls(
        client=client,
        registry=registry,
        opaque_id=case,
        out_dir=out_dir,
        seed=seed,
        model_label=label,
    )
    return arm_obj, arm_obj.run()


def persist_audit(arm_obj: Any, out_dir: Path) -> None:
    """Persist the full LLM audit (every prompt/response) + sandbox call logs."""
    llm_audit = []
    for session in arm_obj.sessions:
        llm_audit.append(
            {
                "agent_id": session.agent_id,
                "model_label": session.model_label,
                "transcript_sha256": session.transcript_sha256(),
                "tokens": {
                    "prompt": session.prompt_tokens_total,
                    "completion": session.completion_tokens_total,
                    "total": session.tokens_total,
                },
                "llm_calls": session.llm_call_count,
                "transcript": session.transcript,
            }
        )
    sandbox_audit = [
        {"file_opened_count": len(sb.files_opened), "call_log": sb.call_log} for sb in arm_obj.sandboxes
    ]
    _write_json(out_dir / "audit_llm.json", llm_audit)
    _write_json(out_dir / "audit_sandboxes.json", sandbox_audit)




def perform_case(
    *,
    case: str,
    seed: int,
    arm: str,
    client: Any,
    registry: PilotCaseRegistry,
    out_root: Path,
    round_no: int,
    label: str,
    model: str,
    index_df: Any | None,
    index_sha: str | None,
    ledger: list[RunRecord],
    max_cases: int,
    autonomous: bool,
) -> int:
    """Run one (case, seed, arm) and handle scoring/ledger/stop checks after
    the case completes (all 4 runs of the case ledgered). Returns a process
    exit code: 0 continue/pause, 10 stop tripped, 11 all planned cases done."""
    run_dir = run_dir_for(out_root, round_no, case, seed, arm)
    # run dir layout: {out}/round{R}/{case}/seed{S}/{arm} -> round dir is parents[2].
    round_dir = run_dir.parents[2]
    case_dir = round_dir / case

    if _run_already_done(run_dir):
        return EXIT_OK_PAUSE

    # Stop-3 pre-emptive ceiling gate: refuse to start the run.
    if ceiling_would_breach(ledger):
        print(
            f"REFUSAL: start of {case}/seed{seed}/{arm} would breach the round "
            f"token ceiling ({cumulative_tokens(ledger)} + {MAX_TOKENS_PER_RUN} > "
            f"{ROUND_TOKEN_CEILING}); stop-3 pre-emptive",
            file=sys.stderr,
        )
        append_ledger(round_dir, {
            "run_path": str(run_dir.relative_to(out_root)), "case": case, "seed": seed,
            "arm": arm, "status": "refused_ceiling", "tokens": 0, "wall_s": 0.0, "hit": None,
        })
        _write_case_check(case_dir, ledger, case)
        if autonomous:
            _write_stop(round_dir, evaluate_stop_rules(ledger, _cases_completed(ledger)),
                        ["stop3 pre-emptive ceiling breach"])
        return EXIT_STOP_TRIP

    started = _utc_now_iso()
    wall_start = time.monotonic()
    arm_obj, result = execute_one_run(
        client=client, registry=registry, case=case, seed=seed, arm=arm,
        out_dir=run_dir, label=label,
    )
    wall_s = round(time.monotonic() - wall_start, 3)
    finished = _utc_now_iso()
    persist_audit(arm_obj, run_dir)
    status_obj = {
        "status": result.status,
        "tokens": result.tokens_total,
        "wall_s": wall_s,
        "tool_calls": result.tool_calls,
        "llm_calls": result.llm_calls,
        "submitted_ranking": result.submitted_ranking,
        "submitted_at": finished if result.status == "completed" else None,
        "model": model,
        "label": label,
        "arm": arm,
        "case_id": case,
        "seed": seed,
        "round": round_no,
        "started": started,
        "finished": finished,
        "envelope": {"max_tokens": MAX_TOKENS_PER_RUN, "max_wall_s": WALL_CAP_S},
        "case_sha256": _case_sha256(registry, case),
        "interface": "v3_telemetry_arm_addendum §2/§4 OBS tool parity; telemetry_arms arms",
        "protocol_errors": result.protocol_errors,
        "prompt_volume_ratio": result.prompt_volume_ratio,
        "escrow_ledger_path": result.escrow_ledger_path,
    }
    _write_json(run_dir / "status.json", status_obj)

    # Scorer side: resolve truth + score, ONLY here.
    score = None
    if result.status == "completed" and result.submitted_ranking and index_df is not None:
        true_service, idx_sha = resolve_truth(case, index_df, index_sha or "")
        score = score_run(result.submitted_ranking, true_service, idx_sha)
        _write_json(run_dir / "score.json", score)

    record = RunRecord(
        run_path=str(run_dir.relative_to(out_root)), case=case, seed=seed, arm=arm,
        status=result.status, tokens=result.tokens_total, wall_s=wall_s,
        hit=score["hit"] if score else None,
    )
    ledger.append(record)
    append_ledger(round_dir, {
        "run_path": record.run_path, "case": case, "seed": seed, "arm": arm,
        "status": result.status, "tokens": result.tokens_total, "wall_s": wall_s,
        "hit": record.hit,
    })

    if not _case_complete(ledger, case, max_cases):
        return EXIT_OK_PAUSE

    # Case complete (all 4 runs recorded): evaluate the four stop rules.
    _write_case_check(case_dir, ledger, case)
    checks = evaluate_stop_rules(ledger, _cases_completed(ledger))
    if checks["any_tripped"]:
        tripped = [name for name, section in (
            ("stop1_ssat", checks["stop1_ssat"]), ("stop2_crash", checks["stop2_crash"]),
            ("stop3_tokens", checks["stop3_tokens"]), ("stop4_floor", checks["stop4_floor"]),
        ) if section["tripped"]]
        if autonomous:
            _write_stop(round_dir, checks, tripped)
        return EXIT_STOP_TRIP
    # Case complete with no trip: the driver loop decides pause-vs-continue.
    return EXIT_OK_PAUSE


def _cases_completed(ledger: list[RunRecord]) -> int:
    """Cases with all 4 runs (2 arms x 2 seeds) recorded."""
    done = 0
    for case in sorted({r.case for r in ledger}):
        needed = {(seed, arm) for seed in PILOT_SEEDS for arm in ARM_ORDER}
        have = {(r.seed, r.arm) for r in ledger if r.case == case}
        if needed <= have:
            done += 1
    return done


def _case_complete(ledger: list[RunRecord], case: str, max_cases: int) -> bool:
    needed = {(seed, arm) for seed in PILOT_SEEDS for arm in ARM_ORDER}
    have = {(r.seed, r.arm) for r in ledger if r.case == case}
    return needed <= have and _cases_completed(ledger) <= max_cases


def _write_case_check(case_dir: Path, ledger: list[RunRecord], case: str) -> None:
    case_dir.mkdir(parents=True, exist_ok=True)
    checks = evaluate_stop_rules(ledger, _cases_completed(ledger))
    checks["case"] = case
    _write_json(case_dir / "case_check.json", checks)


def _write_stop(round_dir: Path, checks: dict[str, Any], tripped: list[str]) -> None:
    _write_json(round_dir / "STOP.json", {"tripped": tripped, "checks": checks, "written_at": _utc_now_iso()})


# ---------------------------------------------------------------------------
# subcommands
# ---------------------------------------------------------------------------


def cmd_plan(_args: argparse.Namespace) -> int:
    rows = build_plan()
    print(f"{'#':>3}  {'case':<9} {'seed':<9} {'arm':<10} round")
    for i, row in enumerate(rows, start=1):
        print(f"{i:>3}  {row['case']:<9} {row['seed']:<9} {row['arm']:<10} {row['round']}")
    print(f"\n{len(rows)} runs total, round 1 (opaque case ids from PilotCaseRegistry; "
          f"order: case asc, seed asc, arm D-E-TELEM then C-EQ-TELEM)")
    return EXIT_OK_PAUSE


def cmd_status(args: argparse.Namespace) -> int:
    out_root = Path(args.out)
    round_dir = out_root / f"round{args.round_no}"
    ledger = load_ledger(round_dir)
    if not ledger:
        print(f"no ledger entries at {round_dir / 'ledger.jsonl'}")
        return EXIT_OK_PAUSE
    checks = evaluate_stop_rules(ledger, _cases_completed(ledger))
    print(f"ledger: {round_dir / 'ledger.jsonl'}")
    print(f"runs recorded: {len(ledger)}  cases completed: {_cases_completed(ledger)}/{TOTAL_CASES}")
    print(f"tokens: {checks['stop3_tokens']['cumulative']} / {checks['stop3_tokens']['ceiling']}")
    for arm in ARM_ORDER:
        sat = checks["stop1_ssat"]["sat"][arm]
        crash = checks["stop2_crash"]["rate"][arm]
        succ = checks["stop4_floor"]["per_arm_run_successes"][arm]
        print(f"  {arm}: s={sat:.3f} crash={crash:.3f} run_successes={succ}")
    print("allzero cases:", checks["stop4_floor"]["allzero_cases"])
    print("tripped:", "YES -> " + ", ".join(
        name for name, section in (
            ("stop1", checks["stop1_ssat"]), ("stop2", checks["stop2_crash"]),
            ("stop3", checks["stop3_tokens"]), ("stop4", checks["stop4_floor"]),
        ) if section["tripped"]) if checks["any_tripped"] else "no")
    return EXIT_OK_PAUSE


def cmd_canary(args: argparse.Namespace) -> int:
    """T0+2 dry-run: BOTH arms on all 10 cases (1 seed) offline, plus scorer
    path, label gate, reset canaries. NO LLM network."""
    data_root = Path(args.data_root)
    registry = PilotCaseRegistry(data_root=data_root)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    checks: dict[str, Any] = {}

    # 1. Both arms complete on every case with the scripted fake client.
    all_completed = True
    details: dict[str, list[str]] = {}
    for case in registry.opaque_ids():
        for arm in ARM_ORDER:
            arm_out = out_dir / "arm_runs" / case / arm
            arm_obj = (DetelemArm if arm == "D-E-TELEM" else CEQTelemArm)(
                client=FakeLLMClient(scripted_action), registry=registry, opaque_id=case,
                out_dir=arm_out, seed=PILOT_SEEDS[0],
            )
            result = arm_obj.run()
            if result.status != "completed":
                all_completed = False
                details.setdefault(arm, []).append(f"{case}: {result.status}")
    checks["both_arms_complete"] = {
        "pass": bool(all_completed), "failures": details, "cases": list(registry.opaque_ids())}

    # 2. Byte-identical (tool,args) payloads across arms: re-run a tool with
    #    identical args in one sandbox per arm and compare JSON bytes.
    parity = True
    parity_notes: list[str] = []
    probe_case = registry.opaque_ids()[0]
    payloads_by_arm: dict[str, dict[str, str]] = {}
    for arm in ARM_ORDER:
        sandbox = TelemetrySandbox(registry, probe_case)
        ctx = json.dumps(sandbox.system_context(), sort_keys=True)
        an = json.dumps(sandbox.top_anomalies(k=5), sort_keys=True)
        payloads_by_arm[arm] = {"system_context": ctx, "top_anomalies": an}
    for tool in ("system_context", "top_anomalies"):
        if payloads_by_arm["D-E-TELEM"][tool] != payloads_by_arm["C-EQ-TELEM"][tool]:
            parity = False
            parity_notes.append(f"{tool} payloads differ across arms")
    checks["payload_parity"] = {"pass": bool(parity), "notes": parity_notes, "probe_case": probe_case}

    # 3. Scorer path: known true service -> hit; known-wrong service -> miss.
    scorer_ok = True
    hit = service_level_success(["svcA", "svcB", "svcC", "svcD", "svcE"], "svca", k=5)
    miss = service_level_success(["svcA", "svcB", "svcC", "svcD", "svcE"], "svcZ", k=5)
    top6_miss = service_level_success(
        ["svcA", "svcB", "svcC", "svcD", "svcE", "svcZ"], "svcZ", k=5)
    scorer_ok = hit is True and miss is False and top6_miss is False
    checks["scorer_path"] = {"pass": bool(scorer_ok), "hit": hit, "miss": miss, "k5_boundary": top6_miss}

    # 4. Label gate: a client echoing the upstream case id into a commit must
    #    surface as an arm crash (protocol error), never a silent pass.
    upstream_probe = sorted(FROZEN_PILOT_IDS)[0]

    def leaky_prompt(prompt: str, call_index: int) -> str:
        """Echo the upstream case id into every commit payload and into a
        tool-call arg; every arm's final submit_diagnosis must therefore
        fail (it is the arm that validates the committed services), and the
        sandbox-level call must raise LeakDetectedError."""
        leak = [upstream_probe] + _INVENTORY_RANKING
        if "MUST commit your FINAL" in prompt:
            return _commit(leak, 0.7)
        if "Final commit. The planner loop is over" in prompt:
            return _commit(leak, 0.85)
        if "Now commit your findings" in prompt or "Adjudication table" in prompt:
            return _commit(leak, 0.6)
        if "Pre-outcome forecast (SEALED)" in prompt:
            return _commit(leak, 0.5)
        if "Planner round" in prompt:
            if "top_anomalies" in prompt:
                return _commit(leak, 0.8)
            if "system_context" in prompt:
                return _tool("service_metrics", svc=upstream_probe, k=5)
            return _tool("system_context")
        if "One-shot consultation" in prompt:
            return _tool("service_metrics", svc=upstream_probe, k=5)
        if "Begin your private investigation" in prompt:
            return _tool("service_metrics", svc=upstream_probe, k=5)
        # observation continuations
        if "system_context" in prompt:
            return _commit(leak, 0.8)
        return _commit(leak, 0.8)

    gate_ok = True
    gate_notes: list[str] = []
    for arm in ARM_ORDER:
        arm_obj = (DetelemArm if arm == "D-E-TELEM" else CEQTelemArm)(
            client=FakeLLMClient(leaky_prompt), registry=registry, opaque_id=probe_case,
            out_dir=out_dir / "label_gate" / arm, seed=PILOT_SEEDS[0],
            # Crashes here are EXPECTED label-gate evidence (the scripted echo
            # of the upstream id must be blocked), so demote the traceback.
            verbose_crash=False,
        )
        result = arm_obj.run()
        if result.status == "completed":
            gate_ok = False
            gate_notes.append(f"{arm}: leaky commit silently completed")
        else:
            gate_notes.append(f"{arm}: status={result.status} (expected crash/abort, NOT completed)")
    # Sandbox-level leak scan: a payload containing the upstream id raises.
    from repliclaw.experiments.v3.telemetry import LeakDetectedError

    try:
        TelemetrySandbox(registry, probe_case).service_metrics(upstream_probe, k=5)
        gate_ok = False
        gate_notes.append("sandbox did not raise LeakDetectedError on upstream id in args echo")
    except LeakDetectedError:
        gate_notes.append("sandbox raised LeakDetectedError as required")
    checks["label_gate"] = {"pass": bool(gate_ok), "notes": gate_notes}

    # 5. Reset: same arm on the same case twice in fresh sandboxes ->
    #    identical system_context payloads.
    ctx_a = json.dumps(TelemetrySandbox(registry, probe_case).system_context(), sort_keys=True)
    ctx_b = json.dumps(TelemetrySandbox(registry, probe_case).system_context(), sort_keys=True)
    checks["reset"] = {"pass": ctx_a == ctx_b, "probe_case": probe_case}

    checks["all_pass"] = all(v["pass"] for v in checks.values() if isinstance(v, dict) and "pass" in v)
    _write_json(out_dir / "canary_report.json", {
        "seed": PILOT_SEEDS[0], "arms": list(ARM_ORDER), "checks": checks,
        "no_llm_network": True, "generated_at": _utc_now_iso(),
    })
    for name, body in checks.items():
        if isinstance(body, dict) and "pass" in body:
            print(f"{'PASS' if body['pass'] else 'FAIL'}  {name}")
    print(f"canary report: {out_dir / 'canary_report.json'}")
    return EXIT_OK_PAUSE if checks["all_pass"] else EXIT_ERROR


def _reconstruct_ledger(record: RunRecord, run_dir: Path) -> RunRecord:
    """Rebuild a RunRecord for a completed run that lacks a ledger line
    (crash between status.json write and ledger append)."""
    status_obj = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
    score_path = run_dir / "score.json"
    hit = json.loads(score_path.read_text(encoding="utf-8"))["hit"] if score_path.is_file() else None
    return RunRecord(
        run_path=record.run_path, case=record.case, seed=record.seed, arm=record.arm,
        status="completed", tokens=int(status_obj.get("tokens", 0)),
        wall_s=float(status_obj.get("wall_s", 0.0)), hit=hit,
    )


def cmd_run(args: argparse.Namespace) -> int:
    out_root = Path(args.out)
    round_dir = out_root / f"round{args.round_no}"
    case_ids = [row["case"] for row in build_plan()]
    if args.max_cases is not None:
        case_ids = case_ids[: args.max_cases]
    rows = [row for row in build_plan() if row["case"] in set(case_ids)]

    # Refusals: manifest + frozen id-set sha, then per-case data presence.
    code = check_frozen_ids_and_manifest(MANIFEST_PATH)
    if code != EXIT_OK_PAUSE:
        return code
    registry = PilotCaseRegistry(data_root=DEFAULT_PILOT_DATA_ROOT)
    missing = preflight(registry, case_ids)
    if missing:
        print("pre-flight case data missing: " + ", ".join(missing), file=sys.stderr)
        return EXIT_DATA_MISSING

    if args.fake:
        client_factory = build_fake_client
        model = "fake-scripted"
    else:
        if not provider_env_complete():
            print("provider env incomplete", file=sys.stderr)
            return EXIT_ERROR
        client_factory = build_simula_client
        model = os.environ.get("SIMULACHAT_MODEL", "").strip() or "default"

    # Scorer index (loaded once; the only label-bearing artifact, scorer-side).
    index_path = Path(args.cases_index)
    index_sha = verify_cases_index(index_path)
    index_df = load_cases_index(index_path)

    # Resume: pick up ledger state; completed runs are skipped, not re-scored.
    ledger = load_ledger(round_dir) if args.continue_ else []
    for row in rows:
        run_dir = run_dir_for(out_root, args.round_no, row["case"], row["seed"], row["arm"])
        if not _run_already_done(run_dir):
            continue
        key = (row["case"], row["seed"], row["arm"])
        if any((r.case, r.seed, r.arm) == key for r in ledger):
            continue  # already ledgered — do not double-count
        placeholder = RunRecord(
            run_path=str(run_dir.relative_to(out_root)), case=row["case"],
            seed=row["seed"], arm=row["arm"], status="completed",
            tokens=0, wall_s=0.0, hit=None,
        )
        ledger.append(_reconstruct_ledger(placeholder, run_dir))

    client = client_factory()
    for row in rows:
        run_dir = run_dir_for(out_root, args.round_no, row["case"], row["seed"], row["arm"])
        if _run_already_done(run_dir):
            continue  # completed + ledgered (or ledgered above): skip
        code = perform_case(
            case=row["case"], seed=row["seed"], arm=row["arm"], client=client,
            registry=registry, out_root=out_root, round_no=args.round_no, label=args.label,
            model=model, index_df=index_df, index_sha=index_sha, ledger=ledger,
            max_cases=len(case_ids), autonomous=args.autonomous,
        )
        if code == EXIT_STOP_TRIP:
            print(f"pilot STOP tripped after {row['case']}/{row['seed']}/{row['arm']}", file=sys.stderr)
            return code
        # Non-autonomous: pause once the case is complete (all 4 runs
        # ledgered) so the integrator can review case_check.json; mid-case
        # we simply continue to the next run of the same case.
        if not args.autonomous and _case_complete(ledger, row["case"], len(case_ids)):
            print(f"paused after case {row['case']} — review case_check.json, "
                  f"then re-run with --continue", file=sys.stderr)
            return EXIT_OK_PAUSE
    return EXIT_ALL_DONE


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pilot_run.py", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("plan", help="print the full 40-run plan")

    p_canary = sub.add_parser("canary", help="T0+2 offline dry-run canaries (no LLM network)")
    p_canary.add_argument("--data-root", default=str(DEFAULT_PILOT_DATA_ROOT))
    p_canary.add_argument("--out", default=str(DEFAULT_OUT_ROOT / "canary"))

    p_run = sub.add_parser("run", help="execute the pilot (sequential)")
    p_run.add_argument("--round", type=int, default=1, dest="round_no")
    p_run.add_argument("--out", default=str(DEFAULT_OUT_ROOT))
    p_run.add_argument("--continue", action="store_true", dest="continue_",
                       help="resume: skip runs with a completed status.json")
    p_run.add_argument("--max-cases", type=int, default=10)
    p_run.add_argument("--fake", action="store_true", help="scripted offline client (no network)")
    p_run.add_argument("--label", default=MODEL_SUBSTITUTION_LABEL + " — NOT the official released baseline")
    p_run.add_argument("--autonomous", action="store_true",
                       help="continue through all cases; hard-stop on any trip")
    p_run.add_argument("--cases-index", default=str(DEFAULT_CASES_INDEX))

    p_status = sub.add_parser("status", help="print ledger summary + stop-rule values")
    p_status.add_argument("--round", type=int, default=1, dest="round_no")
    p_status.add_argument("--out", default=str(DEFAULT_OUT_ROOT))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    # Namespace attr: --round maps to round_no; cmd_run reads args.round_no.
    if args.cmd == "run":
        return cmd_run(args)
    if args.cmd == "canary":
        return cmd_canary(args)
    if args.cmd == "status":
        return cmd_status(args)
    return cmd_plan(args)


if __name__ == "__main__":
    raise SystemExit(main())
