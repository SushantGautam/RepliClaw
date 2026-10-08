"""Case-agnostic counterfactual case-runner base (P06 minimal local runner).

The real P02 counterfactual package (``CaseSpec`` / ``InterventionSpec`` /
``SimpleAuditExecutor``) lives on the ``p02`` branch and is NOT present in this
worktree base (``b5f7bfb``). The mission for P06 is to add a *second, genuinely
independent* scientific case; the concrete P02 wiring happens at P07
integration. To keep this branch self-contained and to avoid colliding with the
P02 branch, this module provides the *smallest* case-agnostic runner plumbing
needed to execute a frozen, deterministic, OFFLINE counterfactual experiment
with a sealed oracle:

* canonical hashing  -- compact, key-sorted JSON -> stable sha256 (so the same
  case/config/seed reproduces byte-identical artifacts),
* per-arm persistence -- deterministic arm files (NO wall-clock timestamps) plus
  a ``hashes.json`` pin,
* case-level manifest  -- ``repliclaw.case_manifest/v1`` pinning case sha256,
  engine metadata and every arm's artifact hashes,
* replay verification -- stored arm files match their pins AND a clean re-run in
  a temp dir reproduces every pinned hash,
* engine metadata    -- ``{name, version, git_sha}`` for provenance.

It deliberately has NO dependency on rdkit or pydantic so it can host unrelated
future cases; a concrete case implements the :class:`Case` protocol below.

Contract references: docs/design/EESS_CONTRACTS.md sections 5 (run interface +
replay/single-factor rules) and 7 (artifact layout), and the oracle-leakage rule
in section 6 (the oracle is read ONLY by the judge, never by the arm).
"""
from __future__ import annotations

import hashlib
import json
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

__all__ = [
    "ARM_FILES",
    "ArmRun",
    "Case",
    "canonical_bytes",
    "engine_metadata",
    "persist_arm",
    "replay",
    "run_case",
    "run_canonical",
    "sha256_bytes",
    "write_case_manifest",
]

# Deterministic per-arm files. No wall-clock timestamps live in any of these;
# the started_at/finished_at timestamps are recorded only in the manifest, which
# replay does not compare byte-for-byte.
ARM_FILES = ("config.json", "target_output.json", "stdout.log", "judgment.json")


