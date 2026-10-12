"""Thin AIOpsLab adapter for the V4 deadline instrument.

Wraps a live AIOpsLab problem instance (minikube + Astronomy Shop, namespace
``astronomy-shop``) as a tool sandbox exposing the same five OBS tools the V4
arms' ``_execute_tool`` understands, mapped onto AIOpsLab's *live* task actions
instead of frozen RCAEval parquet:

    get_metrics  -> TaskActions.get_metrics / read_metrics (Prometheus export)
    get_traces   -> TaskActions.get_traces   / read_traces   (Jaeger export)
    get_logs     -> TaskActions.get_logs                      (kubectl logs)
    exec_shell   -> TaskActions.exec_shell                    (bounded shell)
    submit_diagnosis -> LocalizationActions.submit            (one-shot commit)

Importable WITHOUT AIOpsLab installed: every ``aiopslab.*`` import is lazy
inside :func:`load_aiopslab`, which adds AIOpsLab's checkout to ``sys.path``
(constructor arg, ``$AIOPSLAB_ROOT``, or the known local checkout) and raises
a clear :class:`AIOpsLabImportError` naming the missing dependency otherwise.

Usage::

    runner = AIOpsLabCaseRunner("astronomy_shop_ad_service_high_cpu-localization-1")
    case = runner.setup()          # workload up, fault injected
    ... let an arm drive case.sandbox via _execute_tool-style dispatch ...
    result = runner.evaluate(case, ranking)
    runner.teardown(case)          # recover fault, always runs

``__main__`` runs a live smoke test (registry, all five tools, eval, recovery).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_DEFAULT_AIOPSLAB_ROOT = "/Users/sushantgautam/Documents/stg2-worktrees/AIOpsLab"
_DEFAULT_NAMESPACE = "astronomy-shop"


class AIOpsLabImportError(RuntimeError):
    """AIOpsLab could not be imported; message names what is missing."""


def load_aiopslab(root: str | os.PathLike[str] | None = None) -> None:
    """Make ``aiopslab`` importable; tries an existing import first, then adds
    ``root`` / ``$AIOPSLAB_ROOT`` / the known local checkout to ``sys.path``."""
    try:
        import aiopslab.orchestrator.problems.registry  # noqa: F401
        return
    except ImportError:
        pass
    candidates = [p for p in (str(root) if root else None,
                              os.environ.get("AIOPSLAB_ROOT"),
                              _DEFAULT_AIOPSLAB_ROOT) if p]
    for cand in candidates:
        cand_path = Path(cand).resolve()
        if (cand_path / "aiopslab" / "__init__.py").is_file():
            if str(cand_path) not in sys.path:
                sys.path.insert(0, str(cand_path))
            break
    try:
        import aiopslab.orchestrator.problems.registry  # noqa: F401
    except ImportError as exc:
        missing = type(exc).__name__ + (f": {exc}" if str(exc) else "")
        hint = ""
        if isinstance(exc, ModuleNotFoundError) and getattr(exc, "name", None):
            hint = (f" Missing dependency '{exc.name}' — install it in the "
                    f"interpreter that runs this adapter, e.g. "
                    f"{Path(_DEFAULT_AIOPSLAB_ROOT)}/.venv/bin/pip install {exc.name}.")
        raise AIOpsLabImportError(
            f"AIOpsLab is not importable ({missing}).{hint} Either run under "
            f"its venv ({Path(_DEFAULT_AIOPSLAB_ROOT)}/.venv/bin/python) or "
            f"set AIOPSLAB_ROOT to a checkout whose deps are installed "
            f"(tried roots: {', '.join(candidates) or 'none'}). Original error: {exc}"
        ) from exc


@dataclass
class AIOpsLabCase:
    """One live AIOpsLab problem instance plus its tool sandbox."""

    problem_id: str
    problem: Any          # AIOpsLab problem/task instance (lazy-typed)
    namespace: str
    sandbox: "AIOpsLabToolSandbox"
    task_description: str
    instructions: str
    _fault_injected: bool = field(default=False, repr=False)


class AIOpsLabToolSandbox:
    """Live-tool sandbox mirroring the V4 instrument's five-tool protocol.

    Signatures match ``det_deadline._execute_tool``-style dispatch:
    ``get_metrics(k)``, ``get_traces(svc, k)``, ``get_logs(svc, k)``,
    ``exec_shell(command)``, ``submit_diagnosis(ranked_services)``. Every call
    appends ``{tool, args, wall_ms, payload_bytes}`` to :attr:`call_log` so the
    V4 accounting (budgets, repeated-action counts) works unchanged.
    """

    def __init__(self, actions: Any, *, namespace: str) -> None:
        self._actions = actions
        self.namespace = namespace
        self.call_log: list[dict[str, Any]] = []
        self._metrics_dir: str | None = None
        self._traces_dir: str | None = None
        self._prom_forward: subprocess.Popen | None = None
        self._submission: dict[str, Any] | None = None

    # -- internals -------------------------------------------------------------
    def _ensure_prometheus_port_forward(self) -> None:
        """AIOpsLab's PrometheusAPI forwards ``svc/prometheus-server -n observe``,
        which does not exist in this Astronomy Shop install (service
        ``prometheus:9090`` in the app namespace). If nothing listens on the
        hardcoded URL port, start a tracked port-forward; non-fatal otherwise."""
        import socket

        # must match the hardcoded URL inside AIOpsLab's TaskActions.get_metrics
        host, port = "localhost", 32000
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((host, port)) == 0:
                return
        try:
            self._prom_forward = subprocess.Popen(
                ["kubectl", "port-forward", "svc/prometheus", f"{port}:9090",
                 "-n", self.namespace],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)
            if self._prom_forward.poll() is not None:
                print(f"[aiopslab_adapter] prometheus port-forward exited: "
                      f"{self._prom_forward.returncode}")
                self._prom_forward = None
        except Exception as exc:  # noqa: BLE001 — never kill the arm over a forward
            print(f"[aiopslab_adapter] prometheus port-forward failed to start: {exc}")

    def close(self) -> None:
        """Stop our Prometheus port-forward (idempotent)."""
        proc, self._prom_forward = self._prom_forward, None
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    def _finish(self, tool: str, args: dict[str, Any], started: float, payload: Any) -> Any:
        if isinstance(payload, str):
            text = payload
        else:
            text = json.dumps(payload, default=str)
        self.call_log.append({
            "tool": tool,
            "args": args,
            "wall_ms": round((time.monotonic() - started) * 1000.0, 3),
            "payload_bytes": len(text.encode("utf-8")),
        })
        return payload

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[:limit] + f"\n… [truncated to {limit} chars]"

    def _extract_dir(self, raw: str) -> str:
        """AIOpsLab's export actions return a human message with the path
        embedded (e.g. 'Metrics data exported to directory: <path>...')."""
        for marker in ("exported to directory: ", "Trace data exported to: "):
            if marker in raw:
                return raw.split(marker, 1)[1].strip().splitlines()[0]
        return raw.strip()

    @staticmethod
    def _first_csv(directory: str) -> str | None:
        d = Path(directory)
        if not d.is_dir():
            return None
        csvs = sorted(d.rglob("*.csv"))
        return str(csvs[0]) if csvs else None

    # -- OBS tools (live) --------------------------------------------------------
    def _export_payload(self, attr: str, read_fn: Any,
                        raw: str | None, svc: str | None = None) -> dict[str, Any]:
        """First call exports (raw message carries the dir); repeats re-read."""
        if getattr(self, attr) is None:
            assert raw is not None
            setattr(self, attr, self._extract_dir(raw))
        directory = getattr(self, attr)
        path = self._first_csv(directory)
        first_call = raw is not None
        if path is None:
            files = sorted(str(p) for p in Path(directory).rglob("*") if p.is_file())
            return {"available": True, "export_dir": directory, "files": files[:50],
                    "hint": "use exec_shell to grep specific series"}
        content = read_fn(path)
        if first_call:
            files = sorted(str(p) for p in Path(directory).rglob("*.csv"))
            content += f"\n[exported {len(files)} CSV files under {directory}]"
        if svc:
            needle = svc.lower()
            content = "\n".join(ln for ln in content.splitlines() if needle in ln.lower()) \
                or "(no rows matched service)"
        return {"available": True, "export_dir": directory,
                **({"service": svc} if svc is not None else {}),
                "preview": self._truncate(content, 8000)}

    def get_metrics(self, k: int = 5) -> dict[str, Any]:
        """Export Prometheus metrics for the last ``k`` minutes (CSV dir + file
        listing); repeat calls preview the existing export — targeted queries
        go through ``exec_shell`` (e.g. grep) on the returned paths."""
        started = time.monotonic()
        try:
            if self._metrics_dir is None:
                self._ensure_prometheus_port_forward()
                raw = str(self._actions.get_metrics(self.namespace, duration=k))
            else:
                raw = None
            payload = self._export_payload("_metrics_dir", self._actions.read_metrics, raw)
        except Exception as exc:  # noqa: BLE001 — surface as observation, not crash
            payload = {"available": False, "error": f"metrics export failed: {exc}"}
        return self._finish("get_metrics", {"k": k}, started, payload)

    def get_traces(self, svc: str = "", k: int = 5) -> dict[str, Any]:
        """Export Jaeger traces for the last ``k`` minutes; optional service filter."""
        started = time.monotonic()
        try:
            raw = (str(self._actions.get_traces(self.namespace, duration=k))
                   if self._traces_dir is None else None)
            payload = self._export_payload("_traces_dir", self._actions.read_traces, raw,
                                           svc=svc or None)
        except Exception as exc:  # noqa: BLE001 — surface as observation, not crash
            payload = {"available": False, "error": f"traces export failed: {exc}"}
        return self._finish("get_traces", {"svc": svc, "k": k}, started, payload)

    def get_logs(self, svc: str = "", k: int = 50) -> dict[str, Any]:
        """Fetch pod logs for one service (last k lines kept)."""
        started = time.monotonic()
        raw = self._actions.get_logs(self.namespace, svc)
        lines = str(raw).splitlines()
        payload = {"service": svc, "available": not str(raw).startswith("Error"),
                   "count": min(len(lines), k), "rows": lines[-k:] if k > 0 else lines}
        return self._finish("get_logs", {"svc": svc, "k": k}, started, payload)

    def exec_shell(self, command: str) -> dict[str, Any]:
        """Run one bounded shell command in AIOpsLab's debugging environment."""
        started = time.monotonic()
        out = self._actions.exec_shell(command, timeout=60)
        payload = {"command": command, "output": self._truncate(str(out), 12000)}
        return self._finish("exec_shell", {"command": command}, started, payload)

    def submit_diagnosis(self, ranked_services: list[str]) -> dict[str, Any]:
        """Commit the single ranked diagnosis through AIOpsLab's submit action."""
        if self._submission is not None:
            raise RuntimeError("diagnosis already committed for this sandbox")
        if not ranked_services:
            raise ValueError("ranked_services must be non-empty")
        started = time.monotonic()
        status = self._actions.submit(list(ranked_services))
        payload = {"committed": True, "ranking": list(ranked_services),
                   "status": str(status)}
        confirmed = self._finish("submit_diagnosis",
                                 {"ranked_services": list(ranked_services)}, started, payload)
        self._submission = confirmed
        return confirmed


