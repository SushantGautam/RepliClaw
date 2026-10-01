"""SimpleAudit-backed counterfactual executor (P02 hero case).

``SimpleAuditExecutor`` wraps ``simpleaudit.model_auditor.ModelAuditor`` with
the deterministic frozen target/judge from :mod:`frozen_backend`.
``run_case`` executes one (case, intervention) arm and persists a replayable
artifact set; ``replay`` re-executes and verifies byte-identical provenance.

Determinism rules (why replay is byte-identical):
* The target and judge are pure functions of the effective config.
* SimpleAudit offline mode never calls a real LLM; all token counts are 0.
* Persisted per-arm files (config.json, target_output.txt, conversation.json,
  stdout.log, judgment.json) contain NO wall-clock timestamps. The
  started_at/finished_at timestamps live only in the manifest, which replay
  does not compare byte-for-byte (it compares the deterministic content files
  and their sha256 pins).

Contract §5/§7: every arm records case+config hashes, engine metadata
(name/version/git_sha), the raw target output, conversation, judgment,
severity, token counts, and per-file sha256 hashes.
"""
from __future__ import annotations

import asyncio
import importlib.metadata
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from repliclaw.counterfactual.case import (
    FACTOR_JUDGE_REFERENCE,
    FACTOR_RETRIEVAL,
    CaseSpec,
    InterventionSpec,
    canonical_bytes,
    sha256_bytes,
)
from repliclaw.counterfactual.frozen_backend import FrozenJudgeClient, make_target_fn

# ---------------------------------------------------------------------------
# Engine metadata
# ---------------------------------------------------------------------------


def _simpleaudit_version() -> str:
    return importlib.metadata.version("simpleaudit")


def _simpleaudit_git_sha() -> str:
    try:
        import simpleaudit

        root = Path(simpleaudit.__file__).resolve().parent.parent
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        return out.stdout.strip()
    except Exception:  # noqa: BLE001 - git metadata is best-effort
        return ""


def engine_metadata() -> Dict[str, str]:
    return {
        "name": "simpleaudit",
        "version": _simpleaudit_version(),
        "git_sha": _simpleaudit_git_sha(),
    }


# ---------------------------------------------------------------------------
# Run record
# ---------------------------------------------------------------------------


