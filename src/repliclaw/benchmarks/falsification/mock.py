"""Deterministic offline LLM double for the ``--dry-run`` harness check.

This is a SCRIPTED double (same pattern as the indepinfo test suite's
``ScriptedLLMClient``): it subclasses :class:`repliclaw.investigators.LLMClient`
and overrides :meth:`chat_messages` to return canned, well-formed JSON actions
and to advance ``self.usage`` exactly like the real client. It makes NO network
calls.

It is used ONLY to validate the harness plumbing end to end (all four arms run,
produce per-claim conclusions, enforce the matched caps, score against ground
truth, hold partition isolation, and capture receipts). The verdicts it emits
are deterministic stubs — a ``--dry-run`` result is a HARNESS CHECK, NOT a
scientific result, and must never be reported as one.

Format detection: the double inspects the system prompt. If it contains
``hypothesis_statement`` it emits the indepinfo escrow commit shape; otherwise
it emits the pooled commit shape (``verdict``/``reasoning``). The verdict is a
stable function of (system prompt, agent seed) so the aggregation and scoring
paths are exercised with varied inputs.
"""
from __future__ import annotations

import hashlib
import json
from typing import Optional

from repliclaw.investigators import BudgetExceeded, LLMClient, LLMConfig

_VALID = ("TRUE", "FALSE", "ABSTAIN")


def _verdict_for(system_prompt: str, agent_seed: str) -> str:
    h = hashlib.sha256((system_prompt + "|" + agent_seed).encode("utf-8")).hexdigest()
    return _VALID[int(h, 16) % len(_VALID)]


class MockLLMClient(LLMClient):
    """Offline scripted double: canned JSON commits + deterministic usage."""

    def __init__(self, agent_seed: str = "mock", model: str = "mock-dryrun", per_call=(40, 12)) -> None:
        super().__init__(
            cfg=LLMConfig(base_url="http://fake.invalid/v1", api_key="fake", model=model, max_calls=10_000)
        )
        self.agent_seed = agent_seed
        self._per_call = (int(per_call[0]), int(per_call[1]))

    def chat_messages(self, messages: list, max_tokens: Optional[int] = None) -> str:
        if self._calls >= self.cfg.max_calls:
            raise BudgetExceeded("mock client exceeded max_calls")
        self._calls += 1
        # Advance usage exactly like the real client (cumulative, in place).
        p, c = self._per_call
        self.usage.prompt_tokens += p
        self.usage.completion_tokens += c
        self.usage.total_tokens = self.usage.prompt_tokens + self.usage.completion_tokens
        self.usage.llm_calls += 1
        self.last_model = self.cfg.model

        system = next((m["content"] for m in messages if m.get("role") == "system"), "")
        verdict = _verdict_for(system, self.agent_seed)

        if "hypothesis_statement" in system:
            # indepinfo escrow commit shape.
            return json.dumps(
                {
                    "action": "commit",
                    "hypothesis_statement": f"VERDICT: {verdict} (mock dry-run stub for {self.agent_seed}).",
                    "predicted_outcome": "mock: the sealed prediction would be confirmed on reveal.",
                    "refutation_criterion": "mock: an observation contradicting the sealed prediction.",
                    "competing_explanation": "mock: the strongest alternative reading of the source.",
                    "intervention_id": "observational_only",
                    "estimated_cost": {"tokens": 100, "wall_s": 1.0},
                }
            )
        # pooled commit shape.
        return json.dumps(
            {
                "action": "commit",
                "verdict": verdict,
                "reasoning": f"mock dry-run stub verdict for {self.agent_seed}.",
            }
        )


__all__ = ["MockLLMClient"]