class AIOpsLabCaseRunner:
    """Case lifecycle for one AIOpsLab problem id (localization problems)."""

    def __init__(self, problem_id: str, *, aiopslab_root: str | None = None) -> None:
        self.problem_id = problem_id
        self.aiopslab_root = aiopslab_root
        self._registry: Any = None
        self._cases: list[AIOpsLabCase] = []

    # -- lazy accessors ----------------------------------------------------------
    @property
    def registry(self) -> Any:
        if self._registry is None:
            load_aiopslab(self.aiopslab_root)
            from aiopslab.orchestrator.problems.registry import ProblemRegistry
            self._registry = ProblemRegistry()
        return self._registry

    def list_problem_ids(self, task_type: str | None = None) -> list[str]:
        return self.registry.get_problem_ids(task_type)

    # -- lifecycle -----------------------------------------------------------------
    def setup(self) -> AIOpsLabCase:
        """Instantiate the problem, start workload, inject fault, build sandbox."""
        load_aiopslab(self.aiopslab_root)
        problem = self.registry.get_problem_instance(self.problem_id)
        if not hasattr(problem, "inject_fault"):
            raise ValueError(f"{self.problem_id!r} has no inject_fault; localization "
                             f"problems only are supported by this adapter")
        problem.start_workload()
        problem.inject_fault()
        namespace = getattr(problem, "namespace", None) or _DEFAULT_NAMESPACE
        sandbox = AIOpsLabToolSandbox(problem.actions, namespace=namespace)
        case = AIOpsLabCase(
            problem_id=self.problem_id,
            problem=problem,
            namespace=namespace,
            sandbox=sandbox,
            task_description=problem.get_task_description(),
            instructions=problem.get_instructions(),
            _fault_injected=True,
        )
        self._cases.append(case)
        return case

    def evaluate(self, case: AIOpsLabCase, solution: Any,
                 trace: list[Any] | None = None, duration: float | None = None) -> dict[str, Any]:
        """Run AIOpsLab's own evaluator. ``trace``: optional list of AIOpsLab
        ``SessionItem`` (defaults to one per sandbox call_log entry);
        ``duration`` seconds defaults to cumulative sandbox wall time."""
        if trace is None:
            from aiopslab.session import SessionItem
            trace = [SessionItem(role="assistant", content=json.dumps(c["args"]))
                     for c in case.sandbox.call_log]
        if duration is None:
            duration = sum(c["wall_ms"] for c in case.sandbox.call_log) / 1000.0
        results = case.problem.eval(solution, trace, float(duration))
        return dict(results)

    def teardown(self, case: AIOpsLabCase) -> None:
        """Recover the fault and close sandbox resources; idempotent."""
        if case._fault_injected:
            try:
                case.problem.recover_fault()
            finally:
                case._fault_injected = False
        case.sandbox.close()

    def cleanup_all(self) -> None:
        for case in self._cases:
            self.teardown(case)
        self._cases.clear()


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------


