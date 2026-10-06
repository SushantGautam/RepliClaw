"""Run provenance capture and verification (shared benchmark infrastructure).

:func:`capture_provenance` writes ``provenance.json`` into a run directory:
upstream repo SHAs (from local clones when available), dataset file sha256s,
installed dependency pins via ``importlib.metadata``, the RepliClaw git SHA
at run time, and the Python/platform environment.

:func:`verify_provenance` re-reads the file, checks it against the
``repliclaw.provenance/v1`` schema, and re-hashes every dataset file to
detect drift after the run.

All repo access is read-only ``git`` subprocess calls scoped to the given
path; any failure degrades to an explicit ``unknown`` marker rather than
raising, so provenance capture never breaks a run.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from repliclaw.canonical import canonical_json

from .records import Environment, Provenance, UpstreamRepo
from .validation import validate_record

PROVENANCE_FILENAME = "provenance.json"


class ProvenanceError(RuntimeError):
    """Provenance capture or verification failure."""


def _now_iso_zulu() -> str:
    """UTC timestamp with Z suffix (the schema's required shape)."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _git(repo: Path, *args: str) -> tuple[bool, str]:
    """Read-only git query. Returns (ok, stdout_stripped).

    ``ok`` is False only when the git command itself failed (not a repo, no
    git binary, non-zero exit). A command that succeeds with EMPTY output
    (e.g. ``status --porcelain`` on a clean tree) is (True, "") — that is a
    real, meaningful result and must not be conflated with a failure.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False, ""
    if out.returncode != 0:
        return False, ""
    return True, out.stdout.strip()


def git_head_sha(repo: Path) -> Optional[str]:
    ok, out = _git(repo, "rev-parse", "HEAD")
    return out if ok and out else None


def git_dirty(repo: Path) -> Optional[bool]:
    """True = working tree has uncommitted changes; False = clean; None = unresolvable."""
    ok, out = _git(repo, "status", "--porcelain")
    if not ok:
        return None
    return bool(out)


def package_pins(names: Optional[List[str]] = None) -> Dict[str, str]:
    """Installed distribution name -> version via importlib.metadata.

    With no ``names``, pins the full distribution set (excluding itself is
    the caller's choice). Unknown names are silently omitted — pins are
    evidence, not a hard requirement.
    """
    from importlib import metadata

    try:
        dists = sorted(
            {d.metadata["Name"] for d in metadata.distributions() if d.metadata["Name"] is not None}
        )
    except Exception:  # pragma: no cover - metadata enumeration is best-effort
        dists = []
    if names is not None:
        wanted = {n.lower() for n in names}
        dists = [n for n in dists if n.lower() in wanted]
    pins: Dict[str, str] = {}
    for name in dists:
        try:
            pins[name] = metadata.version(name)
        except metadata.PackageNotFoundError:  # pragma: no cover
            continue
    return pins


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class RepoPin:
    """An upstream repository to pin: local clone path and/or its URL."""

    name: str
    path: Optional[Path] = None
    url: Optional[str] = None


def capture_provenance(
    run_dir: Path,
    run_id: str,
    *,
    upstream: Optional[List[RepoPin]] = None,
    dataset_files: Optional[Dict[str, Path]] = None,
    repo: Optional[Path] = None,
    extra_env: Optional[Dict[str, str]] = None,
    dependency_names: Optional[List[str]] = None,
    captured_at: Optional[str] = None,
) -> Provenance:
    """Capture provenance into ``run_dir/provenance.json`` and return the record.

    ``upstream`` repos are resolved from their local clone (read-only git);
    capture is FAIL-LOUD: any pin whose clone is missing or whose SHA cannot
    be resolved raises :class:`ProvenanceError` (no URL-only placeholder is
    recorded, and :func:`verify_provenance` has no fill-in-later path).
    ``dataset_files`` maps a stable relative
    name to a local path; each is hashed. The RepliClaw SHA is taken from
    ``repo`` (default: this source tree) and MUST resolve — capture raises
    :class:`ProvenanceError` otherwise, because a run with unknown origin is
    not reproducible.
    """
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    repo = repo or Path(__file__).resolve().parents[3]
    repliclaw_sha = git_head_sha(repo)
    if repliclaw_sha is None:
        raise ProvenanceError(
            f"cannot resolve RepliClaw git HEAD under {repo}; provenance capture is fail-loud"
        )
    dirty = git_dirty(repo)
    if dirty is None:
        raise ProvenanceError(f"cannot read git status under {repo}")

    upstream_repos: Dict[str, UpstreamRepo] = {}
    for pin in upstream or ():
        sha = git_head_sha(pin.path) if pin.path else None
        if sha is None:
            if pin.url is None:
                raise ProvenanceError(f"upstream {pin.name!r}: no local clone and no url")
            raise ProvenanceError(
                f"upstream {pin.name!r}: local clone at {pin.path} has no HEAD; "
                "provenance must pin a real SHA"
            )
        upstream_repos[pin.name] = UpstreamRepo(url=pin.url, sha=sha)

    dataset_sha256s: Dict[str, str] = {}
    for name, path in (dataset_files or {}).items():
        p = Path(path)
        if not p.is_file():
            raise ProvenanceError(f"dataset file {name!r} missing: {p}")
        dataset_sha256s[name] = sha256_file(p)

    env = Environment(
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        os_version=platform.version(),
        os_release=platform.release(),
        timezone=time.tzname[0] if time.daylight or time.tzname[0] else "UTC",
        vars=dict(extra_env or {}),
    )

    record = Provenance(
        run_id=run_id,
        captured_at=captured_at or _now_iso_zulu(),
        repliclaw_git_sha=repliclaw_sha,
        repliclaw_dirty=dirty,
        dependency_pins=package_pins(dependency_names),
        environment=env,
        upstream_repos=upstream_repos,
        dataset_sha256s=dataset_sha256s,
    )
    report = record.validate()
    if not report.ok:
        raise ProvenanceError("captured provenance fails its own schema: " + "; ".join(map(str, report.errors)))

    (run_dir / PROVENANCE_FILENAME).write_bytes(
        (canonical_json(record.to_dict()) + "\n").encode("utf-8")
    )
    return record


def read_provenance(run_dir: Path) -> Provenance:
    path = Path(run_dir) / PROVENANCE_FILENAME
    if not path.is_file():
        raise ProvenanceError(f"no provenance record at {path}")
    return Provenance.from_dict(json.loads(path.read_text(encoding="utf-8")))


def verify_provenance(
    run_dir: Path,
    *,
    dataset_files: Optional[Dict[str, Path]] = None,
    expected_repliclaw_sha: Optional[str] = None,
) -> List[str]:
    """Verify a run's provenance; returns a list of mismatch strings (empty = OK).

    Checks, in order: schema validity, repliclaw_git_sha (against
    ``expected_repliclaw_sha`` when given), and — for every name in
    ``dataset_files`` — that the current file hash still equals the
    recorded one. A missing recorded hash or a missing file is a mismatch,
    not an exception.
    """
    issues: List[str] = []
    try:
        raw = json.loads((Path(run_dir) / PROVENANCE_FILENAME).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"unreadable: {type(exc).__name__}: {exc}"]

    def _schema_issues(payload: Any) -> List[str]:
        report = validate_record("provenance", payload)
        return [f"schema: {err}" for err in report.errors]

    if not isinstance(raw, dict):
        return [f"schema: top-level record must be an object, got {type(raw).__name__}"]

    # Schema first (works on partially-tampered payloads), then typed load.
    issues.extend(_schema_issues(raw))
    try:
        record = Provenance.from_dict(raw)
    except (KeyError, TypeError, ValueError) as exc:
        issues.append(f"unparseable: {type(exc).__name__}: {exc}")
        return issues

    if expected_repliclaw_sha is not None and record.repliclaw_git_sha != expected_repliclaw_sha:
        issues.append(
            f"repliclaw git sha mismatch: recorded {record.repliclaw_git_sha} != expected {expected_repliclaw_sha}"
        )

    for name, path in (dataset_files or {}).items():
        recorded = record.dataset_sha256s.get(name)
        p = Path(path)
        if recorded is None:
            issues.append(f"dataset {name!r}: no hash recorded in provenance")
            continue
        if not p.is_file():
            issues.append(f"dataset {name!r}: file missing at {p}")
            continue
        actual = sha256_file(p)
        if actual != recorded:
            issues.append(f"dataset {name!r}: sha256 drift recorded={recorded[:12]}… actual={actual[:12]}…")
    return issues


__all__ = [
    "PROVENANCE_FILENAME",
    "ProvenanceError",
    "RepoPin",
    "capture_provenance",
    "read_provenance",
    "verify_provenance",
    "package_pins",
    "sha256_file",
    "git_head_sha",
    "git_dirty",
]
