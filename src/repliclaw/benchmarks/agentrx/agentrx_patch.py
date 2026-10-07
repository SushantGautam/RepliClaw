"""Runtime wiring of the SimulaChat client into AgentRx@7a18c797 (READ-ONLY).

The upstream checkout
``/Users/sushantgautam/Documents/stg2-worktrees/agentrx-upstream`` must not be
modified (pinned read-only source of truth). AgentRx hardcodes its three
LLM endpoints (``copilot | azure | trapi``) in five client-selection seams:

* ``agentrx.ir.trajectory_ir.llm_ir``            (IR stage)
* ``agentrx.invariants.static_invariant_generator`` (static stage)
* ``agentrx.invariants.dynamic_invariant_generator`` (dynamic stage, 2 sites)
* ``agentrx.invariants.checker``                  (check stage)
* ``agentrx.judge.judge.get_llm_judge_class``     (judge stage)

:func:`apply_simula_patch` monkey-patches ONLY the shared factory objects
those seams import (``copilot_cli.copilot_mk_client``,
``copilot_cli._verify_cli``, ``copilot_cli.LLMAgent``,
``trapi.LLMAgent.trapi_mk_client``) and the globals the judge reads for its
model name. After patching, the stages run with ``endpoint="simulachat"`` —
a string our :class:`_EndpointChoice` (an ``str`` subclass assigned to
``agentrx.pipeline.globals.DEFAULT_ENDPOINT``) makes pass argparse's
``choices`` validation. No upstream file on disk is ever written.

Scientific label: D-V3-010 (docs/next_stage/DECISIONS.md). Every run through
this wiring is a **MODEL-SUBSTITUTION BASELINE**, never the official AgentRx
baseline; :func:`stamp_model_substitution_metadata` enforces the label in
run metadata.

Mechanical label enforcement (F-W2-10): the routed factories REFUSE to
serve completions until :func:`stamp_model_substitution_metadata` has been
called for the active run dir (identified by the ``REPLICLAW_RUN_DIR``
environment variable, exported before the pipeline stages run). The override
``apply_simula_patch(..., enforce_label=False)`` disables this check —
**tests only**, never for official/live runs.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional

from .simula import (
    DEFAULT_MODEL,
    MODEL_SUBSTITUTION_LABEL,
    LLMAgent,
    SimulaChatClient,
    load_config,
)

#: Endpoint name this patch introduces.
ENDPOINT = "simulachat"

#: LLM completion log served by the patched factories since the last
#: :func:`apply_simula_patch` call (test/diagnostics + token provenance).
CALLS_SERVED: List[Dict[str, Any]] = []

#: Env var naming the run dir active for the current patched pipeline run.
#: The routed factories refuse to serve completions until
#: :func:`stamp_model_substitution_metadata` has been called for it.
ACTIVE_RUN_DIR_ENV = "REPLICLAW_RUN_DIR"

#: Run dirs for which the model-substitution label has been stamped by
#: :func:`stamp_model_substitution_metadata` in this process.
STAMPED_RUN_DIRS: List[str] = []


class SimulaChatNotStampedError(RuntimeError):
    """Raised by the routed SimulaChat factories when the active run dir has
    not been labeled via :func:`stamp_model_substitution_metadata`."""

__all__ = [
    "ACTIVE_RUN_DIR_ENV",
    "CALLS_SERVED",
    "ENDPOINT",
    "STAMPED_RUN_DIRS",
    "SimulaChatNotStampedError",
    "SimulaPatchState",
    "apply_simula_patch",
    "stamp_model_substitution_metadata",
    "total_tokens_served",
]


class _EndpointChoice(str):
    """``str`` subclass that also equals the native endpoint choices.

    Assigned to ``agentrx.pipeline.globals.DEFAULT_ENDPOINT`` (which
    ``run.py`` uses as argparse ``choices``). Argparse validates with
    ``value in choices`` → ``value == _EndpointChoice`` → our ``__eq__``
    returns True for "copilot"/"azure"/"trapi"/"simulachat". Native stages
    that compare ``endpoint == "trapi"`` etc. against *literals* still do a
    plain string equality where the left side is our value, so
    "simulachat" matches nothing native and flows to the TRAPI else-branch
    — which is exactly the factory we patched to serve SimulaChat.
    """

    def __eq__(self, other: object) -> bool:
        return isinstance(other, str) and str(self) in ("copilot", "azure", "trapi", ENDPOINT)

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash("simula-choice")


def _serve(enforce_label: bool = True, **_kwargs: Any) -> SimulaChatClient:
    """Factory body: enforce the label gate, then build + record.

    Refuses to serve until the active run dir (``REPLICLAW_RUN_DIR``) has
    been stamped via :func:`stamp_model_substitution_metadata`, unless
    *enforce_label* is False — an explicit override **for tests only**.
    """
    if enforce_label:
        active = os.environ.get(ACTIVE_RUN_DIR_ENV)
        if active is not None and active not in STAMPED_RUN_DIRS:
            raise SimulaChatNotStampedError(
                "SimulaChat client refused: the active run dir "
                f"({active!r}) has not been labeled with "
                f"stamp_model_substitution_metadata(). Every run through "
                f"this wiring is a {MODEL_SUBSTITUTION_LABEL!r} baseline; "
                "stamp the run metadata BEFORE the pipeline stages run. "
                "(Override with apply_simula_patch(..., enforce_label=False) "
                "for tests only — never for official/live runs.)"
            )
    client = SimulaChatClient(config=load_config())
    CALLS_SERVED.append({"factory": "client"})
    return client


class _LLMAgentRoute(LLMAgent):
    """LLMAgent route that records judge constructions and every completion
    with its real token usage (provenance for the substitution baseline)."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # kwargs never contains config for the judge: apply_simula_patch
        # stamps _label_enforced so the label gate matches the patch.
        enforce = kwargs.pop("_label_enforced", True)
        if enforce:
            active = os.environ.get(ACTIVE_RUN_DIR_ENV)
            if active is not None and active not in STAMPED_RUN_DIRS:
                raise SimulaChatNotStampedError(
                    "SimulaChat LLMAgent refused: the active run dir "
                    f"({active!r}) has not been labeled with "
                    f"stamp_model_substitution_metadata(). {MODEL_SUBSTITUTION_LABEL}"
                    " (Override with apply_simula_patch(..., enforce_label=False) "
                    "for tests only — never for official/live runs.)"
                )
        super().__init__(*args, **kwargs)
        CALLS_SERVED.append({"factory": "LLMAgent", "model_name": self.model_name})

    def get_llm_response(self, messages: Any) -> Any:
        response = super().get_llm_response(messages)
        usage = getattr(response, "usage", None)
        CALLS_SERVED.append({
            "factory": "completion",
            "model_name": self.model_name,
            "prompt_tokens": getattr(usage, "prompt_tokens", 0),
            "completion_tokens": getattr(usage, "completion_tokens", 0),
            "total_tokens": getattr(usage, "total_tokens", 0),
            "execution_time_sec": self.last_call_telemetry.execution_time_sec
            if self.last_call_telemetry else None,
        })
        return response