def _smoke_test() -> int:
    # AIOpsLab exports metrics/traces into cwd-relative dirs — keep the repo clean.
    workdir = Path(__file__).resolve().parents[4] / ".artifacts" / "aiopslab_smoke"
    workdir.mkdir(parents=True, exist_ok=True)
    os.chdir(workdir)
    print(f"[smoke] working dir: {workdir}")

    print("[smoke] loading aiopslab ...")
    load_aiopslab()
    print("[smoke] ok")

    runner = AIOpsLabCaseRunner("astronomy_shop_ad_service_high_cpu-localization-1")
    ids = runner.list_problem_ids("localization")
    assert runner.problem_id in ids, f"{runner.problem_id} not in {len(ids)} localization ids"
    print(f"[smoke] registry ok ({len(ids)} localization problems)")

    case = runner.setup()
    try:
        print(f"[smoke] fault injected in namespace {case.namespace}; "
              f"task description {len(case.task_description)} chars")
        obs = case.sandbox.get_metrics(k=5)
        assert obs["available"], obs
        print(f"[smoke] get_metrics ok -> {obs['export_dir']}")
        tr = case.sandbox.get_traces(svc="ad", k=5)
        print(f"[smoke] get_traces available={tr['available']} "
              f"preview_len={len(tr.get('preview') or tr.get('error') or '')}")
        lg = case.sandbox.get_logs(svc="ad", k=10)
        print(f"[smoke] get_logs service={lg['service']} count={lg['count']}")
        sh = case.sandbox.exec_shell("kubectl get pods -n astronomy-shop --no-headers | head -5")
        print("[smoke] exec_shell ok:")
        print(sh["output"])
        assert len(case.sandbox.call_log) == 4
        print(f"[smoke] call_log entries: {[c['tool'] for c in case.sandbox.call_log]}")
        # submit + evaluate round-trip (fault IS injected, so ['ad'] should score 100)
        confirmed = case.sandbox.submit_diagnosis(["ad", "cart", "checkout", "currency", "frontend"])
        assert confirmed["committed"]
        results = runner.evaluate(case, ["ad", "cart", "checkout", "currency", "frontend"])
        print(f"[smoke] eval results: {results}")
        assert len(case.sandbox.call_log) == 5
        print("[smoke] PASS")
        return 0
    finally:
        runner.teardown(case)
        print("[smoke] fault recovered")






