"""F02 — execution honesty: no model self-attestation.

Today `finding["executable"]` is pure model self-attestation, and
`verdict.py` already WEIGHTS executable evidence — so a model can buy verdict
confidence with an unverified flag. This module inverts that at the source:

  * A model's self-claim alone can NEVER produce an executable-stamped
    evidence row.
  * Only an `ExecutionRecord` produced by a REAL subprocess run
    (`run_python_execution`) and independently re-checked
    (`verify_execution`) can carry the stamp.

Design notes:
  * `ExecutionRecord.verified` / `.verify_report` are PROTECTED fields:
    plain construction / `model_validate` (the paths available to an
    investigator) always force them to the honest defaults. Only the
    verifier — the deterministic investigator right after its subprocess
    run, and the protocol via `from_verified_payload` — can stamp them.
  * The record carries the exact `code` that ran, and
    `artifact_hashes["script.py"]` pins its sha256. Verification re-runs
    that code in a CLEAN temp directory (independent of the investigator's
    cwd) and compares script hash, exit_code, normalized stdout, and
    produced-artifact hashes. A doctored record (edited stdout/exit
    code/script) fails, and a record of a DIFFERENT computation fails the
    script-hash check.
  * Persistence mirrors the RunStore pattern: `{root}/execution/records/
    *.json` + append-only `manifest.jsonl`.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExecutionRecord(BaseModel):
    """A REAL, subprocess-executed computation with full provenance.

    Investigators build records via `run_python_execution` (never by hand).
    `verified` / `verify_report` can ONLY be set by the verifier through
    `from_verified_payload`; any self-stamp in a payload is neutralized.
    """

    model_config = ConfigDict(protected_namespaces=())

    command: str  # the exact command line that was executed
    cwd: str  # working directory of the subprocess
    code: str = ""  # the exact snippet source that was executed
    exit_code: int
    stdout: str
    stderr: str
    duration_s: float
    started_at: str  # ISO-8601 UTC
    agent_id: str  # which investigator ran it
    artifact_hashes: Dict[str, str] = Field(default_factory=dict)  # sha256 by relpath
    env_notes: str = ""

    # Verifier-only: an investigator cannot stamp a record verified=True.
    verified: bool = False
    verify_report: str = ""

    @field_validator("verified", mode="before")
    @classmethod
    def _verified_never_self_set(cls, v: Any) -> bool:
        return False

    @field_validator("verify_report", mode="before")
    @classmethod
    def _report_never_self_set(cls, v: Any) -> str:
        return ""

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_verified_payload(
        cls, payload: Dict[str, Any], verified: bool, report: str
    ) -> "ExecutionRecord":
        """The ONLY path to a verifier-stamped record. Strips any
        investigator self-stamp from the payload first."""
        d = dict(payload)
        d.pop("verified", None)
        d.pop("verify_report", None)
        rec = cls.model_validate(d)
        rec.verified = verified
        rec.verify_report = report
        return rec


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize_stdout(text: str) -> str:
    """Normalize volatile formatting so a re-run in a different directory
    compares equal: unify newlines, strip trailing whitespace per line and
    surrounding blank lines. Numeric output is kept verbatim — it must
    reproduce exactly."""
    lines = [ln.rstrip() for ln in (text or "").replace("\r\n", "\n").split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def _script_filename(command: str) -> Optional[str]:
    for tok in (command or "").split():
        if tok.endswith(".py"):
            return tok.rsplit("/", 1)[-1]
    return None


def _recheck_timeout(record: ExecutionRecord) -> int:
    # Generous multiple of the original duration so a slow-but-faithful
    # re-run is not mistaken for a divergence.
    return max(30, int(record.duration_s) * 5 + 15)


def run_python_execution(
    code: str,
    cwd: str,
    agent_id: str,
    timeout_s: int = 20,
    env_notes: str = "",
) -> ExecutionRecord:
    """Really execute `code` in a subprocess of the current interpreter.

    Writes the snippet to `cwd/script.py`, runs `<sys.executable> script.py`,
    captures exit code / stdout / stderr / duration / start time, and hashes
    the script (and any files the snippet produced under `cwd`) as artifact
    hashes. A crash or timeout is a normal outcome: it yields a non-zero
    exit_code, not a raised exception.
    """
    cwd_p = Path(cwd)
    cwd_p.mkdir(parents=True, exist_ok=True)
    script = cwd_p / "script.py"
    script.write_text(code, encoding="utf-8")

    cmd = [sys.executable, str(script)]
    started = datetime.now(timezone.utc)
    started_at = started.isoformat()
    t0 = started.timestamp()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd_p),
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        exit_code: int = proc.returncode
        stdout: str = proc.stdout or ""
        stderr: str = proc.stderr or ""
        notes = env_notes
    except subprocess.TimeoutExpired as exc:
        exit_code = -1
        out = exc.stdout or ""
        stdout = out if isinstance(out, str) else ""
        err = exc.stderr or ""
        stderr = (err if isinstance(err, str) else "") + f"\nTIMEOUT after {timeout_s}s"
        notes = (env_notes + " | " if env_notes else "") + f"timed_out_after_{timeout_s}s"
    duration = datetime.now(timezone.utc).timestamp() - t0

    artifact_hashes: Dict[str, str] = {"script.py": _sha256(script)}
    for f in sorted(cwd_p.rglob("*")):
        if f.is_file() and f != script:
            artifact_hashes[f.relative_to(cwd_p).as_posix()] = _sha256(f)
    # Keep the caller's directory clean; the record carries the source (`code`)
    # and the hash, so the file itself is not needed for verification.
    script.unlink(missing_ok=True)

    return ExecutionRecord(
        command=" ".join(cmd),
        cwd=str(cwd_p),
        code=code,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_s=round(duration, 4),
        started_at=started_at,
        agent_id=agent_id,
        artifact_hashes=artifact_hashes,
        env_notes=notes,
        # Honest by construction: a fresh investigator run is never pre-verified.
        verified=False,
    )


def verify_execution(record: ExecutionRecord, out_dir: str | Path) -> Tuple[bool, str]:
    """Independent re-check of an ExecutionRecord.

    Re-runs the recorded `code` in a CLEAN directory under `out_dir`
    (reconstructing any input files the record's artifact hashes pin), then
    compares:
      1. script hash   — re-run bytes vs recorded `artifact_hashes["script.py"]`
      2. exit_code     — re-run vs recorded
      3. stdout        — normalized re-run vs normalized recorded
      4. artifacts     — sha256 of files the re-run produced vs recorded hashes
    Returns `(verified, report)`; failures quote the exact mismatch.
    """
    out = Path(out_dir)
    check = out / "recheck"
    check.mkdir(parents=True, exist_ok=True)
    failures: List[str] = []

    script_name = _script_filename(record.command) or "script.py"
    if not record.code:
        return False, "FAILED: record carries no script source to re-execute"

    # Reconstruct input files the record pins by hash (inputs only; files
    # the script PRODUCED must simply be (re)produced with the same hash).
    inputs: Dict[str, bytes] = {}
    for name in record.artifact_hashes:
        if name == script_name:
            continue
        src = Path(record.cwd) / name
        if src.exists():
            inputs[name] = src.read_bytes()
    for name, data in inputs.items():
        (check / name).write_bytes(data)

    rec_script = check / script_name
    rec_script.write_text(record.code, encoding="utf-8")

    # --- Re-run in the clean dir. ------------------------------------------
    try:
        proc = subprocess.run(
            [sys.executable, str(rec_script)],
            cwd=str(check),
            capture_output=True,
            text=True,
            timeout=_recheck_timeout(record),
        )
        got_exit: int = proc.returncode
        got_stdout: str = proc.stdout or ""
    except subprocess.TimeoutExpired:
        got_exit, got_stdout = -1, ""
        failures.append("re-run timed out (recorded run did not)")

    # --- Compare script hash (catches swapped/edited computation). ---------
    recorded_script_hash = record.artifact_hashes.get(script_name) or record.artifact_hashes.get(
        "script.py"
    )
    if recorded_script_hash and _sha256(rec_script) != recorded_script_hash:
        failures.append(
            f"script hash mismatch: recorded {recorded_script_hash[:16]}… vs "
            f"re-run source {_sha256(rec_script)[:16]}… (computation differs from record)"
        )

    # --- Compare exit code. --------------------------------------------------
    if got_exit != record.exit_code:
        failures.append(f"exit_code mismatch: recorded {record.exit_code} vs re-run {got_exit}")

    # --- Compare normalized stdout. -----------------------------------------
    if _normalize_stdout(got_stdout) != _normalize_stdout(record.stdout):
        failures.append(
            "stdout mismatch:\n"
            f"  recorded: {_truncate(record.stdout)}\n"
            f"  re-run:   {_truncate(got_stdout)}"
        )

    # --- Compare produced artifact hashes. ----------------------------------
    for name, rec_h in record.artifact_hashes.items():
        if name == script_name or name in inputs:
            continue
        produced = check / name
        if not produced.exists():
            failures.append(f"produced artifact missing on re-run: {name}")
        elif _sha256(produced) != rec_h:
            failures.append(
                f"artifact hash mismatch for {name}: recorded {rec_h[:16]}… vs "
                f"re-run {_sha256(produced)[:16]}…"
            )

    if failures:
        return False, "FAILED: " + " | ".join(failures)
    return True, (
        "OK: re-executed in clean temp dir; script hash, exit_code, normalized "
        "stdout, and produced-artifact hashes all reproduce."
    )


def _truncate(text: str, n: int = 400) -> str:
    t = text or ""
    return t if len(t) <= n else t[:n] + f"… (+{len(t) - n} chars)"


# ---------------------------------------------------------------------------
# Run-store-compatible persistence (append-only, run-local)
# ---------------------------------------------------------------------------
def save_execution_record(
    store_root: str | Path, record: ExecutionRecord, evidence_id: str = ""
) -> Path:
    """Persist one record under `{store_root}/execution/` (RunStore pattern):
    `records/{agent}-{digest}.json` + append to `manifest.jsonl`.
    Returns the record file path."""
    exd = Path(store_root) / "execution"
    (exd / "records").mkdir(parents=True, exist_ok=True)
    safe_agent = "".join(c if c.isalnum() or c in "-_" else "-" for c in record.agent_id)[:40]
    safe_agent = safe_agent or "agent"
    digest = hashlib.sha256(
        json.dumps(record.to_dict(), sort_keys=True).encode("utf-8")
    ).hexdigest()[:10]
    path = exd / "records" / f"{safe_agent}-{digest}.json"
    path.write_text(json.dumps(record.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    entry = {
        "record_file": path.name,
        "agent_id": record.agent_id,
        "evidence_id": evidence_id,
        "exit_code": record.exit_code,
        "verified": record.verified,
        "ts": _now(),
    }
    with open(exd / "manifest.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return path


def load_execution_records(store_root: str | Path) -> List[ExecutionRecord]:
    exd = Path(store_root) / "execution" / "records"
    if not exd.exists():
        return []
    out = []
    for p in sorted(exd.glob("*.json")):
        out.append(ExecutionRecord.model_validate(json.loads(p.read_text(encoding="utf-8"))))
    return out
