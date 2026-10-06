"""Offline tests for the SimulaChat AgentRx client adapter (D-V3-010).

No network in these tests: ``simula._http_post_json`` is monkeypatched.
"""
from __future__ import annotations

import json
import types
from typing import Any, Dict

import pytest

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