def total_tokens_served() -> Dict[str, int]:
    """Aggregate real token usage over all completions served so far."""
    out = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
           "completions": 0}
    for call in CALLS_SERVED:
        if call.get("factory") == "completion":
            out["completions"] += 1
            for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
                out[k] += int(call.get(k, 0) or 0)
    return out


def apply_simula_patch(agentrx_root: str,
                       enforce_label: bool = True) -> "SimulaPatchState":
    """Patch AgentRx (imported from *agentrx_root*) for endpoint
    ``"simulachat"``. Returns a :class:`SimulaPatchState` with ``undo()``.

    *enforce_label* (default True) makes the routed factories refuse to
    serve completions until :func:`stamp_model_substitution_metadata` has
    been called for the active run dir (``REPLICLAW_RUN_DIR`` env var).
    Pass ``enforce_label=False`` **for tests only** — never for
    official/live runs (F-W2-10).
    """
    if agentrx_root not in sys.path:
        sys.path.insert(0, agentrx_root)

    import agentrx.invariants.checker as checker_mod  # noqa: F401 (import for seam existence)
    import agentrx.invariants.dynamic_invariant_generator as dyn_mod  # noqa: F401
    import agentrx.invariants.static_invariant_generator as static_mod  # noqa: F401
    import agentrx.ir.trajectory_ir as ir_mod  # noqa: F401
    import agentrx.judge.judge as judge_mod
    import agentrx.llm_clients.copilot_cli as copilot_mod
    import agentrx.llm_clients.trapi as trapi_mod
    import agentrx.pipeline.globals as g

    saved = {
        "DEFAULT_ENDPOINT": g.DEFAULT_ENDPOINT,
        "TRAPI_DEPLOYMENT_NAME": g.TRAPI_DEPLOYMENT_NAME,
        "TRAPI_MODEL_NAME": g.TRAPI_MODEL_NAME,
        "copilot_mk_client": copilot_mod.copilot_mk_client,
        "verify_cli": copilot_mod._verify_cli,
        "copilot_LLMAgent": copilot_mod.LLMAgent,
        "trapi_mk_client": trapi_mod.LLMAgent.trapi_mk_client,
        "get_llm_judge_class": judge_mod.get_llm_judge_class,
    }

    # 1. Make "simulachat" pass argparse choices validation.
    g.DEFAULT_ENDPOINT = _EndpointChoice(str(saved["DEFAULT_ENDPOINT"]))  # type: ignore[assignment]

    # 2. The judge reads its model name from g.TRAPI_MODEL_NAME /
    #    g.TRAPI_DEPLOYMENT_NAME when the endpoint is not "azure"
    #    (run.py L418, judge.py L1089); point both at our model so the
    #    actual completion request carries the SimulaChat model id.
    g.TRAPI_DEPLOYMENT_NAME = load_config().model
    g.TRAPI_MODEL_NAME = load_config().model

    # 3. Client-factory seams. "simulachat" falls into each stage's TRAPI
    #    else-branch (and llm_ir would raise, so llm_ir is handled by
    #    endpoint normalization below); serve SimulaChat there. The stages
    #    call ``LLMAgentTrapi.trapi_mk_client()`` (staticmethod, no args).
    def _trapi_mk_routed(enforce_label: bool = enforce_label,
                         *args: Any, **kwargs: Any) -> Any:
        return _serve(enforce_label=enforce_label)

    trapi_mod.LLMAgent.trapi_mk_client = _trapi_mk_routed  # type: ignore[assignment]

    # The IR stage raises on unknown endpoints before reaching a factory,
    # so normalize its endpoint argument to "copilot" and serve SimulaChat
    # through the copilot factory instead.
    _orig_llm_ir = ir_mod.llm_ir

    def _llm_ir_routed(trajectories: Any, *, endpoint: str = "azure", **kwargs: Any) -> Any:
        if str(endpoint) == ENDPOINT:
            copilot_mod.copilot_mk_client = _serve
            copilot_mod._verify_cli = lambda: None
            result = _orig_llm_ir(trajectories, endpoint="copilot", **kwargs)
            # llm_ir stamps model="copilot-cli" on IR records; normalize to
            # the real SimulaChat model for provenance.
            try:
                for rec in result:
                    if isinstance(rec, dict) and rec.get("model") == "copilot-cli":
                        rec["model"] = load_config().model
            except TypeError:
                pass
            return result
        return _orig_llm_ir(trajectories, endpoint=endpoint, **kwargs)

    saved["llm_ir"] = _orig_llm_ir
    ir_mod.llm_ir = _llm_ir_routed  # type: ignore[assignment]

    # 4. Judge: the native factory builds LLMJudge by subclassing
    #    copilot_cli.LLMAgent (when endpoint=="copilot"). Route it: set
    #    ENDPOINT_USED to "copilot" for one call while copilot_mod.LLMAgent
    #    points at our LLMAgent, so the judge class body (all
    #    _parse_json_response / judge_response methods) is preserved
    #    verbatim and only the LLM transport is ours.
    # Route the judge's LLMAgent construction through the label gate by
    # injecting _label_enforced (popped in _LLMAgentRoute.__init__).
    class _LLMAgentRouteEnforced(_LLMAgentRoute):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            kwargs.setdefault("_label_enforced", enforce_label)
            super().__init__(*args, **kwargs)

    def _get_llm_judge_class_routed():
        if str(judge_mod.ENDPOINT_USED) == ENDPOINT:
            copilot_mod.LLMAgent = _LLMAgentRouteEnforced
            judge_mod.ENDPOINT_USED = "copilot"
            try:
                cls = saved["get_llm_judge_class"]()
            finally:
                copilot_mod.LLMAgent = saved["copilot_LLMAgent"]
                judge_mod.ENDPOINT_USED = ENDPOINT
            return cls
        return saved["get_llm_judge_class"]()

    judge_mod.get_llm_judge_class = _get_llm_judge_class_routed  # type: ignore[assignment]

    # 5. Normalize "simulachat" → "trapi" at the stage boundaries so the
    #    stages' literal comparisons land on the (patched) TRAPI branch.
    _orig_run_py_stages: Dict[str, Any] = {}

    def _make_endpoint_normalizer(stage_name: str, fn: Any) -> Any:
        def _wrapped(*args: Any, **kwargs: Any):
            # run.py calls run_ir(input, run_dir, domain, endpoint, state)
            # positionally; signature: (input_path, run_dir, domain,
            #  endpoint, state, [extra...]).
            new_args = list(args)
            if len(new_args) >= 4 and str(new_args[3]) == ENDPOINT:
                new_args[3] = "trapi"
            elif "endpoint" in kwargs and str(kwargs["endpoint"]) == ENDPOINT:
                kwargs["endpoint"] = "trapi"
            result = fn(*new_args, **kwargs)
            CALLS_SERVED.append({"stage": stage_name})
            return result
        return _wrapped

    try:
        import run as run_py  # type: ignore[import-not-found]

        for name in ("run_ir", "run_static", "run_dynamic", "run_check", "run_judge"):
            if hasattr(run_py, name):
                _orig_run_py_stages[name] = getattr(run_py, name)
                setattr(run_py, name, _make_endpoint_normalizer(name, getattr(run_py, name)))
    except ImportError:
        # run.py only importable from the AgentRx repo root; stage-level
        # normalization is then skipped (callers must pass "trapi" or the
        # judge endpoint directly). The factory-level patches above still
        # make the pipeline simulachat-served.
        pass

    state = SimulaPatchState(
        judge_mod=judge_mod, g=g, copilot_mod=copilot_mod, trapi_mod=trapi_mod,
        ir_mod=ir_mod, run_py_mod=_import_run_py_or_none(),
        run_py=_orig_run_py_stages, saved=saved,
    )
    return state