class InterventionRun(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    case_id: str
    case_version: str
    intervention_id: str
    case_sha256: str
    config_sha256: str
    model_id: str
    seed: int
    engine: Dict[str, str]  # {name, version, git_sha}
    started_at: str  # ISO-8601; manifest only, never in a per-arm file
    finished_at: str
    target_output: str
    conversation: List[Dict[str, str]]
    judgment: Dict[str, Any]
    severity: str
    token_counts: Dict[str, int]
    exit_code: int
    stdout_log: str = ""
    artifact_hashes: Dict[str, str]  # arm file name -> sha256

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------


class SimpleAuditExecutor:
    """Wraps ModelAuditor with a deterministic target/judge per run config."""

    def __init__(self, seed: int = 0) -> None:
        self.seed = int(seed)

    def run(
        self,
        case: CaseSpec,
        intervention: InterventionSpec,
        effective_config: Dict[str, Any],
    ) -> InterventionRun:
        from datetime import datetime, timezone

        from simpleaudit.model_auditor import ModelAuditor
        from simpleaudit.targets.callable import CallableTarget

        started_iso = datetime.now(timezone.utc).isoformat()
        retrieved = list(effective_config[FACTOR_RETRIEVAL])
        reference_days = int(effective_config[FACTOR_JUDGE_REFERENCE])

        auditor = ModelAuditor(
            model=case.target_model_id,
            provider="openai",
            judge_model="deterministic-rubric-judge/v1",
            judge_provider="openai",
            api_key="offline-placeholder",
            judge_api_key="offline-placeholder",
            judge_prompt="Return JSON: severity pass|critical, issues_found, summary.",
            max_turns=1,
            show_progress=False,
        )
        auditor.set_target(CallableTarget(make_target_fn(retrieved)))
        auditor.judge_client = FrozenJudgeClient(reference_days)

        scenario = case.scenario
        result = asyncio.run(
            auditor.run_scenario(
                name=scenario["name"],
                description=scenario["description"],
                expected_behavior=scenario["expected_behavior"],
                test_prompt=scenario["test_prompt"],
                max_turns=1,
            )
        )
        finished_iso = datetime.now(timezone.utc).isoformat()

        target_output = ""
        for turn in reversed(result.conversation):
            if turn.get("role") == "assistant":
                target_output = str(turn.get("content", ""))
                break

        judgment = result.judgment if isinstance(result.judgment, dict) else {}
        token_counts = {
            "auditor_input": int(result.auditor_input_tokens or 0),
            "auditor_output": int(result.auditor_output_tokens or 0),
            "judge_input": int(result.judge_input_tokens or 0),
            "judge_output": int(result.judge_output_tokens or 0),
            "target_input": int(result.target_input_tokens or 0),
            "target_output": int(result.target_output_tokens or 0),
            "real_token_calls": 0,  # offline: no network/token spend
        }

        return InterventionRun(
            run_id=f"{case.case_id}::{intervention.intervention_id}::seed{self.seed}",
            case_id=case.case_id,
            case_version=case.case_version,
            intervention_id=intervention.intervention_id,
            case_sha256=case.sha256,
            config_sha256=sha256_bytes(canonical_bytes(effective_config)),
            model_id=case.target_model_id,
            seed=self.seed,
            engine=engine_metadata(),
            started_at=started_iso,
            finished_at=finished_iso,
            target_output=target_output,
            conversation=[
                {"role": str(t.get("role", "")), "content": str(t.get("content", ""))}
                for t in result.conversation
            ],
            judgment=judgment,
            severity=str(result.severity),
            token_counts=token_counts,
            exit_code=0,
            stdout_log="offline simpleaudit run; deterministic target+judge; 0 real tokens\n",
            artifact_hashes={},  # populated at persistence time
        )


# ---------------------------------------------------------------------------
# Case / intervention loading (no oracle import path — contract §6)
# ---------------------------------------------------------------------------

_CASES_ROOT = Path(__file__).resolve().parents[3] / "experiments"

# case_id -> data directory. The hero case's data lives in experiments/policy_rag/
# (owned path) while its frozen case_id is policy_rag_v1.
_CASE_DIRS = {"policy_rag_v1": "policy_rag"}


def case_dir(case_id: str) -> Path:
    return _CASES_ROOT / _CASE_DIRS.get(case_id, case_id)


# Deterministic per-arm files (no timestamps).
ARM_FILES = ("config.json", "target_output.txt", "conversation.json", "stdout.log", "judgment.json")


def load_case(case_id: str = "policy_rag_v1") -> CaseSpec:
    spec_path = case_dir(case_id) / "case.json"
    data = json.loads(spec_path.read_text(encoding="utf-8"))
    return CaseSpec(**data)


def load_interventions(case_id: str = "policy_rag_v1") -> List[InterventionSpec]:
    spec_path = case_dir(case_id) / "interventions.json"
    data = json.loads(spec_path.read_text(encoding="utf-8"))
    return [InterventionSpec(**d) for d in data]


def case_root(case_id: str) -> Path:
    return case_dir(case_id)


# ---------------------------------------------------------------------------
# Persistence (contract §7 layout, compact)
# ---------------------------------------------------------------------------


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def persist_arm(
    run: InterventionRun, effective_config: Dict[str, Any], out_root: Path
) -> Dict[str, str]:
    """Write one arm's deterministic files; return {name: sha256}."""
    arm = Path(out_root) / "interventions" / run.intervention_id
    arm.mkdir(parents=True, exist_ok=True)
    _write_json(arm / "config.json", effective_config)
    (arm / "target_output.txt").write_text(run.target_output + "\n", encoding="utf-8")
    _write_json(arm / "conversation.json", run.conversation)
    (arm / "stdout.log").write_text(run.stdout_log, encoding="utf-8")
    _write_json(arm / "judgment.json", run.judgment)

    hashes = {name: sha256_bytes((arm / name).read_bytes()) for name in ARM_FILES}
    _write_json(arm / "hashes.json", hashes)
    return hashes


def write_case_manifest(case: CaseSpec, out_root: Path, runs: Dict[str, InterventionRun]) -> Path:
    """Pin the case-level manifest (contract §7) that ``replay`` verifies."""
    arms: Dict[str, Any] = {}
    for arm_id in sorted(runs):
        run = runs[arm_id]
        arm_dir = Path(out_root) / "interventions" / arm_id
        arms[arm_id] = {
            **run.to_dict(),
            "artifacts": {name: sha256_bytes((arm_dir / name).read_bytes()) for name in ARM_FILES},
        }
    manifest = {
        "schema": "repliclaw.case_manifest/v1",
        "case": case.case_id,
        "case_version": case.case_version,
        "case_sha256": case.sha256,
        "target_model_id": case.target_model_id,
        "engine": engine_metadata(),
        "runtime": {"offline": True, "deterministic": True},
        "reproduce": "replay.sh",
        "arms": arms,
    }
    _write_json(Path(out_root) / "manifest.json", manifest)
    return Path(out_root) / "manifest.json"


# ---------------------------------------------------------------------------
# Public API (contract §5): run_case / run_canonical / replay
# ---------------------------------------------------------------------------


def run_case(
    case: CaseSpec,
    intervention: InterventionSpec,
    *,
    seed: int = 0,
    out_root: Optional[Path] = None,
) -> InterventionRun:
    """Execute one arm; persist deterministic artifacts under ``out_root``."""
    if intervention.case_id != case.case_id:
        raise ValueError(
            f"intervention {intervention.intervention_id} targets case "
            f"{intervention.case_id}, not {case.case_id}"
        )
    effective = intervention.resolve(case)
    run = SimpleAuditExecutor(seed=seed).run(case, intervention, effective)
    if out_root is not None:
        hashes = persist_arm(run, effective, out_root)
        run = run.model_copy(update={"artifact_hashes": hashes})
    return run


def run_canonical(
    case: CaseSpec,
    interventions: List[InterventionSpec],
    *,
    seed: int = 0,
    out_root: Path,
) -> Dict[str, InterventionRun]:
    """Run every arm for the case and pin the case-level manifest."""
    runs: Dict[str, InterventionRun] = {}
    for intervention in interventions:
        runs[intervention.intervention_id] = run_case(
            case, intervention, seed=seed, out_root=out_root
        )
    write_case_manifest(case, out_root, runs)
    return runs


def replay(case_id: str, out_root: Path) -> bool:
    """Re-execute the pinned canonical case; True iff the run is genuine.

    Two independent checks, mirroring ``verify_execution`` (f02):
    * Pass 1 — the STORED arm files match their pinned sha256 (catches
      post-hoc tampering / swapped artifacts on disk).
    * Pass 2 — re-execution in a clean temp dir reproduces every pinned
      arm file's sha256 (catches forged manifests / self-attestation).

    Wall-clock timestamps are not compared.
    """
    import shutil

    manifest_path = Path(out_root) / "manifest.json"
    if not manifest_path.exists():
        return False
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    case = load_case(case_id)
    if case.sha256 != manifest.get("case_sha256"):
        return False
    interventions = {i.intervention_id: i for i in load_interventions(case_id)}

    # Pass 1: the STORED arm files must match their pinned hashes
    # (catches post-hoc tampering / swapped artifacts on disk).
    for arm_id, pinned in sorted(manifest.get("arms", {}).items()):
        stored_dir = Path(out_root) / "interventions" / arm_id
        for name, pin in sorted(pinned.get("artifacts", {}).items()):
            reg = stored_dir / name
            if not reg.exists() or sha256_bytes(reg.read_bytes()) != pin:
                return False

    # Pass 2: re-execution must reproduce the pinned artifacts exactly.
    replay_root = Path(out_root) / ".replay"
    if replay_root.exists():
        shutil.rmtree(replay_root)
    replay_root.mkdir(parents=True, exist_ok=True)
    try:
        for arm_id, pinned in sorted(manifest.get("arms", {}).items()):
            intervention = interventions.get(arm_id)
            if intervention is None:
                return False
            seed = int(pinned.get("seed", 0))
            run_case(case, intervention, seed=seed, out_root=replay_root)
            arm_dir = replay_root / "interventions" / arm_id
            for name, pin in sorted(pinned.get("artifacts", {}).items()):
                reg = arm_dir / name
                if not reg.exists():
                    return False
                if sha256_bytes(reg.read_bytes()) != pin:
                    return False
    finally:
        shutil.rmtree(replay_root, ignore_errors=True)
    return True


__all__ = [
    "ARM_FILES",
    "InterventionRun",
    "SimpleAuditExecutor",
    "case_root",
    "engine_metadata",
    "load_case",
    "load_interventions",
    "persist_arm",
    "replay",
    "run_canonical",
    "run_case",
    "write_case_manifest",
]
