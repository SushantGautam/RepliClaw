"""Idempotent run-state helper (shared benchmark infrastructure).

Every benchmark run directory owns exactly one ``run_state.json``. The
state machine is::

    (absent) --begin()--> running --mark_finished(record)--> finished

Semantics (these are the contract, and the tests assert them):

* **Atomic writes.** State is written as ``run_state.json.tmp`` in the same
  directory, fsync'd, then ``os.replace``'d onto the final name (the same
  pattern the escrow ledger uses for ``ledger_root.json``). A crashed
  writer therefore never leaves a torn file.
* **Idempotent begin.** ``begin()`` on an already-running state is a no-op
  that bumps ``attempts`` (crash-and-restart evidence). ``begin()`` on a
  finished state raises :class:`RunAlreadyFinished` — a finished run is
  never re-opened, which is what makes "no double-record of a finished
  run" hold without caller-side bookkeeping.
* **Idempotent finish.** ``mark_finished(record)`` on an already-finished
  state is a no-op when the recorded payload is byte-identical (same
  canonical SHA-256); a *different* record for the same run raises
  :class:`StateConflict` (fail-loud, mirroring the escrow ledger's
  ``DuplicateCommitment``).
* **Resume contract.** ``is_finished``/``record()`` let a driver skip
  finished runs; a ``running`` state with no liveness guarantee is simply
  resumable — ``begin()`` accepts it.

No locks: the state machine is single-writer per run directory by lane
design (one process per run id). Cross-process safety is the escrow
ledger's job, not this file's.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from repliclaw.canonical import canonical_json, sha256_hex

from .records import RunRecord

RUN_STATE_SCHEMA = "repliclaw.run_state/v1"
RUN_STATE_FILENAME = "run_state.json"

STATE_RUNNING = "running"
STATE_FINISHED = "finished"


class RunStateError(RuntimeError):
    """Base error for run-state contract violations."""


class RunAlreadyFinished(RunStateError):
    """``begin()`` was called on a run whose state is already finished."""


class StateConflict(RunStateError):
    """A different finished record was submitted for an already-finished run."""


def run_id_for(case: str, arm: str, seed: int) -> str:
    """Conventional run id ``{case}::{arm}::seed{n}`` (matches run_record schema)."""
    return f"{case}::{arm}::seed{int(seed)}"


def _now_iso_zulu() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _atomic_write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    data = (canonical_json(obj) + "\n").encode("utf-8")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    # Fsync the directory BEFORE the rename so the tmp entry is durable first;
    # a crash after rename then only risks losing the final entry update, not
    # the file content itself.
    dir_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)
    os.replace(tmp, path)


@dataclass
class _State:
    run_id: str
    state: str
    attempts: int = 0
    started_at: str = ""
    updated_at: str = ""
    record: Optional[Dict[str, Any]] = None
    record_sha256: Optional[str] = None


class RunState:
    """File-backed idempotent state machine for one benchmark run."""

    def __init__(self, run_dir: Path | str, run_id: str) -> None:
        self.path = Path(run_dir) / RUN_STATE_FILENAME
        self.run_id = run_id
        self._state: Optional[_State] = self._load()

    # -- persistence ------------------------------------------------------

    def _load(self) -> Optional[_State]:
        if not self.path.is_file():
            return None
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RunStateError(f"run state file is corrupt: {self.path}: {exc}") from exc
        if raw.get("schema") != RUN_STATE_SCHEMA:
            raise RunStateError(f"run state file has unexpected schema: {raw.get('schema')!r}")
        if raw.get("run_id") != self.run_id:
            raise RunStateError(
                f"run state file belongs to run {raw.get('run_id')!r}, not {self.run_id!r}"
            )
        return _State(
            run_id=self.run_id,
            state=raw["state"],
            attempts=int(raw.get("attempts", 0)),
            started_at=raw.get("started_at", ""),
            updated_at=raw.get("updated_at", ""),
            record=raw.get("record"),
            record_sha256=raw.get("record_sha256"),
        )

    def _persist(self, state: _State) -> None:
        _atomic_write_json(
            self.path,
            {
                "schema": RUN_STATE_SCHEMA,
                "run_id": state.run_id,
                "state": state.state,
                "attempts": state.attempts,
                "started_at": state.started_at,
                "updated_at": state.updated_at,
                "record": state.record,
                "record_sha256": state.record_sha256,
            },
        )
        self._state = state

    # -- queries ----------------------------------------------------------

    @property
    def exists(self) -> bool:
        return self._state is not None

    @property
    def is_running(self) -> bool:
        return self._state is not None and self._state.state == STATE_RUNNING

    @property
    def is_finished(self) -> bool:
        return self._state is not None and self._state.state == STATE_FINISHED

    @property
    def attempts(self) -> int:
        return self._state.attempts if self._state else 0

    def record(self) -> Optional[RunRecord]:
        """The finished run record, or None if not finished."""
        if not self.is_finished or self._state is None or self._state.record is None:
            return None
        return RunRecord.from_dict(self._state.record)

    def reload(self) -> "RunState":
        """Re-read from disk (use after out-of-band changes)."""
        reloaded: Optional[_State] = self._load()
        self._state = reloaded
        return self

    # -- transitions ------------------------------------------------------

    def begin(self) -> _State:
        """Enter (or re-enter) the running state.

        Idempotent for a running state (bumps ``attempts``). Raises
        :class:`RunAlreadyFinished` for a finished state — finished runs
        are terminal.
        """
        now = _now_iso_zulu()
        if self._state is None:
            state = _State(
                run_id=self.run_id,
                state=STATE_RUNNING,
                attempts=1,
                started_at=now,
                updated_at=now,
            )
            self._persist(state)
            self._state = state
            return state
        if self._state.state == STATE_RUNNING:
            self._state.attempts += 1
            self._state.updated_at = now
            self._persist(self._state)
            return self._state
        raise RunAlreadyFinished(f"run {self.run_id} is already finished; refusing to re-open")

    def mark_finished(self, run_record: RunRecord) -> _State:
        """Transition running -> finished, recording ``run_record``.

        Idempotent: a byte-identical record on a finished state returns the
        existing state. A *different* record raises :class:`StateConflict`.
        Calling before ``begin()`` raises :class:`RunStateError`.
        """
        if run_record.run_id != self.run_id:
            raise RunStateError(
                f"record run_id {run_record.run_id!r} != state run_id {self.run_id!r}"
            )
        now = _now_iso_zulu()
        if self._state is not None and self._state.state == STATE_FINISHED:
            record_sha = sha256_hex(canonical_json(run_record.to_dict()))
            if self._state.record_sha256 is None:
                raise StateConflict(
                    f"run {self.run_id} already finished but has no recorded sha256 "
                    f"(re-recorded {record_sha[:12]}…)"
                )
            if self._state.record_sha256 == record_sha:
                return self._state  # idempotent no-op
            raise StateConflict(
                f"run {self.run_id} already finished with a different record "
                f"(recorded {self._state.record_sha256[:12]}… vs {record_sha[:12]}…)"
            )
        if self._state is None or self._state.state != STATE_RUNNING:
            raise RunStateError(f"run {self.run_id} must begin() before mark_finished()")

        record = run_record.to_dict()
        self._state.state = STATE_FINISHED
        self._state.record = record
        self._state.record_sha256 = sha256_hex(canonical_json(record))
        self._state.updated_at = now
        self._persist(self._state)
        return self._state


__all__ = [
    "RUN_STATE_SCHEMA",
    "RUN_STATE_FILENAME",
    "STATE_RUNNING",
    "STATE_FINISHED",
    "RunState",
    "RunStateError",
    "RunAlreadyFinished",
    "StateConflict",
    "run_id_for",
]