def _import_run_py_or_none() -> Any:
    """Import run.py from the AgentRx root if possible; else None.

    Undo must not depend on re-importing run.py (F-W2-2); capture the
    module object once, at apply time, best-effort.
    """
    try:
        import run as run_py  # type: ignore[import-not-found]
        return run_py
    except ImportError:
        return None


class SimulaPatchState:
    """Holds the originals for :meth:`undo`. Keeps module references for
    tests and the smoke runner.

    Restores come from the snapshot taken at :func:`apply_simula_patch`
    time (module objects + original attribute values); :meth:`undo` never
    re-imports anything (F-W2-2).
    """

    def __init__(self, judge_mod: Any, g: Any, copilot_mod: Any, trapi_mod: Any,
                 ir_mod: Any, run_py_mod: Any,
                 run_py: Dict[str, Any], saved: Dict[str, Any]) -> None:
        self.judge_mod = judge_mod
        self.g = g
        self.copilot_mod = copilot_mod
        self.trapi_mod = trapi_mod
        self._ir_mod = ir_mod
        self._run_py_mod = run_py_mod
        self._run_py = run_py
        self._saved = saved
        self._undone = False

    def undo(self) -> None:
        """Best-effort, idempotent restore (F-W2-2).

        Every patched attribute is restored from the apply-time snapshot in
        its own try/except, so one failing step never leaves the process
        half-patched by omission. If ANY attribute could not be restored,
        a single :class:`RuntimeError` is raised at the end naming all of
        them — fail loud, never silently half-patched. A second ``undo()``
        call is a no-op (the snapshot only describes the patched state).
        """
        if self._undone:
            return
        self._undone = True

        s = self._saved
        failures: List[str] = []

        def _restore(label: str, target: Any, attr: str, value: Any) -> None:
            try:
                setattr(target, attr, value)
            except BaseException as e:  # noqa: BLE001 — report, keep restoring
                failures.append(f"{label}.{attr} ({e!r})")

        _restore("g", self.g, "DEFAULT_ENDPOINT", s["DEFAULT_ENDPOINT"])
        _restore("g", self.g, "TRAPI_DEPLOYMENT_NAME", s["TRAPI_DEPLOYMENT_NAME"])
        _restore("g", self.g, "TRAPI_MODEL_NAME", s["TRAPI_MODEL_NAME"])
        _restore("trapi_mod.LLMAgent", self.trapi_mod.LLMAgent,
                 "trapi_mk_client", s["trapi_mk_client"])
        _restore("copilot_mod", self.copilot_mod, "copilot_mk_client",
                 s["copilot_mk_client"])
        _restore("copilot_mod", self.copilot_mod, "_verify_cli", s["verify_cli"])
        _restore("copilot_mod", self.copilot_mod, "LLMAgent", s["copilot_LLMAgent"])
        _restore("judge_mod", self.judge_mod, "get_llm_judge_class",
                 s["get_llm_judge_class"])
        if "llm_ir" in s:
            _restore("ir_mod", self._ir_mod, "llm_ir", s["llm_ir"])
        if self._run_py_mod is not None:
            for name, fn in self._run_py.items():
                _restore(f"run_py.{name}", self._run_py_mod, name, fn)

        if failures:
            raise RuntimeError(
                "apply_simula_patch().undo() could not restore "
                f"{len(failures)} attribute(s); the process may still be "
                "patched — do NOT run the official pipeline in this "
                "process. Unrestored: " + "; ".join(failures)
            )


