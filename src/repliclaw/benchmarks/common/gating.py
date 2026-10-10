"""Scorer-only access gate for benchmark ground truth (J-SCI C-SCI-1, S1 residual).

Enforces the "the scorer is the only reader of ground truth" rule at the code
level:

* :class:`ScorerContext` is the ONLY sanctioned reader of resolved ground
  truth. It holds an evaluator-side case index and exposes
  :meth:`ScorerContext.resolve`, which returns the label for a case id and
  records every resolve in an append-only audit log. An explicit ``caller_tag``
  (deterministic — not stack-derived) identifies the reader.
* :func:`assert_no_agent_access` is a canary: it scans agent-visible artifact
  files and raises :class:`GroundTruthLeakError` if any resolved ground-truth
  value from the expected label set is present.
* Ground-truth content is never embedded in a :class:`CaseManifest` or any
  agent-visible record; the manifest carries the pointer only (schema
  ``ground_truth`` stays pointer-only).

The static caller-restriction test (``tests/benchmarks/test_ground_truth_gate.py``)
pins that only the scorer path (and tests) may reference this gate.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Sequence, Union

import pandas as pd

from .records import GroundTruthPointer


class GroundTruthLeakError(RuntimeError):
    """Raised when a resolved ground-truth value is found in agent-visible artifacts."""


@dataclass(frozen=True)
class ResolveAuditEntry:
    """One recorded ground-truth resolve (case_id, UTC timestamp, caller tag)."""

    case_id: str
    timestamp: str
    caller: str


@dataclass
class ResolveAuditLedger:
    """Append-only, process-lifetime ledger of ground-truth resolves.

    A :class:`ScorerContext` that is given a ledger mirrors every
    :class:`ResolveAuditEntry` into it, so audits survive the destruction of
    the context (F-W2-3: the production resolve path in
    ``heldout_ground_truth`` constructs a fresh context per call and would
    otherwise discard its audit log). Use :meth:`entries` to read a snapshot
    (a shallow copy — mutating the returned list never affects the ledger).
    :meth:`clear` exists for test isolation only; production code must not
    call it.
    """

    _entries: List[ResolveAuditEntry] = field(default_factory=list)

    def append(self, entry: ResolveAuditEntry) -> None:
        """Append one resolve record (append-only; no removal API)."""
        self._entries.append(entry)

    def entries(self) -> List[ResolveAuditEntry]:
        """Return a copy of all recorded entries, oldest first."""
        return list(self._entries)

    def clear(self) -> None:
        """Drop all entries. Test isolation only — never call in production."""
        self._entries.clear()


_MODULE_LEDGER = ResolveAuditLedger()


def get_resolve_audit_ledger() -> ResolveAuditLedger:
    """Return the module-level default ledger (evaluator/QA inspection only)."""
    return _MODULE_LEDGER


@dataclass
class ScorerContext:
    """EVALUATOR-ONLY reader of ground truth; the single sanctioned resolve path.

    ``index`` must be keyed by case id (``index["case"]``) and carry
    ``label_column`` (the resolved ground-truth value, e.g.
    ``root_cause_service`` for RCAEval). ``pointer`` is the evaluator-side
    locator recorded on the manifest for provenance; it is never dereferenced
    by lane code. ``clock`` is injectable for deterministic tests. ``ledger``
    is an optional :class:`ResolveAuditLedger`; when provided, every resolve
    is recorded both in this context's ``audit`` list and in the ledger, so
    audits survive contexts that are created and discarded per call.
    """

    index: pd.DataFrame
    label_column: str
    pointer: Optional[GroundTruthPointer] = None
    clock: Callable[[], str] = lambda: datetime.now(timezone.utc).isoformat()
    audit: List[ResolveAuditEntry] = field(default_factory=list)
    ledger: Optional[ResolveAuditLedger] = None

    def resolve(self, case_id: str, *, caller_tag: str = "scorer") -> str:
        """Return the ground-truth label for ``case_id``, auditing every call.

        ``caller_tag`` names the resolving code path explicitly (deterministic;
        ``inspect``-derived stacks are deliberately not used). Raises
        ``KeyError`` for case ids absent from the index.
        """
        if "case" not in self.index.columns:
            raise ValueError("ScorerContext index must carry a 'case' column")
        sub = self.index[self.index["case"] == case_id]
        if sub.empty:
            raise KeyError(f"case id {case_id!r} not in ground-truth index")
        if self.label_column not in self.index.columns:
            raise ValueError(f"label column {self.label_column!r} missing from index")
        label = str(sub[self.label_column].iloc[0])
        entry = ResolveAuditEntry(case_id=case_id, timestamp=self.clock(), caller=caller_tag)
        self.audit.append(entry)
        if self.ledger is not None:
            self.ledger.append(entry)
        return label

    def resolve_many(self, case_ids: Sequence[str], *, caller_tag: str = "scorer") -> dict:
        """Resolve each case id (in order); every id is audited individually."""
        return {cid: self.resolve(cid, caller_tag=caller_tag) for cid in case_ids}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except OSError as exc:
        raise GroundTruthLeakError(f"canary cannot read agent artifact {path}: {exc}") from exc


def assert_no_agent_access(
    artifacts: Iterable[Union[str, Path]],
    expected_labels: Sequence[str],
) -> None:
    """Canary: raise :class:`GroundTruthLeakError` if a resolved label leaks.

    Scans every file in ``artifacts`` (the agent-visible artifact set) and
    raises as soon as any value from ``expected_labels`` — the resolved
    ground-truth value set passed by the caller, never hardcoded here —
    appears. Non-identifier labels (shorter than 4 chars) are matched
    word-bounded to avoid substring false positives; identifiers are matched
    as exact substrings.
    """
    labels = [str(label) for label in expected_labels if str(label)]
    for artifact in artifacts:
        path = Path(artifact)
        if not path.is_file():
            continue
        text = _read_text(path)
        for label in labels:
            hit = label in text if len(label) >= 4 else re.search(rf"\b{re.escape(label)}\b", text)
            if hit:
                raise GroundTruthLeakError(
                    f"resolved ground-truth value {label!r} found in agent-visible artifact {path}"
                )
