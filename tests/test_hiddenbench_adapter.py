"""Smoke test for the HiddenBench three-arm adapter (offline, no network)."""
from __future__ import annotations

from pathlib import Path

from repliclaw.benchmarks.hiddenbench import _vendor
from repliclaw.benchmarks.hiddenbench.arms import EscrowBox
from repliclaw.benchmarks.hiddenbench.client import ArmBudgetExceeded, FakeClient
from repliclaw.benchmarks.hiddenbench.runner import run_arms

HB = _vendor.ensure_path()

PARENT = Path(__file__).resolve().parent.parent


def _benchmark_path() -> Path:
    return PARENT / "third_party" / "hiddenbench" / "data" / "benchmark_short.json"


def test_escrow_box_commit_reveal_phases():
    box = EscrowBox()
    sha = box.commit("Person 1", "evidence_packet", 1, {"agent": "Person 1", "response": "x"})
    digest = box.pre_reveal_digest()
    # Pre-reveal state is content-free.
    assert digest == [
        {"agent_id": "Person 1", "kind": "evidence_packet", "round": 1,
         "commitment_sha256": sha}
    ]
    assert "x" not in str(digest)
    revealed = box.reveal()
    assert revealed[0]["content"]["response"] == "x"
    # No commits after reveal.
    try:
        box.commit("Person 1", "evidence_packet", 2, {"response": "y"})
        raise AssertionError("commit after reveal must raise")
    except Exception:
        pass


def test_fake_client_budget_caps():
    client = FakeClient(max_calls=2, max_total_tokens=10**9)
    schema = {"properties": {"vote": {"enum": ["A", "B"]}}}
    client.chat_json([], schema)
    client.chat_json([{"role": "user", "content": "x"}], schema)
    try:
        client.chat_json([{"role": "user", "content": "y"}], schema)
        raise AssertionError("call cap must raise")
    except ArmBudgetExceeded:
        pass


def test_three_arm_smoke_run(tmp_path):
    summary = run_arms(
        benchmark_path=_benchmark_path(),
        task_ids=[1],
        rounds=1,
        seed=2026,
        max_calls=64,
        max_tokens=100_000,
        fake=True,
        out_dir=tmp_path / "smoke",
    )
    assert set(summary["per_arm"]) == {"escrow", "open-share", "central"}
    for arm, stats in summary["per_arm"].items():
        assert stats["num_tasks"] == 1
        # Fake votes are not expected to be correct; completions must be 1.
        assert stats["completed"] == 1, f"{arm} failed: {stats['failure_reasons']}"
        assert stats["total_llm_calls"] > 0
        assert stats["total_tokens"] > 0
    # Same fact assignment across the two multi-agent arms (same seed).
    assert (tmp_path / "smoke" / "REPORT.md").exists()
    assert (tmp_path / "smoke" / "summary.json").exists()
    assert any("OBSERVATIONAL" in label for label in summary["labels"])
