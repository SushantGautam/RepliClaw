"""V3 telemetry sandbox: shared OBS tools for the D-E-TELEM / C-EQ-TELEM arms.

Implements the "Telemetry sandbox (OBS tools — both arms, byte-identical)"
section (``docs/next_stage/design/v3_telemetry_arm_addendum.md`` §3) of the V3
pilot design.

Design guarantees (frozen, additive):

* **Opaque case ids.** Agents never see upstream RCAEval case ids.
  :class:`PilotCaseRegistry` maps the 10 frozen pilot ids (sha256-pinned at
  construction) to public opaque ids ``RCA-P-01`` .. ``RCA-P-10`` assigned in
  sorted upstream-id order. The mapping is deterministic: every construction
  of the registry yields the identical mapping. No public method exposes the
  upstream id for an opaque id.
* **Arm parity.** Every tool is a pure function of (case, args): the same
  opaque id + args produces byte-identical payloads for both arms.
* **Leak guards.** Every returned payload passes a recursive
  :meth:`TelemetrySandbox._sanitize` scan that raises
  :class:`LeakDetectedError` if any forbidden literal (an upstream case id,
  the label-column names ``root_cause`` / ``fault_description``) appears.
  ``root_cause.txt`` is never opened — every file read goes through a single
  injection point (``opener``) tracked in :attr:`TelemetrySandbox.files_opened`
  so tests can assert it.
* **Diagnosis commit.** Each sandbox accepts exactly ONE
  :meth:`TelemetrySandbox.submit_diagnosis`; a second call raises
  :class:`DiagnosisAlreadyCommitted`.
* **Tool budget.** Max 24 query-tool calls per sandbox, max 4 each for
  ``service_logs`` / ``service_traces``; exceeding raises
  :class:`ToolBudgetExhausted`. Every call is appended to
  :attr:`TelemetrySandbox.call_log` as
  ``{tool, args, wall_ms, payload_bytes}``.

Scoring note: :func:`service_level_success` implements the official RCAEval
coarse service-level accuracy@k semantics (true service among first k
submitted services). Ground truth itself is resolved ONLY through the scorer-side
heldout resolve helper (see ``repliclaw.benchmarks.rcaeval``) by the
scorer — this module never reads labels. The
``top_anomalies`` math is a SHARED reference for agents (same
windowing/scaling family as the BARO-style scorer); it is NOT the official
Evaluator (that one is used only for BARO parity runs).
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Frozen pilot roster (D-V3-013 approved pilot, 10 frozen cases).
#
# Opaque ids are assigned to these ids sorted ascending; the sha256 pin over
# the sorted newline-joined list is asserted at registry construction, so a
# tampered roster fails fast rather than silently re-mapping cases.
# ---------------------------------------------------------------------------
FROZEN_PILOT_IDS: tuple[str, ...] = (
    "re1ob_adservice_cpu_1",
    "re1ob_adservice_delay_1",
    "re1ob_cartservice_cpu_1",
    "re1ob_cartservice_delay_1",
    "re2ob_checkoutservice_delay_1",
    "re2ob_currencyservice_delay_1",
    "re2ob_emailservice_delay_1",
    "re2ob_productcatalogservice_delay_1",
    "re3ob_adservice_f3_1",
    "re3ob_cartservice_f1_1",
)
FROZEN_PILOT_SHA256 = "955a462175200909577c8c71db64e3fc8f879c83f1a9028e307926c471503a02"

# Label columns that must never surface in an agent-facing payload.
FORBIDDEN_LABEL_LITERALS: tuple[str, ...] = ("root_cause", "fault_description")

# Budget constants (addendum §3 / §6.2: per-run tool caps).
MAX_TOOL_CALLS = 24
MAX_LOGS_CALLS = 4
MAX_TRACES_CALLS = 4

# Anomaly-window math (BARO-style windowing: 600 s windows around onset).
FAULTY_WINDOW_SECONDS = 600
NORMAL_WINDOW_SECONDS = 600
LOGS_TRACES_CONTEXT_SECONDS = 300
EPS = 1e-9
SCORE_CAP = 10.0

_OPAQUE_PREFIX = "RCA-P-"


class LeakDetectedError(RuntimeError):
    """A payload or read path contained a forbidden label/case-id literal."""


class DiagnosisAlreadyCommitted(RuntimeError):
    """The sandbox already received its single committed diagnosis."""


class ToolBudgetExhausted(RuntimeError):
    """The per-sandbox tool-call budget was exceeded."""


class UnknownServiceError(ValueError):
    """A referenced service is not in the case's metric inventory."""


