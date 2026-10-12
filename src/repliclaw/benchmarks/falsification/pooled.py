"""Bounded real-LLM investigator for the POOLED arms.

The three pooled arms (open_sharing, central_adaptive, single_investigator)
all see the FULL evidence union and are driven by the same
:class:`repliclaw.investigators.LLMClient` and the same JSON tool protocol as
the indepinfo partitioned investigators — so their receipts are directly
comparable and auditable. The only differences between the pooled arms are the
system prompt (and, for open_sharing, the two-phase share-then-finalize flow),
never the evidence, model, or budget.

Usage integrity follows the repo's "never zero-fill" rule (P08 contract /
judge item 7): per-call usage is measured with the snapshot/delta pattern, and
a call that reports no usage fields INVALIDATES the run (status
``invalid_usage``) — it is never zero-filled.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from repliclaw.benchmarks.indepinfo import CallRecord
from repliclaw.canonical import canonical_json
from repliclaw.eess_live.budget_calls import usage_delta, usage_present, usage_snapshot
from repliclaw.investigators import BudgetExceeded, LLMClient

RECEIPT_SCHEMA = "repliclaw.falsification.pooled_receipt/v1"

VALID_VERDICTS = ("TRUE", "FALSE", "ABSTAIN")

CORRECTION_MSG = (
    "Your last response was not a valid action JSON object. Respond with "
    "exactly one JSON object: either {\"action\": \"tool_call\", \"tool\": "
    "<name>, \"args\": {...}} or {\"action\": \"commit\", \"verdict\": "
    "\"TRUE|FALSE|ABSTAIN\", \"reasoning\": \"...\"}. No prose outside the JSON."
)

_PREVIEW_CHARS = 160


class PooledRunError(RuntimeError):
    """Raised when an LLM call (or the run) fails; the run is failed, not faked."""

    def __init__(self, message: str, receipt: Optional["PooledReceipt"] = None) -> None:
        super().__init__(message)
        self.receipt = receipt


class PooledReceipt(BaseModel):
    """Structured receipt for one pooled-arm investigator (auditable)."""

    schema_: str = Field(default=RECEIPT_SCHEMA, alias="schema")
    agent_id: str
    claim_id: str
    arm: str
    model_requested: str
    model_reported: Optional[str] = None
    status: str = Field(pattern=r"^(committed|bound|failed|invalid_usage)$")
    transcript: List[Dict[str, str]]
    transcript_sha256: str = ""
    calls: List[CallRecord] = Field(default_factory=list)
    num_llm_calls: int = 0
    num_tool_calls: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    wall_s: float = 0.0
    bounds_hit: List[str] = Field(default_factory=list)
    verdict: Optional[str] = None  # TRUE / FALSE / ABSTAIN (None if not committed)
    reasoning: Optional[str] = None
    error: Optional[str] = None

    model_config = {"populate_by_name": True, "frozen": True}

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True)


def _parse_action(content: str):
    """Parse the model's JSON action. Returns (action, tool, args, error)."""
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        return None, None, {}, f"not valid JSON: {e}"
    if not isinstance(obj, dict):
        return None, None, {}, "JSON must be an object"
    action = obj.get("action")
    if action == "tool_call":
        tool = obj.get("tool")
        args = obj.get("args") or {}
        if not isinstance(tool, str) or not isinstance(args, dict):
            return None, None, {}, "tool_call requires string 'tool' and object 'args'"
        return "tool_call", tool, args, None
    if action == "commit":
        return "commit", None, obj, None
    return None, None, {}, f"unknown action {action!r}"


