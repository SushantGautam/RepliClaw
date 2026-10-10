"""Offline tests for the SimulaChat AgentRx client adapter (D-V3-010).

No network in these tests: ``simula._http_post_json`` is monkeypatched.
"""
from __future__ import annotations

import json
import sys
import types
from typing import Any, Dict

import pytest

import repliclaw.benchmarks.agentrx.agentrx_patch as agentrx_patch
import repliclaw.benchmarks.agentrx.simula as simula
from repliclaw.benchmarks.agentrx import (
    MODEL_SUBSTITUTION_LABEL,
    SimulaChatClient,
    SimulaChatMissingEnvError,
    SimulaLLMAgent,
    load_config,
    simula_mk_client,
    stamp_model_substitution_metadata,
)


@pytest.fixture
def clean_env(monkeypatch):
    for var in ("SIMULACHAT_BASE_URL", "SIMULACHAT_API_KEY", "SIMULACHAT_MODEL"):
        monkeypatch.delenv(var, raising=False)
    yield


def _fake_response(**overrides):
    body = {
        "id": "chatcmpl-test",
        "model": "Qwen3.8-27B",
        "object": "chat.completion",
        "choices": [{
            "index": 0,
            "finish_reason": "stop",
            "message": {"role": "assistant", "content": "hello world"},
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 13},
    }
    body.update(overrides)
    return body


@pytest.fixture
def fake_transport(monkeypatch):
    """Replaces the HTTP layer; records (url, payload) of every call."""
    calls: list = []

    def _fake(url: str, payload: Dict[str, Any], api_key: str, timeout: float):
        assert api_key == "sk-test-key", "bearer key must be forwarded"
        calls.append({"url": url, "payload": payload, "key": api_key, "timeout": timeout})
        return _fake_response()

    monkeypatch.setattr(simula, "_http_post_json", _fake)
    return calls


# --- env construction -------------------------------------------------------

def test_load_config_missing_vars_raise(clean_env):
    with pytest.raises(SimulaChatMissingEnvError) as ei:
        load_config()
    msg = str(ei.value)
    assert "SIMULACHAT_BASE_URL" in msg and "SIMULACHAT_API_KEY" in msg
    assert "D-V3-010" in msg


def test_load_config_partial_missing_names_the_missing(clean_env, monkeypatch):
    monkeypatch.setenv("SIMULACHAT_BASE_URL", "https://example.test/api/v1")
    with pytest.raises(SimulaChatMissingEnvError) as ei:
        load_config()
    msg = str(ei.value)
    assert "SIMULACHAT_API_KEY" in msg
    # only the missing var may appear in the "Missing required..." clause
    missing_clause = msg.split(". Export")[0]
    assert "SIMULACHAT_BASE_URL" not in missing_clause


def test_load_config_from_env(clean_env, monkeypatch):
    monkeypatch.setenv("SIMULACHAT_BASE_URL", "https://example.test/api/v1/")
    monkeypatch.setenv("SIMULACHAT_API_KEY", "sk-test-key")
    cfg = load_config()
    assert cfg.base_url == "https://example.test/api/v1/"
    assert cfg.api_key == "sk-test-key"
    assert cfg.model == "default"
    assert cfg.chat_completions_url == "https://example.test/api/v1/chat/completions"
    assert cfg.models_url == "https://example.test/api/v1/models"


def test_load_config_explicit_args_override_env(clean_env, monkeypatch):
    monkeypatch.setenv("SIMULACHAT_BASE_URL", "https://from-env.test/v1")
    monkeypatch.setenv("SIMULACHAT_API_KEY", "sk-env")
    cfg = load_config(base_url="https://explicit.test/v1", api_key="sk-explicit", model="m2")
    assert cfg.base_url == "https://explicit.test/v1"
    assert cfg.api_key == "sk-explicit"
    assert cfg.model == "m2"


def test_simula_mk_client_requires_env(clean_env):
    with pytest.raises(SimulaChatMissingEnvError):
        simula_mk_client()


# --- request shape (offline) -------------------------------------------------

def _client(monkeypatch, model="default"):
    monkeypatch.setenv("SIMULACHAT_BASE_URL", "https://sim.test/api/v1")
    monkeypatch.setenv("SIMULACHAT_API_KEY", "sk-test-key")
    monkeypatch.setenv("SIMULACHAT_MODEL", model)
    return SimulaChatClient(timeout=7.5)


def test_create_request_shape_and_response(monkeypatch, fake_transport):
    client = _client(monkeypatch, model="default")
    resp = client.chat.completions.create(
        model="default",
        messages=[{"role": "user", "content": "hi"}],
        temperature=0.2,
    )
    (call,) = fake_transport
    assert call["url"] == "https://sim.test/api/v1/chat/completions"
    assert call["payload"] == {
        "model": "default",
        "messages": [{"role": "user", "content": "hi"}],
        "temperature": 0.2,
    }
    assert call["timeout"] == 7.5
    # OpenAI-SDK-shaped response
    assert resp.choices[0].message.content == "hello world"
    assert resp.choices[0].message.role == "assistant"
    assert resp.choices[0].finish_reason == "stop"
    assert resp.usage.prompt_tokens == 10
    assert resp.usage.completion_tokens == 3
    assert resp.usage.total_tokens == 13
    assert resp.model == "Qwen3.8-27B"


def test_create_omitted_model_falls_back_to_config(monkeypatch, fake_transport):
    client = _client(monkeypatch, model="default")
    client.chat.completions.create(messages=[{"role": "user", "content": "x"}])
    (call,) = fake_transport
    assert call["payload"]["model"] == "default"
    # unknown kwargs like max_tokens must be forwarded
    fake_transport.clear()
    client.chat.completions.create(messages=[], max_tokens=100)
    assert fake_transport[0]["payload"]["max_tokens"] == 100


def test_no_network_at_import_or_construction(monkeypatch):
    """Construction must not touch the network even with env set."""
    monkeypatch.setenv("SIMULACHAT_BASE_URL", "https://sim.test/api/v1")
    monkeypatch.setenv("SIMULACHAT_API_KEY", "sk-test-key")

    def _no_network(*_a, **_kw):
        pytest.fail("network called during construction")

    monkeypatch.setattr(simula, "_http_post_json", _no_network)
    client = SimulaChatClient()
    assert client.config.api_key == "sk-test-key"
    c2 = simula_mk_client()
    assert c2.config.base_url == "https://sim.test/api/v1"


def test_llm_agent_interface_matches_copilot_client(clean_env, monkeypatch):
    monkeypatch.setenv("SIMULACHAT_BASE_URL", "https://sim.test/api/v1")
    monkeypatch.setenv("SIMULACHAT_API_KEY", "sk-test-key")
    agent = SimulaLLMAgent(api_version="v1", model_name="default",
                           model_version="", deployment_name="default")
    # attribute set mirrors copilot_cli.LLMAgent.__init__
    assert agent.api_version == "v1"
    assert agent.model_name == "default"
    assert agent.model_version == ""
    assert agent.deployment_name == "default"
    assert agent.endpoint == "simulachat"
    assert agent.last_call_telemetry is None
    assert agent.client.config.api_key == "sk-test-key"
    assert isinstance(agent.get_llm_response, types.MethodType)


def test_llm_agent_get_llm_response_records_telemetry(monkeypatch, fake_transport):
    monkeypatch.setenv("SIMULACHAT_BASE_URL", "https://sim.test/api/v1")
    monkeypatch.setenv("SIMULACHAT_API_KEY", "sk-test-key")
    agent = SimulaLLMAgent(api_version="v1", model_name="default",
                           model_version="", deployment_name="default")
    resp = agent.get_llm_response([{"role": "user", "content": "t"}])
    assert resp.choices[0].message.content == "hello world"
    assert agent.last_call_telemetry is not None
    assert agent.last_call_telemetry.total_tokens == 13
    assert agent.last_call_telemetry.model_name == "default"
    assert agent.last_call_telemetry.instance == "https://sim.test/api/v1"
    assert agent.last_call_telemetry.execution_time_sec >= 0


# --- mandatory model-substitution label --------------------------------------

def test_label_string_is_exact():
    assert MODEL_SUBSTITUTION_LABEL == (
        "MODEL-SUBSTITUTION BASELINE (SimulaChat default, Qwen3.8-27B) — "
        "NOT the official released AgentRx baseline"
    )


def test_stamp_metadata_writes_label(tmp_path, monkeypatch):
    monkeypatch.setenv("SIMULACHAT_MODEL", "default")
    run_dir = tmp_path / "runs" / "tiny_smoke"
    path = stamp_model_substitution_metadata(str(run_dir), extra={"trajectories": 2, "iterations": 1})
    state = json.loads(open(path).read())
    assert state["scientific_label"] == MODEL_SUBSTITUTION_LABEL
    assert state["llm_provenance"]["endpoint"] == "simulachat"
    assert state["llm_provenance"]["official_baseline"] is False
    assert state["simula_run_extra"]["trajectories"] == 2


def test_stamp_metadata_merges_existing_state(tmp_path, monkeypatch):
    run_dir = tmp_path / "runs" / "existing"
    run_dir.mkdir(parents=True)
    existing = {"run_name": "existing", "stages": ["ir", "judge"]}
    (run_dir / "state.json").write_text(json.dumps(existing))
    stamp_model_substitution_metadata(str(run_dir))
    state = json.loads((run_dir / "state.json").read_text())
    assert state["run_name"] == "existing"
    assert state["stages"] == ["ir", "judge"]
    assert state["scientific_label"] == MODEL_SUBSTITUTION_LABEL


# --- agentrx_patch: safe undo (F-W2-2) + mechanical label gate (F-W2-10) ----

class _BlockImportFinder:
    """sys.meta_path hook: make named imports raise ImportError (simulated)."""

    def __init__(self, names):
        self._names = set(names)

    def find_spec(self, name, path=None, target=None):
        if name in self._names:
            raise ImportError(f"simulated: {name} is not importable")
        return None


class _Breaker:
    """Proxy module that raises on setattr of one attribute (fail-loud test)."""

    def __init__(self, inner, break_attr):
        object.__setattr__(self, "_i", inner)
        object.__setattr__(self, "_b", break_attr)

    def __setattr__(self, name, value):
        if name == self._b:
            raise OSError("simulated restore failure")
        setattr(self._i, name, value)

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_i"), name)


@pytest.fixture
def mock_agentrx(monkeypatch, tmp_path):
    """In-memory mock of the AgentRx module tree the patch touches.

    run.py is made unimportable (F-W2-2 scenario: process moved / different
    cwd), and the block stays installed so undo() cannot import it either.
    """
    for name in ("agentrx", "agentrx.invariants", "agentrx.invariants.checker",
                 "agentrx.invariants.dynamic_invariant_generator",
                 "agentrx.invariants.static_invariant_generator",
                 "agentrx.ir", "agentrx.ir.trajectory_ir",
                 "agentrx.judge", "agentrx.judge.judge",
                 "agentrx.llm_clients", "agentrx.llm_clients.copilot_cli",
                 "agentrx.llm_clients.trapi", "agentrx.pipeline",
                 "agentrx.pipeline.globals", "run"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    monkeypatch.setattr(sys, "meta_path",
                        [_BlockImportFinder({"run"})] + list(sys.meta_path))

    mods: Dict[str, types.ModuleType] = {}

    def mod(name, **attrs):
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        mods[name] = m
        monkeypatch.setitem(sys.modules, name, m)
        return m

    class FakeCopilotLLMAgent:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    class FakeTrapiLLMAgent:
        @staticmethod
        def trapi_mk_client(**_kwargs: Any):
            return "trapi-client"

    def _orig_llm_ir(trajectories, *, endpoint="azure", **kwargs):
        return []

    def _orig_judge_factory():
        # Build a judge class that subclasses the copilot LLMAgent, like
        # agentrx.judge.judge.get_llm_judge_class does for endpoint copilot.
        class FakeJudge(copilot_mod.LLMAgent):  # noqa: F821 (closure)
            def __init__(self, **kw):
                super().__init__(**kw)
        return FakeJudge

    def _orig_copilot_mk_client(**_kwargs: Any):
        return "copilot-client"

    def _orig_verify_cli() -> bool:
        return True

    mod("agentrx")
    mod("agentrx.invariants")
    mod("agentrx.invariants.checker")
    mod("agentrx.invariants.dynamic_invariant_generator")
    mod("agentrx.invariants.static_invariant_generator")
    mod("agentrx.ir")
    ir_mod = mod("agentrx.ir.trajectory_ir", llm_ir=_orig_llm_ir)
    mod("agentrx.judge")
    judge_mod = mod("agentrx.judge.judge",
                    get_llm_judge_class=_orig_judge_factory,
                    ENDPOINT_USED="trapi")
    mod("agentrx.llm_clients")
    copilot_mod = mod("agentrx.llm_clients.copilot_cli",
                      copilot_mk_client=_orig_copilot_mk_client,
                      _verify_cli=_orig_verify_cli,
                      LLMAgent=FakeCopilotLLMAgent)
    trapi_mod = mod("agentrx.llm_clients.trapi", LLMAgent=FakeTrapiLLMAgent)
    mod("agentrx.pipeline")
    g = mod("agentrx.pipeline.globals",
            DEFAULT_ENDPOINT="copilot",
            TRAPI_DEPLOYMENT_NAME="orig-deployment",
            TRAPI_MODEL_NAME="orig-model")

    monkeypatch.setenv("SIMULACHAT_BASE_URL", "https://sim.test/api/v1")
    monkeypatch.setenv("SIMULACHAT_API_KEY", "sk-test-key")
    monkeypatch.delenv("REPLICLAW_RUN_DIR", raising=False)

    import repliclaw.benchmarks.agentrx.agentrx_patch as patch_mod

    def _apply(*a, **kw):
        return patch_mod.apply_simula_patch(str(tmp_path / "agentrx"), *a, **kw)

    return types.SimpleNamespace(
        root=str(tmp_path / "agentrx"),
        apply=_apply,
        g=g, ir_mod=ir_mod, judge_mod=judge_mod,
        copilot_mod=copilot_mod, trapi_mod=trapi_mod,
        orig=types.SimpleNamespace(
            llm_ir=_orig_llm_ir,
            judge_factory=_orig_judge_factory,
            copilot_mk_client=_orig_copilot_mk_client,
            verify_cli=_orig_verify_cli,
            copilot_llm_agent=FakeCopilotLLMAgent,
            trapi_mk_client=FakeTrapiLLMAgent.trapi_mk_client,
            default_endpoint="copilot",
            deployment="orig-deployment",
            model="orig-model",
        ),
    )


def _assert_unpatched(mock_agentrx) -> None:
    o = mock_agentrx.orig
    assert mock_agentrx.g.DEFAULT_ENDPOINT == o.default_endpoint
    assert mock_agentrx.g.TRAPI_DEPLOYMENT_NAME == o.deployment
    assert mock_agentrx.g.TRAPI_MODEL_NAME == o.model
    assert mock_agentrx.trapi_mod.LLMAgent.trapi_mk_client == o.trapi_mk_client
    assert mock_agentrx.copilot_mod.copilot_mk_client == o.copilot_mk_client
    assert mock_agentrx.copilot_mod._verify_cli == o.verify_cli
    assert mock_agentrx.copilot_mod.LLMAgent is o.copilot_llm_agent
    assert mock_agentrx.judge_mod.get_llm_judge_class == o.judge_factory
    assert mock_agentrx.ir_mod.llm_ir is o.llm_ir


def test_undo_restores_all_attributes_when_run_py_import_fails(mock_agentrx):
    """F-W2-2: run.py unimportable at apply AND at undo time; undo() must
    still restore every patched attribute from the apply-time snapshot."""
    state = mock_agentrx.apply()
    # sanity: the patch is live
    assert mock_agentrx.trapi_mod.LLMAgent.trapi_mk_client is not mock_agentrx.orig.trapi_mk_client
    assert mock_agentrx.ir_mod.llm_ir is not mock_agentrx.orig.llm_ir
    assert mock_agentrx.judge_mod.get_llm_judge_class is not mock_agentrx.orig.judge_factory
    assert type(mock_agentrx.g.DEFAULT_ENDPOINT).__name__ == "_EndpointChoice"

    state.undo()  # must not raise, even though `import run` would
    _assert_unpatched(mock_agentrx)


def test_undo_twice_is_safe(mock_agentrx):
    state = mock_agentrx.apply()
    state.undo()
    state.undo()  # idempotent no-op
    _assert_unpatched(mock_agentrx)


def test_undo_fails_loud_when_one_attribute_cannot_be_restored(mock_agentrx):
    state = mock_agentrx.apply()
    # Break exactly one restore target; every other attribute must still
    # be restored, and undo must raise a summary error naming the failure.
    state.g = _Breaker(state.g, "TRAPI_MODEL_NAME")
    with pytest.raises(RuntimeError, match="TRAPI_MODEL_NAME"):
        state.undo()
    assert mock_agentrx.g.TRAPI_DEPLOYMENT_NAME == mock_agentrx.orig.deployment
    assert mock_agentrx.copilot_mod.copilot_mk_client is mock_agentrx.orig.copilot_mk_client
    assert mock_agentrx.copilot_mod.LLMAgent is mock_agentrx.orig.copilot_llm_agent
    assert mock_agentrx.judge_mod.get_llm_judge_class is mock_agentrx.orig.judge_factory
    assert mock_agentrx.ir_mod.llm_ir is mock_agentrx.orig.llm_ir
    assert mock_agentrx.trapi_mod.LLMAgent.trapi_mk_client is mock_agentrx.orig.trapi_mk_client


def test_unstamped_run_dir_completions_refused(mock_agentrx, monkeypatch):
    """F-W2-10: routed factories refuse to serve until the active run dir
    is stamped."""
    state = mock_agentrx.apply()
    monkeypatch.setenv(agentrx_patch.ACTIVE_RUN_DIR_ENV,
                       "/nonexistent/agentrx-run-unstamped")
    try:
        with pytest.raises(agentrx_patch.SimulaChatNotStampedError):
            mock_agentrx.trapi_mod.LLMAgent.trapi_mk_client()
        # judge path is gated too
        mock_agentrx.judge_mod.ENDPOINT_USED = agentrx_patch.ENDPOINT
        cls = mock_agentrx.judge_mod.get_llm_judge_class()
        with pytest.raises(agentrx_patch.SimulaChatNotStampedError):
            cls(api_version="v1", model_name="default")
    finally:
        state.undo()
    _assert_unpatched(mock_agentrx)


def test_stamped_run_dir_completions_proceed(mock_agentrx, tmp_path, monkeypatch):
    """F-W2-10: after stamping, the same factories serve (offline)."""
    state = mock_agentrx.apply()
    run_dir = tmp_path / "runs" / "stamped"
    monkeypatch.setenv(agentrx_patch.ACTIVE_RUN_DIR_ENV, str(run_dir))
    try:
        stamp_model_substitution_metadata(str(run_dir))
        client = mock_agentrx.trapi_mod.LLMAgent.trapi_mk_client()
        assert isinstance(client, SimulaChatClient)
        # judge path: class builds and instantiates
        mock_agentrx.judge_mod.ENDPOINT_USED = agentrx_patch.ENDPOINT
        cls = mock_agentrx.judge_mod.get_llm_judge_class()
        judge = cls(api_version="v1", model_name="default")
        assert isinstance(judge, SimulaLLMAgent)
    finally:
        state.undo()
    _assert_unpatched(mock_agentrx)


def test_enforce_label_override_allows_unstamped_for_tests(mock_agentrx, tmp_path,
                                                           monkeypatch):
    """F-W2-10: apply(..., enforce_label=False) — tests-only override."""
    state = mock_agentrx.apply(enforce_label=False)
    monkeypatch.setenv(agentrx_patch.ACTIVE_RUN_DIR_ENV,
                       str(tmp_path / "runs" / "not-stamped"))
    try:
        client = mock_agentrx.trapi_mod.LLMAgent.trapi_mk_client()
        assert isinstance(client, SimulaChatClient)
    finally:
        state.undo()
    _assert_unpatched(mock_agentrx)