class UnknownCaseIdError(ValueError):
    """An opaque case id is not in the frozen pilot roster."""


def normalize_service(name: str) -> str:
    """Normalize a service name: lower-case, strip, ``'-'`` removed.

    ``'Front-End'`` == ``'frontend'``. Used for inventory matching, log/trace
    service matching, and diagnosis validation.
    """
    return name.strip().lower().replace("-", "")


def repo_root() -> Path:
    """Repository root (this module lives at ``src/repliclaw/experiments/v3/``)."""
    return Path(__file__).resolve().parents[4]


def _roster_sha256(ids: tuple[str, ...]) -> str:
    return hashlib.sha256("\n".join(sorted(ids)).encode("utf-8")).hexdigest()


def _forbidden_literals() -> tuple[str, ...]:
    return FORBIDDEN_LABEL_LITERALS + FROZEN_PILOT_IDS


class PilotCaseRegistry:
    """Deterministic opaque-id -> pilot-case-dir registry for the frozen roster.

    Opaque ids ``RCA-P-01`` .. ``RCA-P-10`` are assigned to the frozen pilot
    ids sorted ascending, so the same mapping results from every construction.
    The roster sha256 is asserted at construction; a tampered roster raises
    ``ValueError``. The reverse map (opaque -> upstream id) is intentionally
    NOT exposed by any public method.
    """

    def __init__(self, data_root: str | Path | None = None) -> None:
        if _roster_sha256(FROZEN_PILOT_IDS) != FROZEN_PILOT_SHA256:
            raise ValueError("frozen pilot roster sha256 mismatch — roster was tampered with")
        root = Path(data_root) if data_root is not None else repo_root() / ".artifacts" / "rcaeval" / "pilot"
        self._data_root = root
        sorted_ids = sorted(FROZEN_PILOT_IDS)
        self._opaque_to_dir: dict[str, Path] = {
            f"{_OPAQUE_PREFIX}{i:02d}": root / upstream for i, upstream in enumerate(sorted_ids, start=1)
        }

    @property
    def data_root(self) -> Path:
        return self._data_root

    def opaque_ids(self) -> tuple[str, ...]:
        """All opaque case ids, in frozen-assignment order."""
        return tuple(self._opaque_to_dir)

    def is_known_opaque_id(self, opaque_id: str) -> bool:
        return opaque_id in self._opaque_to_dir

    def case_dir(self, opaque_id: str) -> Path:
        """On-disk case dir for an opaque id (no upstream id is ever returned)."""
        try:
            return self._opaque_to_dir[opaque_id]
        except KeyError:
            raise UnknownCaseIdError(f"unknown opaque case id: {opaque_id!r}") from None


