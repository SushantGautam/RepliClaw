"""Offline, deterministic LLM double for the live EESS arms.

This is the ONLY place a "fake" model is defined, and it is used strictly to
UNIT-TEST the live arms and the token-floor measurement script with NO network
and NO API key (the hard rules: no live LLM API keys, no network calls, all
tests pass offline). It subclasses :class:`repliclaw.investigators.LLMClient`
and overrides :meth:`chat` to return canned, purpose-keyed JSON and to advance
``self.usage`` by a FIXED per-call delta — so the arm's snapshot-delta budget
accounting (and its never-zero-fill usage check) is exercised exactly as it
would be against a real endpoint.

The canned payload is keyed off a marker embedded in the prompt:

* a prompt containing ``PRE-OUTCOME_COMMIT``   -> ``commit_payload``
* a prompt containing ``POST_EVIDENCE_VERDICT`` -> ``verdict_payload``

Each payload may be a single dict (used for every agent) or a dict keyed by
``agent_id`` (the ``AGENT_ID: <id>`` marker in the prompt selects it), so a
test can model per-agent disagreement (different confidences/conclusions).
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from ..investigators import LLMClient, LLMConfig

COMMIT_MARKER = "PRE-OUTCOME_COMMIT"
VERDICT_MARKER = "POST_EVIDENCE_VERDICT"
_AGENT_MARKER = "AGENT_ID:"


def _select(pay: Any, agent_id: str) -> Dict[str, Any]:
    """Return the payload for ``agent_id`` (per-agent dict or single dict)."""
    if isinstance(pay, dict) and any(k == agent_id for k in pay):
        return dict(pay[agent_id])
    return dict(pay)


class FakeLLMClient(LLMClient):
    """Canned, deterministic stand-in for a real OpenAI-compatible endpoint."""

    def __init__(
        self,
        per_call: tuple = (40, 12),
        commit_payload: Optional[Dict[str, Any]] = None,
        verdict_payload: Optional[Dict[str, Any]] = None,
        model: str = "fake-v1",
        base_url: str = "http://fake.invalid/v1",
    ) -> None:
        super().__init__(
            cfg=LLMConfig(base_url=base_url, api_key="fake", model=model, max_calls=10_000)
        )
        self._per_call = (int(per_call[0]), int(per_call[1]))
        self._commit_payload: Any = commit_payload or {
            "hypothesis_statement": "The baseline failure is a hidden retrieval omission.",
            "predicted_outcome": "The corrected-retrieval arm changes the target output.",
            "refutation_criterion": "Refuted iff the corrected arm leaves the target unchanged.",
            "competing_explanation": "A stale judge rubric alone could flip the severity.",
            "confidence": 0.7,
        }
        self._verdict_payload: Any = verdict_payload or {
            "conclusion": "supported",
            "confidence": 0.8,
            "defect_class": "retrieval_omission",
            "target_artifact": "retrieval",
            "statement": "Corrected retrieval changes the target; failure is a retrieval omission.",
        }

    # -- the single override: canned content + deterministic usage ----------
    def chat(
        self,
        prompt: str,
        system: str = "You are a careful, quantitative scientific investigator.",
        max_tokens: Optional[int] = None,
    ) -> str:
        if self._calls >= self.cfg.max_calls:
            from ..investigators import BudgetExceeded

            raise BudgetExceeded("fake client exceeded max_calls")
        self._calls += 1
        p, c = self._per_call
        # Advance usage exactly like the real client (cumulative, in place).
        self.usage.prompt_tokens += p
        self.usage.completion_tokens += c
        self.usage.total_tokens = self.usage.prompt_tokens + self.usage.completion_tokens
        self.usage.llm_calls += 1

        agent_id = "unknown"
        if _AGENT_MARKER in prompt:
            for line in prompt.splitlines():
                if line.strip().startswith(_AGENT_MARKER):
                    agent_id = line.split(":", 1)[1].strip()
        if COMMIT_MARKER in prompt:
            return json.dumps(_select(self._commit_payload, agent_id))
        if VERDICT_MARKER in prompt:
            return json.dumps(_select(self._verdict_payload, agent_id))
        # Fallback: a neutral finding (should not occur for the arm's prompts).
        return json.dumps({"conclusion": "uncertain", "confidence": 0.5})

    # convenience: expose a raw endpoint-availability flag for the measure
    # script's guard (a fake is clearly NOT a real, authorized endpoint).
    @property
    def is_real_endpoint(self) -> bool:
        return False


__all__ = ["FakeLLMClient", "COMMIT_MARKER", "VERDICT_MARKER"]