def stamp_model_substitution_metadata(run_dir: str,
                                      extra: Optional[Dict[str, Any]] = None) -> str:
    """Write the mandatory model-substitution label into ``<run_dir>/state.json``.

    Creates the file if run.py has not written state yet; merges otherwise.
    Idempotent — the label is always (re)written and can only be
    strengthened, never weakened. Returns the state file path.
    """
    path = os.path.join(run_dir, "state.json")
    state: Dict[str, Any] = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
    state["scientific_label"] = MODEL_SUBSTITUTION_LABEL
    state["llm_provenance"] = {
        "endpoint": ENDPOINT,
        "provider": "SimulaChat (D-V3-010, human-authorized 2026-10-10)",
        "model": os.environ.get("SIMULACHAT_MODEL", DEFAULT_MODEL),
        "base_url_configured": bool(os.environ.get("SIMULACHAT_BASE_URL")),
        "api_key_configured": bool(os.environ.get("SIMULACHAT_API_KEY")),
        "official_baseline": False,
    }
    if extra:
        state.setdefault("simula_run_extra", {}).update(extra)
    os.makedirs(run_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    # Mechanical label gate (F-W2-10): the routed factories will serve
    # completions for this run dir only after this call has succeeded.
    canonical = os.path.abspath(run_dir)
    if canonical not in STAMPED_RUN_DIRS:
        STAMPED_RUN_DIRS.append(canonical)
    return path
