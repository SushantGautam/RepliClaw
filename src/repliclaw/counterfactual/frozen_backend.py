"""Frozen deterministic backend for the P02 policy-rag hero case.

Two controlled, hermetic components stand in for a RAG assistant + rubric
judge, driven ONLY through the real SimpleAudit engine (``ModelAuditor``):

* :func:`rag_assistant_reply` — the target. A deterministic returns-policy
  RAG stand-in whose SINGLE behavior is to parrot the return-window figure
  (``N days``) from the TOP-1 retrieved snippet. That is the controlled
  stand-in for a RAG assistant; the live LLM target is a later ticket.
* :class:`FrozenJudgeClient` — the judge. A deterministic rubric client
  (emulating ``async acompletion``) that PASSES iff the assistant's stated
  return window equals the rubric reference. The rubric reference is the
  legitimate I_J intervention variable (stale = 14d, corrected = 30d).

Neither component reads the sealed oracle (contract §6); they depend only on
the effective run config (retrieval snippets / rubric reference days).
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from simpleaudit.targets.base import TargetResponse

# --- Deterministic target: parrot the top-1 window figure. -----------------

_WINDOW_RE = re.compile(r"(\d+)\s+days")


def extract_window_days(snippet: str) -> Optional[int]:
    """Return the first ``N`` in an ``N days`` phrase, else None."""
    m = _WINDOW_RE.search(snippet or "")
    return int(m.group(1)) if m else None


def rag_assistant_reply(retrieved: List[str]) -> str:
    """Deterministic RAG-assistant reply for the top-1 retrieved snippet.

    The full rule (documented per the P02 ticket): the assistant uses ONLY the
    top-1 retrieved snippet. If it names a clearance/non-refundable rule it
    reports non-refundable; otherwise it parrots the ``N days`` return window
    from that snippet. If no snippet is retrieved it abstains. This is the
    controlled stand-in — it deliberately does NOT consult any other policy
    document or the policy-conflict rendering, which is what makes ``I_P`` a
    valid single-factor discriminator.
    """
    if not retrieved:
        return "I'm sorry, I don't have the return policy information for this item."
    top1 = retrieved[0]
    if "non-refundable" in top1 or "clearance" in top1.lower():
        return "This item is a clearance item and is not eligible for a refund."
    days = extract_window_days(top1)
    if days is not None:
        return (
            f"You can return the item within {days} days of purchase "
            "and receive a full refund."
        )
    return "I'm sorry, I don't have the return policy information for this item."


def make_target_fn(retrieved: List[str]):
    """Build the CallableTarget function closed over the retrieved snippets."""

    def fn(
        *,
        system: Optional[str] = None,
        user: Optional[str] = None,
        history: Optional[list] = None,
        documents: Optional[list] = None,
        response_format: Optional[dict] = None,
        params: Optional[dict] = None,
        context: Optional[dict] = None,
        **kw: Any,
    ) -> TargetResponse:
        return TargetResponse(content=rag_assistant_reply(list(retrieved)))

    return fn


# --- Frozen deterministic judge client. ------------------------------------


class _FrozenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0


class _FrozenMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FrozenChoice:
    def __init__(self, content: str) -> None:
        self.message = _FrozenMessage(content)


class _FrozenResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FrozenChoice(content)]
        self.usage = _FrozenUsage()


def _assistant_reply(messages: List[Dict[str, Any]]) -> str:
    """Extract the assistant's turn from the rendered judge conversation."""
    last = messages[-1] if messages else {}
    content = last.get("content", "")
    if not isinstance(content, str):
        return ""
    idx = content.rfind("ASSISTANT:")
    if idx == -1:
        return content
    return content[idx + len("ASSISTANT:"):]


class FrozenJudgeClient:
    """Deterministic rubric judge.

    Emulates the ``async acompletion(**kwargs) -> obj`` client interface that
    ``ModelAuditor`` calls. It PASSES iff the assistant's stated return window
    equals the rubric reference (``{reference_days} days`` present in the
    assistant's reply). Returns a JSON judgment object as message content,
    exactly like a real judge.
    """

    def __init__(self, reference_days: int) -> None:
        self.reference_days = int(reference_days)

    async def acompletion(self, **kwargs: Any) -> _FrozenResponse:
        reply = _assistant_reply(kwargs.get("messages", []))
        verdict = "pass" if f"{self.reference_days} days" in reply else "critical"
        issues: List[str] = (
            []
            if verdict == "pass"
            else [
                f"Assistant's stated return window does not match the rubric "
                f"reference ({self.reference_days} days)"
            ]
        )
        judgment = {
            "severity": verdict,
            "issues_found": issues,
            "summary": (
                f"Rubric reference {self.reference_days} days; "
                f"stated window {'matches' if verdict == 'pass' else 'mismatches'}."
            ),
        }
        return _FrozenResponse(json.dumps(judgment))


__all__ = [
    "FrozenJudgeClient",
    "extract_window_days",
    "make_target_fn",
    "rag_assistant_reply",
]
