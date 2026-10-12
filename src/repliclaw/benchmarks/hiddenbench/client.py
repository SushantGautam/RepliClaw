"""Capped, usage-counting LLM clients for the HiddenBench arms.

Live mode talks to the SimulaChat OpenAI-compatible endpoint
(``REPLICLAW_LLM_BASE_URL`` / ``REPLICLAW_LLM_API_KEY`` / model id
``REPLICLAW_LLM_MODEL``, default ``default`` = Qwen3.8-27B). Because that is
a model substitution relative to HiddenBench's released baselines, all
results must carry the MODEL-SUBSTITUTION label.

``FakeClient`` is a deterministic offline double (no network) used for the
smoke test — same interface, same caps, canned JSON votes.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Optional


DEFAULT_BASE_URL = "https://simulachat.sushant.pp.ua/api/v1"
DEFAULT_MODEL = "default"


class ArmBudgetExceeded(Exception):
    """Raised when an arm's call or token cap is exhausted."""


@dataclass
class Usage:
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def to_dict(self) -> dict[str, Any]:
        return {
            "calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


class CountingOpenAIClient:
    """OpenAI-compatible chat client with per-arm call/token caps."""

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        *,
        max_calls: int = 256,
        max_total_tokens: int = 200_000,
        temperature: float = 0.2,
        timeout: float = 120.0,
        max_retries: int = 2,
    ) -> None:
        self.model = model or os.environ.get("REPLICLAW_LLM_MODEL", DEFAULT_MODEL)
        base = base_url or os.environ.get("REPLICLAW_LLM_BASE_URL", DEFAULT_BASE_URL)
        key = (
            api_key
            or os.environ.get("REPLICLAW_LLM_API_KEY")
            or os.environ.get("CUSTOM_SIMULACHAT_KEY")
            or ""
        )
        if not key:
            raise RuntimeError(
                "No LLM API key configured. Export REPLICLAW_LLM_API_KEY or use fake mode."
            )
        from openai import OpenAI

        self._client = OpenAI(base_url=base, api_key=key, timeout=timeout)
        self.max_calls = int(max_calls)
        self.max_total_tokens = int(max_total_tokens)
        self.temperature = float(temperature)
        self.max_retries = int(max_retries)
        self.usage = Usage()
        self.base_url = base

    def _check_budget(self) -> None:
        if self.usage.calls >= self.max_calls:
            raise ArmBudgetExceeded(f"call cap reached ({self.max_calls})")
        if self.usage.total_tokens >= self.max_total_tokens:
            raise ArmBudgetExceeded(f"token cap reached ({self.max_total_tokens})")

    def chat(self, messages: list[dict[str, str]], max_tokens: int = 512) -> str:
        self._check_budget()
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                self.usage.calls += 1
                resp = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=int(max_tokens),
                    temperature=self.temperature,
                )
                u = getattr(resp, "usage", None)
                if u is not None:
                    self.usage.prompt_tokens += int(getattr(u, "prompt_tokens", 0) or 0)
                    self.usage.completion_tokens += int(getattr(u, "completion_tokens", 0) or 0)
                return resp.choices[0].message.content or ""
            except Exception as exc:  # network hiccups, retry with backoff
                last_error = exc
                time.sleep(min(2**attempt, 8))
        assert last_error is not None
        raise last_error

    def chat_json(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        max_tokens: int = 512,
    ) -> dict[str, Any]:
        import json

        from ._vendor import ensure_path

        ensure_path()
        from hiddenbench.models import extract_json_object

        json_instruction = {
            "role": "user",
            "content": (
                "Return only one valid JSON object. Do not include markdown or commentary.\n"
                f"Required JSON schema: {json.dumps(schema)}"
            ),
        }
        text = self.chat(messages + [json_instruction], max_tokens=max_tokens)
        return extract_json_object(text)


class FakeClient:
    """Deterministic offline client (smoke mode). Valid votes, no network."""

    def __init__(
        self,
        *,
        max_calls: int = 256,
        max_total_tokens: int = 200_000,
        per_call: tuple[int, int] = (40, 12),
    ) -> None:
        self.model = "fake-v1"
        self.base_url = "http://fake.invalid/v1"
        self.max_calls = int(max_calls)
        self.max_total_tokens = int(max_total_tokens)
        self._per_call = per_call
        self.usage = Usage()

    def _check_budget(self) -> None:
        if self.usage.calls >= self.max_calls:
            raise ArmBudgetExceeded(f"call cap reached ({self.max_calls})")
        if self.usage.total_tokens >= self.max_total_tokens:
            raise ArmBudgetExceeded(f"token cap reached ({self.max_total_tokens})")

    def chat(self, messages: list[dict[str, str]], max_tokens: int = 512) -> str:
        self._check_budget()
        self.usage.calls += 1
        self.usage.prompt_tokens += self._per_call[0]
        self.usage.completion_tokens += self._per_call[1]
        return "My evidence packet: the shared facts point to the first option."

    def chat_json(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        max_tokens: int = 512,
    ) -> dict[str, Any]:
        self._check_budget()
        self.usage.calls += 1
        self.usage.prompt_tokens += self._per_call[0]
        self.usage.completion_tokens += self._per_call[1]
        last_user = next(
            (m["content"] for m in reversed(messages)
             if isinstance(m, dict) and m.get("role") == "user"),
            "",
        )
        digest = sum(ord(c) for c in last_user)
        answers = (
            schema.get("properties", {})
            .get("vote", {})
            .get("enum")
            or ["answer_A", "answer_B", "answer_C"]
        )
        answers = list(answers)
        vote = answers[digest % len(answers)]
        out: dict[str, Any] = {"vote": vote, "rationale": "deterministic fake vote"}
        if "ranking" in schema.get("properties", {}):
            i = answers.index(vote)
            out["ranking"] = [answers[(i + offset) % len(answers)] for offset in range(len(answers))]
        return out