class TelemetrySandbox:
    """Per-arm telemetry sandbox over one frozen pilot case (via opaque id).

    All public tools return plain JSON-able dicts/lists/strings that are
    pure functions of (case, args) — identical for every arm. Every return is
    leak-scanned; every call is budget-checked and appended to
    :attr:`call_log`. ``root_cause.txt`` is never opened.
    """

    def __init__(
        self,
        registry: PilotCaseRegistry,
        opaque_id: str,
        *,
        opener: Callable[[Path, str], Any] | None = None,
    ) -> None:
        if not registry.is_known_opaque_id(opaque_id):
            raise UnknownCaseIdError(f"unknown opaque case id: {opaque_id!r}")
        self._registry = registry
        self._opaque_id = opaque_id
        self._case_dir = registry.case_dir(opaque_id)
        # Injection point for tests: all file reads go through _open.
        self._opener: Callable[[Path, str], Any] = opener if opener is not None else open
        self.files_opened: list[Path] = []
        self.call_log: list[dict[str, Any]] = []
        self._metrics: pd.DataFrame | None = None
        self._logs: pd.DataFrame | None = None
        self._traces: pd.DataFrame | None = None
        self._logs_loaded = False
        self._traces_loaded = False
        self._onset: int | None = None
        self._invoked: dict[str, int] = {}
        self._total_calls = 0
        self._submission: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _open(self, path: Path, mode: str = "r") -> Any:
        if path.name == "root_cause.txt":
            raise LeakDetectedError("root_cause.txt must never be opened by the sandbox")
        self.files_opened.append(path)
        return self._opener(path, mode)

    def _onset_seconds(self) -> int:
        if self._onset is None:
            with self._open(self._case_dir / "inject_time.txt") as fh:
                self._onset = int(fh.read().strip())
        return self._onset

    def _load_metrics(self) -> pd.DataFrame:
        if self._metrics is None:
            self._metrics = pd.read_parquet(self._open(self._case_dir / "metrics.parquet", "rb"))
        return self._metrics

    def _load_logs(self) -> pd.DataFrame | None:
        if not self._logs_loaded:
            path = self._case_dir / "logs.parquet"
            self._logs = pd.read_parquet(self._open(path, "rb")) if path.is_file() else None
            self._logs_loaded = True
        return self._logs

    def _load_traces(self) -> pd.DataFrame | None:
        if not self._traces_loaded:
            path = self._case_dir / "traces.parquet"
            self._traces = pd.read_parquet(self._open(path, "rb")) if path.is_file() else None
            self._traces_loaded = True
        return self._traces

    @property
    def _has_logs(self) -> bool:
        return (self._case_dir / "logs.parquet").is_file()

    @property
    def _has_traces(self) -> bool:
        return (self._case_dir / "traces.parquet").is_file()

    def _inventory(self) -> list[str]:
        cols = [c for c in self._load_metrics().columns if c != "time"]
        return sorted({c.split("_", 1)[0] for c in cols})

    def _service_of(self, metric_col: str) -> str:
        return metric_col.split("_", 1)[0]

    def _check_budget(self, tool: str) -> None:
        if self._total_calls >= MAX_TOOL_CALLS:
            raise ToolBudgetExhausted(f"total tool budget exhausted ({MAX_TOOL_CALLS} calls)")
        if tool == "service_logs" and self._invoked.get(tool, 0) >= MAX_LOGS_CALLS:
            raise ToolBudgetExhausted(f"service_logs budget exhausted ({MAX_LOGS_CALLS} calls)")
        if tool == "service_traces" and self._invoked.get(tool, 0) >= MAX_TRACES_CALLS:
            raise ToolBudgetExhausted(f"service_traces budget exhausted ({MAX_TRACES_CALLS} calls)")

    def _finish_call(self, tool: str, args: dict[str, Any], started: float, payload: Any) -> Any:
        sanitized = self._sanitize(payload)
        self._total_calls += 1
        self._invoked[tool] = self._invoked.get(tool, 0) + 1
        self.call_log.append(
            {
                "tool": tool,
                "args": args,
                "wall_ms": round((time.monotonic() - started) * 1000.0, 3),
                "payload_bytes": len(json.dumps(sanitized).encode("utf-8")),
            }
        )
        return sanitized

    def _sanitize(self, obj: Any) -> Any:
        """Recursively reject any forbidden literal in a payload (leak guard)."""
        return self._sanitize_node(obj, _forbidden_literals())

    @staticmethod
    def _sanitize_node(obj: Any, forbidden: tuple[str, ...]) -> Any:
        if isinstance(obj, str):
            low = obj.lower()
            for lit in forbidden:
                if lit in low:
                    raise LeakDetectedError(f"forbidden literal in payload: {lit!r}")
            return obj
        if isinstance(obj, dict):
            return {k: TelemetrySandbox._sanitize_node(v, forbidden) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [TelemetrySandbox._sanitize_node(v, forbidden) for v in obj]
        return obj

    # ------------------------------------------------------------------
    # OBS tools (identical for both arms)
    # ------------------------------------------------------------------
    def system_context(self) -> dict[str, Any]:
        """Static per-case context: service inventory, metric counts, window, onset.

        ``anomaly_onset`` is the public "anomaly onset (reported)" incident
        metadata (``inject_time``), NOT ground truth.
        """
        started = time.monotonic()
        metrics = self._load_metrics()
        times = metrics["time"].to_numpy()
        counts: dict[str, int] = {}
        for col in metrics.columns:
            if col == "time":
                continue
            counts[self._service_of(col)] = counts.get(self._service_of(col), 0) + 1
        payload = {
            "opaque_case_id": self._opaque_id,
            "services": sorted(counts),
            "per_service_metric_count": {s: counts[s] for s in sorted(counts)},
            "time_start": int(times.min()),
            "time_end": int(times.max()),
            "anomaly_onset": self._onset_seconds(),
            "has_logs": self._has_logs,
            "has_traces": self._has_traces,
        }
        self._check_budget("system_context")
        return self._finish_call("system_context", {}, started, payload)

    def top_anomalies(self, k: int = 20) -> dict[str, Any]:
        """Ranked (service, metric, score) anomaly list — SHARED reference math.

        Exact formula (BARO-style windowing/scaling family; deterministic):

        * ``onset`` = reported anomaly onset (``inject_time``).
        * faulty window  = rows with ``onset <= t < onset + 600``
        * normal window  = rows with ``onset - 600 <= t < onset``
        * for each metric column ``c`` (skipped if constant or if either
          window is empty):
            ``med = median(c)``; ``iqr = percentile(c, 75) - percentile(c, 25)``
            (skipped if ``iqr == 0``); ``z = (c - med) / iqr``
            (RobustScaler-style median/IQR scaling, NOT the official Evaluator)
            ``fz = max(|z| over faulty window)``
            ``nz = max(|z| over normal window)``
            ``score = min(fz / (nz + 1e-9), 10.0)``
        * rows ranked by ``score`` desc, ties broken by (service, metric) asc;
          top ``k`` returned.

        Constant columns (IQR == 0) are dropped, so every returned row has
        score > 0.
        """
        self._check_budget("top_anomalies")
        started = time.monotonic()
        payload = self._top_anomalies_payload(k)
        return self._finish_call("top_anomalies", {"k": k}, started, payload)

    def _top_anomalies_payload(self, k: int) -> dict[str, Any]:
        metrics = self._load_metrics()
        onset = self._onset_seconds()
        t = metrics["time"].to_numpy()
        faulty = (t >= onset) & (t < onset + FAULTY_WINDOW_SECONDS)
        normal = (t >= onset - NORMAL_WINDOW_SECONDS) & (t < onset)
        if not faulty.any() or not normal.any():
            raise ValueError("case data does not cover both 600 s anomaly windows")
        rows: list[tuple[float, str, str]] = []
        for col in metrics.columns:
            if col == "time":
                continue
            x = metrics[col].to_numpy(dtype=float)
            med = float(np.median(x))
            iqr = float(np.percentile(x, 75) - np.percentile(x, 25))
            if iqr == 0.0:
                continue
            z = (x - med) / iqr
            fz = float(np.abs(z[faulty]).max())
            nz = float(np.abs(z[normal]).max())
            score = min(fz / (nz + EPS), SCORE_CAP)
            rows.append((score, self._service_of(col), col))
        rows.sort(key=lambda r: (-r[0], r[1], r[2]))
        top = rows[: max(0, k)]
        return {
            "window_seconds": FAULTY_WINDOW_SECONDS,
            "rows": [
                {"rank": i + 1, "service": svc, "metric": col, "score": round(score, 6)}
                for i, (score, svc, col) in enumerate(top)
            ],
        }

    def service_metrics(self, svc: str, k: int = 30) -> dict[str, Any]:
        """Per-metric fault-vs-normal window statistics for one service."""
        self._check_budget("service_metrics")
        started = time.monotonic()
        payload = self._service_metrics_payload(svc, k)
        return self._finish_call("service_metrics", {"svc": svc, "k": k}, started, payload)

    def _service_metrics_payload(self, svc: str, k: int) -> dict[str, Any]:
        metrics = self._load_metrics()
        onset = self._onset_seconds()
        target = normalize_service(svc)
        t = metrics["time"].to_numpy()
        faulty = (t >= onset) & (t < onset + FAULTY_WINDOW_SECONDS)
        normal = (t >= onset - NORMAL_WINDOW_SECONDS) & (t < onset)
        rows: list[dict[str, Any]] = []
        for col in sorted(metrics.columns):
            if col == "time" or normalize_service(self._service_of(col)) != target:
                continue
            x = metrics[col].to_numpy(dtype=float)
            iqr = float(np.percentile(x, 75) - np.percentile(x, 25))
            med = float(np.median(x))
            if iqr == 0.0:
                z_peak = 0.0
            else:
                z = (x - med) / iqr
                z_peak = float(max(np.abs(z[faulty]).max() if faulty.any() else 0.0,
                                   np.abs(z[normal]).max() if normal.any() else 0.0))
            rows.append(
                {
                    "metric": col,
                    "median": round(med, 6),
                    "p95": round(float(np.percentile(x, 95)), 6),
                    "faulty_max": round(float(x[faulty].max()), 6) if faulty.any() else None,
                    "normal_max": round(float(x[normal].max()), 6) if normal.any() else None,
                    "z_peak": round(z_peak, 6),
                }
            )
        rows.sort(key=lambda r: (-r["z_peak"], r["metric"]))
        return {"service": svc, "rows": rows[: max(0, k)]}

    def service_logs(self, svc: str, k: int = 50) -> dict[str, Any]:
        """Up to k log lines for one service within ±300 s of reported onset.

        Returns ``{"available": False, "message": "no logs available"}`` when
        the case has no logs file (RE1 pilot cases).
        """
        self._check_budget("service_logs")
        started = time.monotonic()
        payload = self._service_logs_payload(svc, k)
        return self._finish_call("service_logs", {"svc": svc, "k": k}, started, payload)

    def _service_logs_payload(self, svc: str, k: int) -> dict[str, Any]:
        logs = self._load_logs()
        if logs is None:
            return {"available": False, "message": "no logs available"}
        onset = self._onset_seconds()
        ts = logs["timestamp"].to_numpy()
        mask = (ts >= onset - LOGS_TRACES_CONTEXT_SECONDS) & (ts <= onset + LOGS_TRACES_CONTEXT_SECONDS)
        sub = logs.loc[mask]
        if len(sub):
            sub = sub[sub["container_name"].map(normalize_service) == normalize_service(svc)]
        rows = [
            {"t": int(rec["timestamp"]), "msg": str(rec["message"])}
            for rec in sub.head(max(0, k)).to_dict("records")
        ]
        return {"service": svc, "available": True, "count": len(rows), "rows": rows}

    def service_traces(self, svc: str, k: int = 30) -> dict[str, Any]:
        """Up to k span rows for one service within ±300 s of reported onset.

        Returns ``{"available": False, "message": "no traces available"}`` when
        the case has no traces file (RE1/RE3-restricted pilot cases).
        """
        self._check_budget("service_traces")
        started = time.monotonic()
        payload = self._service_traces_payload(svc, k)
        return self._finish_call("service_traces", {"svc": svc, "k": k}, started, payload)

    def _service_traces_payload(self, svc: str, k: int) -> dict[str, Any]:
        traces = self._load_traces()
        if traces is None:
            return {"available": False, "message": "no traces available"}
        onset = self._onset_seconds()
        start_s = traces["startTimeMillis"].to_numpy(dtype=float) / 1000.0
        mask = (start_s >= onset - LOGS_TRACES_CONTEXT_SECONDS) & (
            start_s <= onset + LOGS_TRACES_CONTEXT_SECONDS
        )
        svc_match = traces["serviceName"].map(normalize_service).to_numpy() == normalize_service(svc)
        sub = traces.loc[mask & svc_match]
        rows: list[dict[str, Any]] = []
        for rec in sub.head(max(0, k)).to_dict("records"):
            status = rec["statusCode"]
            rows.append(
                {
                    "service": str(rec["serviceName"]),
                    "operation": "" if rec["operationName"] is None else str(rec["operationName"]),
                    "duration_ms": round(float(rec["duration"]) / 1000.0, 3),
                    "status": None if status is None else int(status),
                }
            )
        return {"service": svc, "available": True, "count": len(rows), "rows": rows}

    # ------------------------------------------------------------------
    # diagnosis commit
    # ------------------------------------------------------------------
    def submit_diagnosis(self, ranked_services: list[str]) -> dict[str, Any]:
        """Commit the arm's SINGLE ranked diagnosis (service ranking).

        Validates every service against the case's metric inventory
        (normalized). Returns a confirmation dict whose ``ranking_sha256`` is
        the sha256 of the canonical (normalized, newline-joined) ranking.
        A second call raises :class:`DiagnosisAlreadyCommitted`.
        """
        if self._submission is not None:
            raise DiagnosisAlreadyCommitted("diagnosis already committed for this sandbox")
        self._check_budget("submit_diagnosis")
        if not ranked_services:
            raise UnknownServiceError("ranked_services must be non-empty")
        inventory = {normalize_service(s) for s in self._inventory()}
        normalized: list[str] = []
        for svc in ranked_services:
            n = normalize_service(svc)
            if n not in inventory:
                raise UnknownServiceError(f"unknown service in diagnosis: {svc!r}")
            normalized.append(n)
        payload = {
            "opaque_case_id": self._opaque_id,
            "committed": True,
            "ranking": normalized,
            "ranking_sha256": hashlib.sha256("\n".join(normalized).encode("utf-8")).hexdigest(),
        }
        started = time.monotonic()
        confirmed = self._finish_call("submit_diagnosis", {"ranked_services": list(ranked_services)}, started, payload)
        self._submission = confirmed
        return confirmed


def service_level_success(submitted_ranking: list[str], true_service: str, k: int = 5) -> bool:
    """Official RCAEval coarse service-level accuracy@k semantics.

    True when the normalized ground-truth service appears among the first
    ``k`` submitted (normalized) services. The scorer is the only path that
    resolves ``true_service`` (via the scorer-side heldout resolve
    helper); this function is pure.
    """
    return normalize_service(true_service) in {normalize_service(s) for s in submitted_ranking[:k]}