# ---------------------------------------------------------------------------
# LiveTelemetrySandbox — implements the TelemetrySandbox protocol over AIOpsLab
# ---------------------------------------------------------------------------

#: Astronomy Shop services (deterministic ordering for fallback ranking).
AIOPSLAB_SERVICES = [
    "ad", "agent", "cart", "checkout", "currency", "email", "fraud-detection",
    "frontend", "image-provider", "kafka", "payment", "product-catalog",
    "quote", "recommendation", "shipping",
]


class LiveTelemetrySandbox:
    """Drop-in replacement for ``TelemetrySandbox`` backed by a live AIOpsLab cluster.

    Implements the same five OBS tool methods + ``_inventory()`` +
    ``submit_diagnosis()`` so the V4 arms (DetelemDetArm, CEQDetArm) work
    unchanged. Tool calls dispatch to the underlying :class:`AIOpsLabToolSandbox`.
    """

    def __init__(self, live_sandbox: "AIOpsLabToolSandbox", *, namespace: str,
                 task_description: str, max_tool_calls: int = 48) -> None:
        self._live = live_sandbox
        self._namespace = namespace
        self._task_description = task_description
        self._max_tool_calls = max_tool_calls
        self._total_calls = 0
        self._invoked: dict[str, int] = {}
        self.call_log: list[dict[str, Any]] = []
        self._submission: dict[str, Any] | None = None

    def _inventory(self) -> list[str]:
        return list(AIOPSLAB_SERVICES)

    def system_context(self) -> dict[str, Any]:
        self._check_budget("system_context")
        started = time.monotonic()
        payload = {
            "services": AIOPSLAB_SERVICES,
            "namespace": self._namespace,
            "task": self._task_description[:2000],
            "note": "Live environment. Use top_anomalies/service_metrics/service_logs/service_traces.",
        }
        return self._finish("system_context", {}, started, payload)

    def top_anomalies(self, k: int = 20) -> dict[str, Any]:
        self._check_budget("top_anomalies")
        started = time.monotonic()
        obs = self._live.get_metrics(k=max(k, 5))
        if not obs.get("available"):
            return self._finish("top_anomalies", {"k": k}, started,
                                {"error": "metrics unavailable", "detail": str(obs)[:500]})
        preview = obs.get("preview", "")[:4000]
        return self._finish("top_anomalies", {"k": k}, started,
                            {"metrics_preview": preview, "export_dir": obs.get("export_dir", "")})

    def service_metrics(self, svc: str, k: int = 30) -> dict[str, Any]:
        self._check_budget("service_metrics")
        started = time.monotonic()
        obs = self._live.get_metrics(k=max(k, 5))
        if not obs.get("available"):
            return self._finish("service_metrics", {"svc": svc, "k": k}, started,
                                {"error": "metrics unavailable"})
        preview = obs.get("preview", "")[:4000]
        return self._finish("service_metrics", {"svc": svc, "k": k}, started,
                            {"service": svc, "metrics_preview": preview})

    def service_logs(self, svc: str, k: int = 50) -> dict[str, Any]:
        self._check_budget("service_logs")
        started = time.monotonic()
        obs = self._live.get_logs(svc=svc, k=k)
        logs_text = obs.get("logs", "")[:4000]
        return self._finish("service_logs", {"svc": svc, "k": k}, started,
                            {"service": svc, "count": obs.get("count", 0), "logs": logs_text})

    def service_traces(self, svc: str, k: int = 30) -> dict[str, Any]:
        self._check_budget("service_traces")
        started = time.monotonic()
        obs = self._live.get_traces(svc=svc, k=k)
        if not obs.get("available"):
            return self._finish("service_traces", {"svc": svc, "k": k}, started,
                                {"error": "traces unavailable", "detail": str(obs)[:500]})
        preview = obs.get("preview", "")[:4000]
        return self._finish("service_traces", {"svc": svc, "k": k}, started,
                            {"service": svc, "traces_preview": preview})

    def submit_diagnosis(self, ranked_services: list[str]) -> dict[str, Any]:
        if self._submission is not None:
            raise RuntimeError("diagnosis already committed")
        valid = [s for s in ranked_services if s in AIOPSLAB_SERVICES]
        if not valid:
            raise ValueError(f"no valid services in diagnosis: {ranked_services}")
        self._submission = {"ranking": valid, "submitted_at": time.monotonic()}
        return self._submission

    def _check_budget(self, tool: str) -> None:
        if self._total_calls >= self._max_tool_calls:
            from repliclaw.experiments.v3.telemetry import ToolBudgetExhausted
            raise ToolBudgetExhausted(f"total tool budget exhausted ({self._max_tool_calls} calls)")

    def _finish(self, tool: str, args: dict, started: float, payload: Any) -> Any:
        self._total_calls += 1
        self._invoked[tool] = self._invoked.get(tool, 0) + 1
        sanitized = json.loads(json.dumps(payload, default=str))
        self.call_log.append({
            "tool": tool,
            "args": args,
            "wall_ms": round((time.monotonic() - started) * 1000.0, 3),
            "payload_bytes": len(json.dumps(sanitized).encode("utf-8")),
        })
        return sanitized


if __name__ == "__main__":
    sys.exit(_smoke_test())
