"""SimulaChat OpenAI-compatible client adapter for the AgentRx G1 pipeline.

Authorization: D-V3-010 (2026-10-10, human, docs/next_stage/DECISIONS.md).
The SimulaChat default model is the authorized LLM provider for the AgentRx
G1 reproduction and for V3 live arms.

Scientific label (mandatory, J-SCI rule):
    Every run through this client is a **model-substitution** baseline. The
    released AgentRx baseline used a frontier model; this client uses the
    SimulaChat default (Qwen3.8-27B). Numbers from such a run must NEVER be
    presented as the official released AgentRx baseline. The constant
    :data:`MODEL_SUBSTITUTION_LABEL` is the exact string to record in run
    metadata.

Interface (mirrors ``agentrx.llm_clients.copilot_cli`` at
agentrx@7a18c797, which is the read-only source of truth):

    * :class:`SimulaChatClient` — mimics ``openai.AzureOpenAI`` just enough
      for AgentRx: ``client.chat.completions.create(model=..., messages=...,
      **kwargs)`` returns an OpenAI-SDK-shaped response
      (``choices[0].message.content`` / ``usage``).
    * :func:`simula_mk_client` — factory with the same call signature as
      ``copilot_cli.copilot_mk_client(**_kwargs)`` /
      ``azure.LLMAgent.azure_mk_client()``.
    * :class:`LLMAgent` — drop-in replacement for the per-endpoint
      ``LLMAgent`` classes (copilot_cli / azure / trapi) so the judge can
      subclass it: attributes ``api_version`` / ``model_name`` /
      ``model_version`` / ``deployment_name`` / ``endpoint`` /
      ``last_call_telemetry`` and method ``get_llm_response(messages)``.

Configuration — environment variables only, NO hardcoded credentials/URLs:

    SIMULACHAT_BASE_URL  (required) OpenAI-compatible root, e.g.
                         "<host>/api/v1" (no trailing slash needed)
    SIMULACHAT_API_KEY   (required) bearer key for the endpoint
    SIMULACHAT_MODEL     (optional) model id, default "default"

No HTTP traffic happens at import time or construction time except an
optional ``/models`` reachability check (:meth:`SimulaChatClient.verify`,
not called automatically). Tests run fully offline (monkeypatched
transport).
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

#: Mandatory scientific label for any run performed through this client.
MODEL_SUBSTITUTION_LABEL = (
    "MODEL-SUBSTITUTION BASELINE (SimulaChat default, Qwen3.8-27B) — NOT the "
    "official released AgentRx baseline"
)

ENV_BASE_URL = "SIMULACHAT_BASE_URL"
ENV_API_KEY = "SIMULACHAT_API_KEY"
ENV_MODEL = "SIMULACHAT_MODEL"

DEFAULT_MODEL = "default"
DEFAULT_TIMEOUT = 120.0
MAX_RETRIES = 3
INITIAL_BACKOFF = 2.0

__all__ = [
    "DEFAULT_MODEL",
    "ENV_API_KEY",
    "ENV_BASE_URL",
    "ENV_MODEL",
    "LLMAgent",
    "MODEL_SUBSTITUTION_LABEL",
    "SimulaChatConfig",
    "SimulaChatClient",
    "SimulaChatMissingEnvError",
    "load_config",
    "simula_mk_client",
]


class SimulaChatMissingEnvError(RuntimeError):
    """Raised when required SIMULACHAT_* environment variables are absent."""


@dataclass(frozen=True)
class SimulaChatConfig:
    """Environment-derived configuration. Never holds secrets in code."""

    base_url: str
    api_key: str
    model: str

    @property
    def chat_completions_url(self) -> str:
        return self.base_url.rstrip("/") + "/chat/completions"

    @property
    def models_url(self) -> str:
        return self.base_url.rstrip("/") + "/models"


def load_config(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> SimulaChatConfig:
    """Build a :class:`SimulaChatConfig` from env vars.

    Explicit arguments override the environment. Raises
    :class:`SimulaChatMissingEnvError` naming every missing variable.
    """
    resolved = {
        ENV_BASE_URL: base_url or os.environ.get(ENV_BASE_URL, ""),
        ENV_API_KEY: api_key or os.environ.get(ENV_API_KEY, ""),
        ENV_MODEL: model or os.environ.get(ENV_MODEL, ""),
    }
    missing = [name for name in (ENV_BASE_URL, ENV_API_KEY) if not resolved[name]]
    if missing:
        raise SimulaChatMissingEnvError(
            "SimulaChat client is not configured. Missing required "
            f"environment variable(s): {', '.join(missing)}. Export "
            f"{ENV_BASE_URL} (OpenAI-compatible root, e.g. '<host>/api/v1') "
            f"and {ENV_API_KEY} (bearer key). Optional: {ENV_MODEL} "
            f"(default '{DEFAULT_MODEL}'). See D-V3-010 in "
            "docs/next_stage/DECISIONS.md."
        )
    return SimulaChatConfig(
        base_url=resolved[ENV_BASE_URL],
        api_key=resolved[ENV_API_KEY],
        model=resolved[ENV_MODEL] or DEFAULT_MODEL,
    )


def _http_post_json(url: str, payload: Dict[str, Any], api_key: str,
                    timeout: float) -> Dict[str, Any]:
    """POST a JSON payload; returns the parsed JSON body.

    Retries transient HTTP errors (429/5xx) and network errors with
    linear backoff. The bearer key is sent in the Authorization header
    and never appears in the payload or in raised messages.
    """
    last_err: Optional[BaseException] = None
    for attempt in range(MAX_RETRIES):
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", "replace")[:300]
            except Exception:
                pass
            last_err = RuntimeError(f"SimulaChat HTTP {e.code}: {body}")
            if e.code not in (408, 429, 500, 502, 503, 504):
                raise last_err
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = e
        time.sleep(INITIAL_BACKOFF * (attempt + 1))
    raise RuntimeError(f"SimulaChat request failed after {MAX_RETRIES} attempts") from last_err


class _Completions:
    """Mimics ``openai.resources.chat.Completions`` (see copilot_cli._Completions)."""

    def __init__(self, config: SimulaChatConfig, timeout: float):
        self._config = config
        self._timeout = timeout

    def create(self, *, model: str = "", messages: List[Dict[str, str]],
               **kwargs: Any) -> SimpleNamespace:
        payload: Dict[str, Any] = {
            "model": model or self._config.model,
            "messages": messages,
        }
        for k in ("temperature", "max_tokens", "top_p", "response_format", "seed"):
            if k in kwargs and kwargs[k] is not None:
                payload[k] = kwargs[k]
        body = _http_post_json(
            self._config.chat_completions_url, payload, self._config.api_key,
            self._timeout,
        )
        choice = body["choices"][0]
        usage = body.get("usage") or {}
        content = choice.get("message", {}).get("content") or ""
        return SimpleNamespace(
            id=body.get("id", ""),
            model=body.get("model") or model or self._config.model,
            choices=[SimpleNamespace(
                message=SimpleNamespace(content=content, role="assistant"),
                index=choice.get("index", 0),
                finish_reason=choice.get("finish_reason", "stop"),
            )],
            usage=SimpleNamespace(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            ),
        )


class _Chat:
    def __init__(self, completions: _Completions):
        self.completions = completions


class SimulaChatClient:
    """Mimics ``openai.AzureOpenAI`` just enough for AgentRx.

    Drop-in for the client objects returned by AgentRx's three existing
    client factories (copilot/azure/trapi): all pipeline stages use it as
    ``client.chat.completions.create(...)``.
    """

    def __init__(self,
                 config: Optional[SimulaChatConfig] = None,
                 timeout: float = DEFAULT_TIMEOUT):
        self.config = config or load_config()
        self.timeout = timeout
        completions = _Completions(self.config, timeout)
        self.chat = _Chat(completions)

    def verify(self) -> List[str]:
        """Reachability check via GET /models. Returns available model ids.

        Not called automatically by any factory — construction never makes
        network calls (tests stay offline).
        """
        req = urllib.request.Request(
            self.config.models_url,
            headers={"Authorization": f"Bearer {self.config.api_key}"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return [m.get("id", "") for m in body.get("data", [])]


def simula_mk_client(**_kwargs: Any) -> SimulaChatClient:
    """Factory — same call signature as ``copilot_cli.copilot_mk_client()``."""
    return SimulaChatClient(**{k: v for k, v in _kwargs.items() if k == "config"})


# ---------------------------------------------------------------------------
# LLMAgent subclass used by judge.py (it inherits from the endpoint's agent
# class, exactly as copilot_cli.LLMAgent / azure.LLMAgent do)
# ---------------------------------------------------------------------------

class LLMAgent:
    """Drop-in replacement for ``llm_clients.{copilot_cli,azure,trapi}.LLMAgent``.

    Attribute set matches ``copilot_cli.LLMAgent.__init__`` so
    ``judge.get_llm_judge_class()`` can subclass it unchanged.
    """

    def __init__(self, api_version: Optional[str] = None,
                 model_name: Optional[str] = None,
                 model_version: Optional[str] = None,
                 deployment_name: Optional[str] = None,
                 **_kwargs: Any):
        self.api_version = api_version or ""
        self.model_name = model_name or DEFAULT_MODEL
        self.model_version = model_version or ""
        self.deployment_name = deployment_name or ""
        self.endpoint = "simulachat"
        self.last_call_telemetry: Optional[Any] = None
        self.client = simula_mk_client(**_kwargs)

    def get_llm_response(self, messages: List[Dict[str, str]]) -> SimpleNamespace:
        """Same contract as azure.LLMAgent.get_llm_response (timing + telemetry)."""
        start_timestamp = time.time()
        start = time.perf_counter()
        response = self.client.chat.completions.create(
            model=self.model_name, messages=messages,
        )
        elapsed = round(time.perf_counter() - start, 4)
        end_timestamp = time.time()
        usage = response.usage
        self.last_call_telemetry = SimpleNamespace(
            prompt_tokens=getattr(usage, "prompt_tokens", 0),
            completion_tokens=getattr(usage, "completion_tokens", 0),
            total_tokens=getattr(usage, "total_tokens", 0),
            execution_time_sec=elapsed,
            start_time=start_timestamp,
            end_time=end_timestamp,
            model_name=self.model_name,
            instance=self.config_url,
        )
        return response

    @property
    def config_url(self) -> str:
        return self.client.config.base_url

    @staticmethod
    def simula_mk_client(**_kwargs: Any) -> SimulaChatClient:
        return simula_mk_client(**_kwargs)