def canonical_bytes(obj: Any) -> bytes:
    """Compact, key-sorted canonical JSON -> stable sha256 across runs/platforms."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def engine_metadata(name: str, version: str = "", git_sha: str = "") -> Dict[str, str]:
    """Provenance block recorded in the manifest (contract section 5)."""
    return {"name": name, "version": version, "git_sha": git_sha}


@dataclass(frozen=True)
class ArmRun:
    """Frozen record of one arm execution (one intervention)."""

    run_id: str
    case_id: str
    case_version: str
    case_sha256: str
    arm_id: str
    config_sha256: str
    engine: Dict[str, str]
    seed: int
    started_at: str  # ISO-8601; manifest only, never written into ARM_FILES
    finished_at: str
    target_output: Dict[str, Any]
    stdout_log: str
    judgment: Dict[str, Any]
    severity: str
    token_counts: Dict[str, int]
    exit_code: int = 0
    artifact_hashes: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "case_id": self.case_id,
            "case_version": self.case_version,
            "case_sha256": self.case_sha256,
            "arm_id": self.arm_id,
            "config_sha256": self.config_sha256,
            "engine": dict(self.engine),
            "seed": self.seed,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "target_output": self.target_output,
            "stdout_log": self.stdout_log,
            "judgment": self.judgment,
            "severity": self.severity,
            "token_counts": dict(self.token_counts),
            "exit_code": self.exit_code,
            "artifact_hashes": dict(self.artifact_hashes),
        }


class Case(ABC):
    """Protocol a concrete counterfactual case implements.

    The ARM (``measure_arm``) must be a pure function of the frozen case data +
    the single-factor intervention + seed, and must NEVER read the sealed
    oracle. The JUDGE (``judge_arm``) is the only code path allowed to open the
    oracle (contract section 6).
    """

    case_id: str = ""
    case_version: str = "v1"
    target_measurement_id: str = ""

    @abstractmethod
    def case_sha256(self) -> str:
        """sha256 of the frozen case data (the immutable 'input' identity)."""

    @abstractmethod
    def arm_ids(self) -> List[str]:
        """Ordered list of intervention arm ids for this case."""

    @abstractmethod
    def effective_config(self, arm_id: str) -> Dict[str, Any]:
        """The single-factor effective config for ``arm_id`` (hashed -> config_sha256)."""

    @abstractmethod
    def measure_arm(self, arm_id: str, seed: int) -> Dict[str, Any]:
        """The ARM: measure the intervention outcome. Must NOT read the oracle."""

    @abstractmethod
    def judge_arm(self, arm_id: str, target_output: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """The JUDGE: score ``target_output`` against the sealed oracle.

        Returns ``(judgment, severity)`` where ``severity`` in
        ``{"pass", "mismatch"}``. This is the only place the oracle is read.
        """

    def stdout_log(self, arm_id: str) -> str:
        """Deterministic per-arm log line (no wall clock)."""
        return (
            f"offline deterministic run; arm={arm_id}; "
            "no LLM, no network, 0 real tokens\n"
        )

    @abstractmethod
    def engine_metadata(self) -> Dict[str, str]:
        """Engine provenance ``{name, version, git_sha}``."""


# ---------------------------------------------------------------------------
# Persistence (contract section 7 layout, compact)
# ---------------------------------------------------------------------------


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


# Fields in a judge's judgment that name the sealed ground truth. They are
# kept in the in-memory ArmRun.judgment (for internal validation/replay) but
# stripped from the PERSISTED public artifacts, per EESS_CONTRACTS section 6
# (oracle values live ONLY in the sealed oracle file, never in
# investigator-visible artifacts).
_PERSISTED_JUDGMENT_DROP = frozenset({"expected_mean_delta_logp", "oracle_schema"})


def persist_arm(run: ArmRun, effective_config: Dict[str, Any], out_root: Path) -> Dict[str, str]:
    """Persist deterministic artifacts for one arm and pin their sha256.

    The PERSISTED ``judgment.json`` is a public view: any field that names the
    sealed ground truth (``expected_mean_delta_logp``, ``oracle_schema``) is
    stripped before writing, per EESS_CONTRACTS section 6 (oracle values live
    ONLY in the sealed oracle file, never in investigator-visible artifacts).
    The in-memory ``ArmRun.judgment`` is left intact for internal validation.
    """
    arm_dir = Path(out_root) / "interventions" / run.arm_id
    arm_dir.mkdir(parents=True, exist_ok=True)
    (arm_dir / "config.json").write_bytes(canonical_bytes(effective_config))
    (arm_dir / "target_output.json").write_bytes(canonical_bytes(run.target_output))
    (arm_dir / "stdout.log").write_bytes(run.stdout_log.encode("utf-8"))
    public_judgment = {
        k: v for k, v in run.judgment.items() if k not in _PERSISTED_JUDGMENT_DROP
    }
    (arm_dir / "judgment.json").write_bytes(canonical_bytes(public_judgment))
    hashes = {name: sha256_bytes((arm_dir / name).read_bytes()) for name in ARM_FILES}
    (arm_dir / "hashes.json").write_bytes(canonical_bytes(hashes))
    return hashes


def write_case_manifest(case: "Case", out_root: Path, runs: Dict[str, ArmRun]) -> Path:
    """Pin the case-level manifest (contract section 7) that ``replay`` verifies."""
    arms: Dict[str, Any] = {}
    for arm_id in sorted(runs):
        run = runs[arm_id]
        arm_dir = Path(out_root) / "interventions" / arm_id
        entry = run.to_dict()
        # Public view: strip ground-truth fields from the manifest judgment
        # (section 6: oracle values only in the sealed oracle file).
        entry["judgment"] = {
            k: v for k, v in entry["judgment"].items() if k not in _PERSISTED_JUDGMENT_DROP
        }
        entry["artifacts"] = {
            name: sha256_bytes((arm_dir / name).read_bytes()) for name in ARM_FILES
        }
        arms[arm_id] = entry
    manifest = {
        "schema": "repliclaw.case_manifest/v1",
        "case": case.case_id,
        "case_version": case.case_version,
        "case_sha256": case.case_sha256(),
        "target_measurement_id": case.target_measurement_id,
        "engine": case.engine_metadata(),
        "runtime": {"offline": True, "deterministic": True},
        "reproduce": "replay.sh",
        "arms": arms,
    }
    _write_json(Path(out_root) / "manifest.json", manifest)
    return Path(out_root) / "manifest.json"


# ---------------------------------------------------------------------------
# Public API (contract section 5): run_case / run_canonical / replay
# ---------------------------------------------------------------------------


def run_case(case: "Case", arm_id: str, *, seed: int = 0, out_root: Optional[Path] = None) -> ArmRun:
    """Execute one arm; persist deterministic artifacts under ``out_root`` if given."""
    if arm_id not in set(case.arm_ids()):
        raise ValueError(f"unknown arm {arm_id!r} for case {case.case_id!r}")
    effective = case.effective_config(arm_id)
    started = _now_iso()
    target_output = case.measure_arm(arm_id, seed)
    judgment, severity = case.judge_arm(arm_id, target_output)
    finished = _now_iso()

    run = ArmRun(
        run_id=f"{case.case_id}::{arm_id}::seed{seed}",
        case_id=case.case_id,
        case_version=case.case_version,
        case_sha256=case.case_sha256(),
        arm_id=arm_id,
        config_sha256=sha256_bytes(canonical_bytes(effective)),
        engine=case.engine_metadata(),
        seed=int(seed),
        started_at=started,
        finished_at=finished,
        target_output=target_output,
        stdout_log=case.stdout_log(arm_id),
        judgment=judgment,
        severity=severity,
        token_counts={"real_token_calls": 0},  # offline: no LLM / no network
        exit_code=0,
        artifact_hashes={},
    )
    if out_root is not None:
        hashes = persist_arm(run, effective, Path(out_root))
        run = ArmRun(**{**run.__dict__, "artifact_hashes": hashes})
    return run


def run_canonical(case: "Case", out_root: Path, *, seed: int = 0) -> Dict[str, ArmRun]:
    """Run every arm for the case and pin the case-level manifest."""
    runs: Dict[str, ArmRun] = {}
    for arm_id in case.arm_ids():
        runs[arm_id] = run_case(case, arm_id, seed=seed, out_root=out_root)
    write_case_manifest(case, out_root, runs)
    return runs


def replay(case: "Case", out_root: Path) -> bool:
    """Re-execute the pinned canonical case; True iff the run is genuine.

    Two independent checks (mirrors the P02 replay contract):
    * Pass 1 -- the STORED arm files match their pinned sha256 (catches
      post-hoc tampering / swapped artifacts on disk).
    * Pass 2 -- a clean re-execution in a temp dir reproduces every pinned arm
      file's sha256 (catches forged manifests / self-attestation).

    Wall-clock timestamps are not compared.
    """
    manifest_path = Path(out_root) / "manifest.json"
    if not manifest_path.exists():
        return False
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("case_sha256") != case.case_sha256():
        return False
    runs = manifest.get("arms", {})

    # Pass 1: stored arm files must match their pinned hashes.
    for arm_id, pinned in sorted(runs.items()):
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
        for arm_id, pinned in sorted(runs.items()):
            seed = int(pinned.get("seed", 0))
            run_case(case, arm_id, seed=seed, out_root=replay_root)
            arm_dir = replay_root / "interventions" / arm_id
            for name, pin in sorted(pinned.get("artifacts", {}).items()):
                reg = arm_dir / name
                if not reg.exists() or sha256_bytes(reg.read_bytes()) != pin:
                    return False
    finally:
        shutil.rmtree(replay_root, ignore_errors=True)
    return True