def _transcript_sha256(agent_id: str, transcript: List[Dict[str, str]]) -> str:
    canonical = json.dumps(
        [{"agent": agent_id, "content": e["content"], "role": e["role"]} for e in transcript],
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _preview(record: Any) -> str:
    text = canonical_json(record)
    return text if len(text) <= _PREVIEW_CHARS else text[:_PREVIEW_CHARS] + "…"


class PooledInvestigator:
    """A real LLM investigator over the FULL evidence union (one pooled arm).

    ``artifacts`` is the flat list of all evidence artifacts (the union).
    ``system_prompt`` is arm-specific. ``caps`` is a dict with ``max_turns``,
    ``token_budget``, ``max_tokens_per_call``, ``wall_deadline_s``.
    ``shared_context`` (optional) is appended to the transcript before the
    loop — used by open_sharing's finalize phase to inject the shared
    conclusions.
    """

    def __init__(
        self,
        client: LLMClient,
        agent_id: str,
        claim_id: str,
        arm: str,
        artifacts: List[Dict[str, Any]],
        system_prompt: str,
        caps: Dict[str, Any],
        shared_context: Optional[str] = None,
    ) -> None:
        self.client = client
        self.agent_id = agent_id
        self.claim_id = claim_id
        self.arm = arm
        self.artifacts = artifacts
        self.system_prompt = system_prompt
        self.caps = caps
        self.shared_context = shared_context
        self._receipt: Optional[PooledReceipt] = None

    @property
    def receipt(self) -> Optional[PooledReceipt]:
        return self._receipt

    # -- tools (operate over the FULL union) --------------------------------
    def _execute_tool(self, tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if tool == "list_artifacts":
            return {
                "artifacts": [
                    {
                        "index": i,
                        "artifact_id": a["artifact_id"],
                        "source": a["source"],
                        "title": a["title"],
                    }
                    for i, a in enumerate(self.artifacts)
                ]
            }
        if tool == "get_artifact":
            raw = args.get("index")
            if not isinstance(raw, int) or isinstance(raw, bool):
                return {"error": "get_artifact requires integer 'index'"}
            if not 0 <= raw < len(self.artifacts):
                return {"error": f"index {raw} out of range (0..{len(self.artifacts) - 1})"}
            return self.artifacts[raw]
        if tool == "search_artifacts":
            q = str(args.get("query", "")).lower()
            if not q:
                return {"error": "search_artifacts requires non-empty 'query'"}
            hits = []
            for i, a in enumerate(self.artifacts):
                hay = (a["artifact_id"] + " " + a["title"] + " " + a["content"]).lower()
                if q in hay:
                    hits.append({"index": i, **a})
            return {"query": q, "count": len(hits), "artifacts": hits[:20]}
        if tool == "source_info":
            sid = str(args.get("source_id", ""))
            srcs = {a["source"] for a in self.artifacts}
            return {"sources": sorted(srcs), "requested": sid or None}
        return {
            "error": (
                f"unknown tool {tool!r}; available: list_artifacts, get_artifact, "
                "search_artifacts, source_info"
            )
        }

    # -- main loop -----------------------------------------------------------
    def run(self) -> PooledReceipt:
        model = self.client.cfg.model
        start = time.monotonic()
        transcript: List[Dict[str, str]] = [
            {"role": "system", "content": self.system_prompt},
        ]
        if self.shared_context:
            transcript.append({"role": "user", "content": self.shared_context})
        transcript.append(
            {"role": "user", "content": "Begin. Respond with exactly one JSON object."}
        )
        calls: List[CallRecord] = []
        total_prompt = total_completion = total_tokens = 0
        num_tool_calls = 0
        bounds_hit: List[str] = []
        status = "bound"
        error: Optional[str] = None
        model_reported: Optional[str] = None
        verdict: Optional[str] = None
        reasoning: Optional[str] = None

        try:
            for turn in range(1, int(self.caps["max_turns"]) + 1):
                if time.monotonic() - start >= float(self.caps["wall_deadline_s"]):
                    bounds_hit.append("wall_deadline")
                    break
                before = usage_snapshot(self.client)
                t0 = time.perf_counter()
                try:
                    content = self.client.chat_messages(
                        transcript, max_tokens=int(self.caps["max_tokens_per_call"])
                    )
                except BudgetExceeded:
                    bounds_hit.append("client_max_calls")
                    status = "bound"
                    break
                except Exception as e:  # endpoint down, HTTP error, timeout...
                    status = "failed"
                    error = f"LLM call failed on turn {turn}: {type(e).__name__}: {e}"
                    break
                wall = time.perf_counter() - t0
                delta = usage_delta(before, usage_snapshot(self.client))
                present = usage_present(delta)
                call_prompt = delta.prompt_tokens
                call_completion = delta.completion_tokens
                call_total = delta.total_tokens
                total_prompt += call_prompt
                total_completion += call_completion
                total_tokens += call_total
                reported = getattr(self.client, "last_model", None)
                if isinstance(reported, str) and reported:
                    model_reported = reported
                content = (content or "").strip()
                transcript.append({"role": "assistant", "content": content})

                action, tool, args, parse_error = _parse_action(content)
                calls.append(
                    CallRecord(
                        turn=turn,
                        model_requested=model,
                        model_reported=model_reported,
                        prompt_tokens=call_prompt,
                        completion_tokens=call_completion,
                        total_tokens=call_total,
                        wall_s=round(wall, 4),
                        action=action,
                        tool=tool,
                        error=parse_error,
                        usage_present=present,
                    )
                )

                if not present:
                    status = "invalid_usage"
                    error = (
                        f"LLM call on turn {turn} reported no usage fields — "
                        "run invalidated (never zero-filled)"
                    )
                    break

                if action is None:
                    transcript.append({"role": "user", "content": CORRECTION_MSG})
                elif action == "tool_call" and tool is not None:
                    num_tool_calls += 1
                    result = self._execute_tool(tool, args)
                    transcript.append(
                        {"role": "user", "content": json.dumps({"tool_result": result}, ensure_ascii=False)}
                    )
                elif action == "tool_call":
                    transcript.append({"role": "user", "content": CORRECTION_MSG})
                else:  # commit
                    v = str(args.get("verdict", "")).strip().upper()
                    if v not in VALID_VERDICTS:
                        transcript.append(
                            {
                                "role": "user",
                                "content": (
                                    f"Your commit was rejected: 'verdict' must be one of "
                                    f"{list(VALID_VERDICTS)}. Respond with a corrected commit "
                                    "JSON object."
                                ),
                            }
                        )
                        continue
                    verdict = v
                    reasoning = str(args.get("reasoning", "")).strip() or None
                    status = "committed"
                    break

                if total_tokens > int(self.caps["token_budget"]):
                    bounds_hit.append("token_budget")
                    status = "bound"
                    break
            else:
                bounds_hit.append("max_turns")
                status = "bound"
        except Exception as e:  # unexpected
            status = "failed"
            error = f"unexpected error: {type(e).__name__}: {e}"

        receipt = PooledReceipt(
            agent_id=self.agent_id,
            claim_id=self.claim_id,
            arm=self.arm,
            model_requested=model,
            model_reported=model_reported,
            status=status,
            transcript=transcript,
            transcript_sha256=_transcript_sha256(self.agent_id, transcript),
            calls=calls,
            num_llm_calls=len(calls),
            num_tool_calls=num_tool_calls,
            total_prompt_tokens=total_prompt,
            total_completion_tokens=total_completion,
            total_tokens=total_tokens,
            wall_s=round(time.monotonic() - start, 4),
            bounds_hit=bounds_hit,
            verdict=verdict,
            reasoning=reasoning,
            error=error,
        )
        self._receipt = receipt
        if status in ("failed", "invalid_usage"):
            raise PooledRunError(f"pooled investigator {self.agent_id!r} {status}: {error}", receipt=receipt)
        return receipt


__all__ = [
    "RECEIPT_SCHEMA",
    "VALID_VERDICTS",
    "PooledRunError",
    "PooledReceipt",
    "PooledInvestigator",
]
