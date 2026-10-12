"""indepinfo Part C: real-LLM investigators (mocked client, offline).

The LLM is a scripted double subclassing ``repliclaw.investigators.LLMClient``
(same pattern as ``repliclaw.eess_live.fake.FakeLLMClient``): it overrides
``chat_messages`` to return canned JSON actions and advances ``self.usage``
exactly like the real client. Tests cover: receipt content (transcript,
model id, usage, tool calls), per-partition snapshot hash in the sealed
packet, turn/token/wall bounds, LLM failure -> failed run (never faked),
investigator independence (no cross-source bytes in transcripts), and the
full run_case commit -> reveal -> persist lifecycle.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pytest

from repliclaw.benchmarks.indepinfo import (
    Evidence,
    EvidenceRecord,
    EvidenceSource,
    InvestigatorConfig,
    InvestigatorRunError,
    PartitionedInvestigator,
    PartitionVault,
    run_case,
)
from repliclaw.escrow import EscrowLedger, PredictionPacket, commitment_hash, verify_ledger
from repliclaw.investigators import BudgetExceeded, LLMClient, LLMConfig

CASE = "case-investigator-1"


def make_evidence() -> Evidence:
    return Evidence(
        case_id=CASE,
        case_brief="two-source fragmented case",
        sources=[
            EvidenceSource(
                source_id="src-a",
                name="source A",
                description="A",
                records=[
                    EvidenceRecord(record_id="a1", data={"k": "alpha-only-value", "latency_ms": 480}),
                    EvidenceRecord(record_id="a2", data={"k": "alpha-second", "latency_ms": 510}),
                ],
            ),
            EvidenceSource(
                source_id="src-b",
                name="source B",
                description="B",
                records=[EvidenceRecord(record_id="b1", data={"k": "beta-only-value", "queue_depth": 97})],
            ),
        ],
    )


def make_view(tmp_path: Path, agent: str, source_id: str):
    ev = make_evidence()
    ledger = EscrowLedger(tmp_path / f"ledger-{agent}", worker_id="w0")
    vault = PartitionVault(ev, ledger, ev.case_id)
    return ev, ledger, vault, vault.view_for(agent, source_id)


def commit_json(agent: str) -> str:
    return json.dumps(
        {
            "action": "commit",
            "hypothesis_statement": f"{agent}: the checkout latency spike is caused by upstream saturation.",
            "predicted_outcome": f"{agent}: retrying under load reproduces the p99 spike.",
            "refutation_criterion": f"{agent}: the spike disappears with no load change.",
            "competing_explanation": f"{agent}: a deploy at 14:00 changed the routing table.",
            "intervention_id": "observational_only",
            "estimated_cost": {"tokens": 100, "wall_s": 1.0},
        }
    )


def tool_json(tool: str, args: Optional[Dict[str, Any]] = None) -> str:
    return json.dumps({"action": "tool_call", "tool": tool, "args": args or {}})


class ScriptedLLMClient(LLMClient):
    """Offline scripted double: canned JSON actions + deterministic usage."""

    def __init__(
        self,
        script: List[Union[str, Exception]],
        model: str = "mock-qwen-27b",
        per_call: tuple = (40, 12),
        delay_s: float = 0.0,
        no_usage: bool = False,
    ) -> None:
        super().__init__(
            cfg=LLMConfig(base_url="http://fake.invalid/v1", api_key="fake", model=model, max_calls=10_000)
        )
        self._script = list(script)
        self._per_call = (int(per_call[0]), int(per_call[1]))
        self._delay_s = delay_s
        self._no_usage = no_usage
        self.seen_messages: List[List[Dict[str, str]]] = []

    def chat_messages(self, messages: list, max_tokens: Optional[int] = None) -> str:
        if self._calls >= self.cfg.max_calls:
            raise BudgetExceeded("scripted client exceeded max_calls")
        self._calls += 1
        self.seen_messages.append([dict(m) for m in messages])
        if self._delay_s:
            time.sleep(self._delay_s)
        if not self._script:
            raise AssertionError("scripted LLM script exhausted")
        item = self._script.pop(0)
        if isinstance(item, Exception):
            raise item
        if not self._no_usage:
            p, c = self._per_call
            # Advance usage exactly like the real client (cumulative, in place).
            self.usage.prompt_tokens += p
            self.usage.completion_tokens += c
            self.usage.total_tokens = self.usage.prompt_tokens + self.usage.completion_tokens
        # llm_calls always advances (the real client counts the attempt even
        # when the endpoint omits usage) — so a no-usage call yields a zero
        # token delta, which usage_present() correctly flags as absent.
        self.usage.llm_calls += 1
        self.last_model = self.cfg.model
        return item


def make_investigator(tmp_path: Path, agent: str, source_id: str, client: LLMClient,
                      config: Optional[InvestigatorConfig] = None) -> PartitionedInvestigator:
    _, _, _, view = make_view(tmp_path, agent, source_id)
    return PartitionedInvestigator(view, client, config or InvestigatorConfig())


# 1. A mocked LLM yields a receipt with transcript + usage + sealed commit.
def test_mock_investigator_receipt_and_commit(tmp_path: Path):
    client = ScriptedLLMClient(
        [
            tool_json("search_records", {"query": "latency"}),
            tool_json("get_record", {"index": 0}),
            commit_json("inv-1"),
        ]
    )
    inv = make_investigator(tmp_path, "inv-1", "src-a", client)
    receipt = inv.run()

    assert receipt.status == "committed"
    assert receipt.error is None
    # Non-empty full transcript: system + user + assistant turns + tool results.
    assert len(receipt.transcript) >= 6
    assert receipt.transcript[0]["role"] == "system"
    blob = json.dumps(receipt.transcript)
    assert "alpha-only-value" in blob  # own partition is in the prompt
    assert "tool_result" in blob  # tool results were observed between calls
    # Model id + real (mocked) usage.
    assert receipt.model_requested == "mock-qwen-27b"
    assert receipt.model_reported == "mock-qwen-27b"
    assert receipt.total_tokens > 0
    assert receipt.num_llm_calls == 3
    assert receipt.num_tool_calls == 2
    assert receipt.bounds_hit == []
    # Audit-transcript integrity hash (mirrors LLMToolSession.transcript_sha256).
    assert len(receipt.transcript_sha256) == 64
    int(receipt.transcript_sha256, 16)  # is hex
    # Per-call records sum to the totals; every call reported usage.
    assert sum(c.total_tokens for c in receipt.calls) == receipt.total_tokens
    assert all(c.usage_present for c in receipt.calls)
    # Sealed packet: per-partition snapshot hash + verifiable commitment.
    assert receipt.packet is not None
    pkt = PredictionPacket.model_validate(receipt.packet)
    assert commitment_hash(pkt) == receipt.commitment_sha256
    assert pkt.prior_evidence_snapshot_sha256 == inv.view.my_partition().snapshot_sha256
    assert inv.packet is not None


# 2. Token budget bound: stop cleanly, record the bound, no commit.
def test_token_budget_bound(tmp_path: Path):
    client = ScriptedLLMClient(
        [tool_json("list_records"), tool_json("list_records"), tool_json("list_records")],
        per_call=(1000, 100),  # 1100 tokens per call
    )
    inv = make_investigator(
        tmp_path, "inv-1", "src-a", client,
        InvestigatorConfig(max_turns=10, token_budget=2500),
    )
    receipt = inv.run()
    assert receipt.status == "bound"
    assert receipt.bounds_hit == ["token_budget"]
    assert receipt.num_llm_calls == 3  # stopped right after exceeding
    assert receipt.total_tokens == 3300
    assert receipt.packet is None
    assert inv.packet is None


# 3. Max-turns bound: loop exhausts, recorded, no commit.
def test_max_turns_bound(tmp_path: Path):
    client = ScriptedLLMClient([tool_json("list_records")] * 3)
    inv = make_investigator(
        tmp_path, "inv-1", "src-a", client,
        InvestigatorConfig(max_turns=3, token_budget=10_000),
    )
    receipt = inv.run()
    assert receipt.status == "bound"
    assert receipt.bounds_hit == ["max_turns"]
    assert receipt.num_llm_calls == 3
    assert receipt.packet is None


# 4. Wall-clock deadline bound: stop before the next call, recorded.
def test_wall_deadline_bound(tmp_path: Path):
    client = ScriptedLLMClient([tool_json("list_records")] * 5, delay_s=0.05)
    inv = make_investigator(
        tmp_path, "inv-1", "src-a", client,
        InvestigatorConfig(max_turns=10, token_budget=10_000, wall_deadline_s=0.01),
    )
    receipt = inv.run()
    assert receipt.status == "bound"
    assert receipt.bounds_hit == ["wall_deadline"]
    assert receipt.num_llm_calls == 1  # first call ran; second was refused
    assert receipt.packet is None


# 5. LLM failure: raise a clear error; receipt marked failed (never faked).
def test_llm_failure_raises_and_receipt_failed(tmp_path: Path):
    client = ScriptedLLMClient([RuntimeError("endpoint down")])
    inv = make_investigator(tmp_path, "inv-1", "src-a", client)
    with pytest.raises(InvestigatorRunError) as exc_info:
        inv.run()
    assert "endpoint down" in str(exc_info.value)
    receipt = exc_info.value.receipt
    assert receipt is not None
    assert receipt.status == "failed"
    assert "endpoint down" in (receipt.error or "")
    assert len(receipt.transcript) >= 2  # system + initial user prompt
    assert receipt.packet is None


# 6. Independence: no investigator sees the other's source bytes.
def test_investigators_cannot_see_each_others_sources(tmp_path: Path):
    client_a = ScriptedLLMClient([commit_json("inv-1")])
    client_b = ScriptedLLMClient([commit_json("inv-2")])
    inv_a = make_investigator(tmp_path, "inv-1", "src-a", client_a)
    inv_b = make_investigator(tmp_path, "inv-2", "src-b", client_b)
    r_a = inv_a.run()
    r_b = inv_b.run()

    blob_a = json.dumps(r_a.transcript)
    blob_b = json.dumps(r_b.transcript)
    assert "alpha-only-value" in blob_a and "beta-only-value" not in blob_a
    assert "beta-only-value" in blob_b and "alpha-only-value" not in blob_b
    # Each sealed packet hashes its OWN partition.
    assert r_a.packet["prior_evidence_snapshot_sha256"] == inv_a.view.my_partition().snapshot_sha256
    assert r_b.packet["prior_evidence_snapshot_sha256"] == inv_b.view.my_partition().snapshot_sha256
    assert r_a.packet["prior_evidence_snapshot_sha256"] != r_b.packet["prior_evidence_snapshot_sha256"]


# 7. Unparseable response gets a correction, then commits within budget.
def test_unparseable_then_commit(tmp_path: Path):
    client = ScriptedLLMClient(["I think the cause is upstream saturation.", commit_json("inv-1")])
    inv = make_investigator(tmp_path, "inv-1", "src-a", client)
    receipt = inv.run()
    assert receipt.status == "committed"
    assert receipt.num_llm_calls == 2
    assert receipt.calls[0].action is None
    assert "not valid JSON" in (receipt.calls[0].error or "")
    assert any("not a valid action JSON" in m["content"] for m in receipt.transcript)


# 8. run_case: commit -> reveal -> persisted receipts, ledger verifies.
def test_run_case_persists_receipts_and_reveals(tmp_path: Path):
    ev = make_evidence()
    ledger = EscrowLedger(tmp_path / "ledger", worker_id="w0")
    vault = PartitionVault(ev, ledger, ev.case_id)
    client_a = ScriptedLLMClient([commit_json("inv-1")])
    client_b = ScriptedLLMClient([tool_json("source_info"), commit_json("inv-2")])
    inv_a = PartitionedInvestigator(vault.view_for("inv-1", "src-a"), client_a, InvestigatorConfig())
    inv_b = PartitionedInvestigator(vault.view_for("inv-2", "src-b"), client_b, InvestigatorConfig())

    artifacts = tmp_path / "artifacts"
    receipts = run_case([inv_a, inv_b], ledger, ev.case_id, artifacts)

    assert set(receipts) == {"inv-1", "inv-2"}
    for r in receipts.values():
        assert r.status == "committed"
        assert r.reveal_status == "verified"
        assert r.commitment_sha256 is not None

    # Persisted artifacts.
    lines = (artifacts / "receipts.jsonl").read_text().strip().splitlines()
    assert len(lines) == 2
    for ln in lines:
        obj = json.loads(ln)
        assert obj["schema"] == "repliclaw.indepinfo.receipt/v1"
        assert obj["reveal_status"] == "verified"
        assert len(obj["transcript"]) > 0
    summary = json.loads((artifacts / "run_summary.json").read_text())
    assert summary["status"] == "completed"
    assert summary["ledger_violations"] == []
    assert verify_ledger(ledger.root) == []


# 9. run_case with a failed investigator: receipts persisted, then raise.
def test_run_case_failed_run_raises_after_persisting(tmp_path: Path):
    ev = make_evidence()
    ledger = EscrowLedger(tmp_path / "ledger", worker_id="w0")
    vault = PartitionVault(ev, ledger, ev.case_id)
    inv_ok = PartitionedInvestigator(
        vault.view_for("inv-1", "src-a"), ScriptedLLMClient([commit_json("inv-1")]), InvestigatorConfig()
    )
    inv_bad = PartitionedInvestigator(
        vault.view_for("inv-2", "src-b"), ScriptedLLMClient([RuntimeError("boom")]), InvestigatorConfig()
    )
    artifacts = tmp_path / "artifacts"
    with pytest.raises(InvestigatorRunError):
        run_case([inv_ok, inv_bad], ledger, ev.case_id, artifacts)

    lines = (artifacts / "receipts.jsonl").read_text().strip().splitlines()
    assert len(lines) == 2
    by_agent = {json.loads(ln)["agent_id"]: json.loads(ln) for ln in lines}
    assert by_agent["inv-1"]["status"] == "committed"
    assert by_agent["inv-1"]["reveal_status"] == "verified"
    assert by_agent["inv-2"]["status"] == "failed"
    assert by_agent["inv-2"]["reveal_status"] is None
    summary = json.loads((artifacts / "run_summary.json").read_text())
    assert summary["status"] == "failed"
    assert len(summary["failures"]) == 1


# 10. Usage integrity (never zero-fill): a call that reports no usage
#     INVALIDATES the run (status invalid_usage) — it is not zero-filled.
def test_missing_usage_invalidates_run(tmp_path: Path):
    client = ScriptedLLMClient([commit_json("inv-1")], no_usage=True)
    inv = make_investigator(tmp_path, "inv-1", "src-a", client)
    with pytest.raises(InvestigatorRunError) as exc_info:
        inv.run()
    assert "no usage" in str(exc_info.value)
    receipt = exc_info.value.receipt
    assert receipt is not None
    assert receipt.status == "invalid_usage"
    assert "never zero-filled" in (receipt.error or "")
    # The offending call is recorded with usage_present=False so the artifact
    # shows WHERE usage went missing; the total is NOT zero-filled into a
    # valid measurement (the run is void).
    assert len(receipt.calls) == 1
    assert receipt.calls[0].usage_present is False
    assert receipt.total_tokens == 0
    assert receipt.packet is None
    assert inv.packet is None
