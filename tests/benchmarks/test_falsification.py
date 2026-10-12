"""Offline tests for the 4-arm matched falsification comparison (mock LLM, no network).

Covers:
  (a) all four arms run and produce per-claim conclusions;
  (b) the matched caps are correct and actually enforced (turns + tokens);
  (c) the scorer correctly scores a known outcome against ground truth;
  (d) the escrowed arm's per-investigator partition isolation holds and the
      sealed commitments verify at reveal;
  (e) receipts are captured for every arm.

Plus: the live path refuses to run without an API key, and the trap-claim set
is derived correctly from the private trap taxonomy.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pytest

from repliclaw.benchmarks.adversarial_audit import ground_truth as gt
from repliclaw.benchmarks.falsification import (
    ARM_NAMES,
    DEFAULT_CAPS,
    ArmResult,
    MockLLMClient,
    PooledInvestigator,
    all_artifacts,
    claim_ids,
    run_comparison,
    score_arm,
    trap_claim_ids,
)
from repliclaw.benchmarks.falsification.arms import run_escrowed
from repliclaw.escrow import verify_ledger
from repliclaw.investigators import BudgetExceeded, LLMClient, LLMConfig


# ---------------------------------------------------------------------------
# scripted double for the pooled budget-enforcement tests
# ---------------------------------------------------------------------------
class _AlwaysToolCallClient(LLMClient):
    """Returns a tool_call every turn (never commits) so the loop runs to a bound."""

    def __init__(self, per_call=(40, 12), model="mock") -> None:
        super().__init__(
            cfg=LLMConfig(base_url="http://fake.invalid/v1", api_key="fake", model=model, max_calls=10_000)
        )
        self._per_call = (int(per_call[0]), int(per_call[1]))

    def chat_messages(self, messages: list, max_tokens: Optional[int] = None) -> str:
        if self._calls >= self.cfg.max_calls:
            raise BudgetExceeded("budget")
        self._calls += 1
        p, c = self._per_call
        self.usage.prompt_tokens += p
        self.usage.completion_tokens += c
        self.usage.total_tokens = self.usage.prompt_tokens + self.usage.completion_tokens
        self.usage.llm_calls += 1
        self.last_model = self.cfg.model
        return json.dumps({"action": "tool_call", "tool": "list_artifacts", "args": {}})


# Distinctive, source-unique content markers (no collision with claim ids C1..C7).
_SOURCE_MARKERS = {
    "source_a": ["12,450 ng*h/mL", "QC-VAL-221", "CAL-118"],
    "source_b": ["ST-HPLC-7", "99.9% uptime", "definitive confirmation"],
    "source_c": ["8.2%", "solvent-recovery line", "200 L"],
    "source_d": ["n=6, p<0.05", "Pearson r=0.85", "systematically overstates"],
}


# ---------------------------------------------------------------------------
# (b) matched caps: invariants + enforcement
# ---------------------------------------------------------------------------
def test_matched_caps_invariants() -> None:
    caps = DEFAULT_CAPS
    # The team split must exactly reconstruct the arm-level totals.
    assert caps.tokens_per_investigator * caps.n_team == caps.total_tokens
    assert caps.calls_per_investigator * caps.n_team == caps.total_calls
    # open_sharing's two-phase split equals the per-investigator budget.
    assert caps.open_sharing_phase_calls * 2 == caps.calls_per_investigator
    assert caps.open_sharing_phase_tokens * 2 == caps.tokens_per_investigator
    # A single-agent arm uses the full arm-level envelope.
    single = caps.single_agent_caps()
    assert single["token_budget"] == caps.total_tokens
    assert single["max_turns"] == caps.total_calls
    team = caps.team_investigator_caps()
    assert team["token_budget"] == caps.tokens_per_investigator
    assert team["max_turns"] == caps.calls_per_investigator


def test_pooled_max_turns_enforced() -> None:
    client = _AlwaysToolCallClient()
    caps = {"max_turns": 3, "token_budget": 100_000, "max_tokens_per_call": 1024, "wall_deadline_s": 60.0}
    inv = PooledInvestigator(
        client, "a", "C1", "single_investigator", all_artifacts(), "sys", caps
    )
    receipt = inv.run()
    assert receipt.num_llm_calls == 3
    assert "max_turns" in receipt.bounds_hit
    assert receipt.verdict is None  # never got to commit


def test_pooled_token_budget_enforced() -> None:
    client = _AlwaysToolCallClient(per_call=(1000, 100))  # 1100 tokens/call
    caps = {"max_turns": 10, "token_budget": 2500, "max_tokens_per_call": 1024, "wall_deadline_s": 60.0}
    inv = PooledInvestigator(
        client, "a", "C1", "single_investigator", all_artifacts(), "sys", caps
    )
    receipt = inv.run()
    assert "token_budget" in receipt.bounds_hit
    assert receipt.verdict is None
    assert receipt.total_tokens > 2500  # stopped right after exceeding


def test_dryrun_spend_within_matched_caps(tmp_path: Path) -> None:
    results = run_comparison(["C1"], list(ARM_NAMES), tmp_path, dry_run=True)
    for arm in ARM_NAMES:
        for r in results["per_arm_per_claim"][arm]:
            assert r["total_llm_calls"] <= DEFAULT_CAPS.total_calls, (arm, r["total_llm_calls"])
            assert r["total_tokens"] <= DEFAULT_CAPS.total_tokens, (arm, r["total_tokens"])


# ---------------------------------------------------------------------------
# (a) all four arms run and produce per-claim conclusions
# ---------------------------------------------------------------------------
def test_all_arms_run_and_produce_conclusions(tmp_path: Path) -> None:
    claims = ["C1", "C2"]
    results = run_comparison(claims, list(ARM_NAMES), tmp_path, dry_run=True)
    assert results["dry_run"] is True
    assert results["harness_check_only"] is True
    for arm in ARM_NAMES:
        per_claim = results["per_arm_per_claim"][arm]
        assert len(per_claim) == len(claims)
        for r in per_claim:
            assert r["team_verdict"] in ("TRUE", "FALSE", "ABSTAIN"), (arm, r)
            assert r["status"] == "completed"
    # Artifacts persisted.
    assert (tmp_path / "results.json").exists()
    assert (tmp_path / "summary.md").exists()
    # The summary is clearly labeled a harness check.
    assert "HARNESS CHECK" in (tmp_path / "summary.md").read_text()


# ---------------------------------------------------------------------------
# (c) scorer correctness against ground truth
# ---------------------------------------------------------------------------
def test_scorer_scores_known_outcome() -> None:
    answers = gt.answers()
    # A perfect arm: every verdict equals ground truth.
    perfect = [
        ArmResult(arm="t", claim_id=c, team_verdict=answers[c], individual_verdicts={"a": answers[c]})
        for c in claim_ids()
    ]
    s = score_arm("t", perfect)
    assert s["accuracy"] == 1.0
    assert s["correct"] == s["total"] == len(claim_ids())
    assert s["abstention_rate"] == 0.0

    # A known-wrong arm on C1 (GT is FALSE, predict TRUE).
    wrong = [ArmResult(arm="t", claim_id="C1", team_verdict="TRUE", individual_verdicts={"a": "TRUE"})]
    s2 = score_arm("t", wrong)
    assert s2["accuracy"] == 0.0
    assert s2["per_claim"]["C1"]["expected"] == "FALSE"
    assert s2["per_claim"]["C1"]["correct"] is False

    # Abstention is counted and not scored as correct.
    abstain = [ArmResult(arm="t", claim_id="C1", team_verdict="ABSTAIN", individual_verdicts={"a": "ABSTAIN"})]
    s3 = score_arm("t", abstain)
    assert s3["abstained"] == 1
    assert s3["abstention_rate"] == 1.0
    assert s3["correct"] == 0


def test_trap_claim_set() -> None:
    traps = trap_claim_ids()
    # The planted traps map to exactly these claims (from the private taxonomy).
    assert traps == {"C1", "C2", "C3", "C5", "C6"}
    # C4 and C7 have no trap artifacts.
    assert "C4" not in traps and "C7" not in traps


def test_scorer_robustness_and_false_consensus() -> None:
    # Team arm: team verdict WRONG, but one individual was RIGHT (false consensus).
    # C1 GT is FALSE. Team says TRUE (wrong); individual 'a' said FALSE (right).
    results = [
        ArmResult(
            arm="team", claim_id="C1", team_verdict="TRUE",
            individual_verdicts={"a": "FALSE", "b": "TRUE", "c": "TRUE", "d": "TRUE"},
        )
    ]
    s = score_arm("team", results)
    assert s["accuracy"] == 0.0
    assert s["team_wrong"] == 1
    assert s["team_wrong_individual_right"] == 1
    assert s["false_consensus_rate"] == 1.0
    # Individual accuracy: 1 of 4 votes correct.
    assert s["individual_correct"] == 1
    assert s["individual_total"] == 4


# ---------------------------------------------------------------------------
# (d) escrowed arm: partition isolation + commitment verification at reveal
# ---------------------------------------------------------------------------
def test_escrowed_isolation_and_reveal_verification(tmp_path: Path) -> None:
    def factory(agent_id: str) -> MockLLMClient:
        return MockLLMClient(agent_seed=agent_id)

    result = run_escrowed("C1", factory, DEFAULT_CAPS, tmp_path)

    # All four source investigators committed and their commitments verified.
    assert len(result.receipts) == 4
    for agent_id, r in result.receipts.items():
        assert r["status"] == "committed"
        assert r["reveal_status"] == "verified"
        assert r["commitment_sha256"] is not None
        assert r["packet"] is not None

    # Partition isolation: each transcript carries only its own source's content.
    for agent_id, r in result.receipts.items():
        own = r["source_id"]
        blob = json.dumps(r["transcript"])
        for marker in _SOURCE_MARKERS[own]:
            assert marker in blob, f"{agent_id} missing own marker {marker!r}"
        for other, markers in _SOURCE_MARKERS.items():
            if other == own:
                continue
            for marker in markers:
                assert marker not in blob, f"{agent_id} leaked foreign marker {marker!r} from {other}"

    # The escrow ledger verifies end to end (hash chain + commitments + reveal).
    ledger_root = tmp_path / "C1" / "escrowed_independent" / "ledger"
    assert verify_ledger(ledger_root) == []


# ---------------------------------------------------------------------------
# (e) receipts captured for every arm
# ---------------------------------------------------------------------------
def test_receipts_captured_for_every_arm(tmp_path: Path) -> None:
    claims = ["C1"]
    run_comparison(claims, list(ARM_NAMES), tmp_path, dry_run=True)
    expected_counts = {
        "escrowed_independent": 4,  # one per source
        "open_sharing": 8,  # 4 investigators x 2 phases
        "central_adaptive": 1,
        "single_investigator": 1,
    }
    for arm, count in expected_counts.items():
        path = tmp_path / claims[0] / arm / "receipts.jsonl"
        assert path.exists(), f"missing receipts for {arm}"
        lines = [ln for ln in path.read_text().splitlines() if ln.strip()]
        assert len(lines) == count, (arm, len(lines))
        for ln in lines:
            obj = json.loads(ln)
            # Every receipt is auditable: transcript + usage + model + status.
            assert obj["transcript"], f"{arm} receipt missing transcript"
            assert "total_tokens" in obj and "num_llm_calls" in obj
            assert obj["model_requested"]
            assert obj["status"] in ("committed", "bound", "failed", "invalid_usage")


# ---------------------------------------------------------------------------
# live path refuses without an API key
# ---------------------------------------------------------------------------
def test_live_refused_without_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REPLICLAW_LLM_API_KEY", raising=False)
    monkeypatch.delenv("CUSTOM_SIMULACHAT_KEY", raising=False)
    from repliclaw.benchmarks.falsification.runner import make_client_factory

    with pytest.raises(RuntimeError, match="No LLM API key"):
        make_client_factory(dry_run=False, llm_config=LLMConfig(api_key=""))


def test_cli_refuses_live_without_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REPLICLAW_LLM_API_KEY", raising=False)
    monkeypatch.delenv("CUSTOM_SIMULACHAT_KEY", raising=False)
    from repliclaw.benchmarks.falsification.__main__ import main

    rc = main(["--claims", "C1", "--arms", "single_investigator", "--out", str(tmp_path)])
    assert rc == 1
    assert not (tmp_path / "results.json").exists()


def test_cli_dry_run_succeeds_offline(tmp_path: Path) -> None:
    from repliclaw.benchmarks.falsification.__main__ import main

    rc = main(["--claims", "C1", "--arms", "single_investigator", "--out", str(tmp_path), "--dry-run"])
    assert rc == 0
    assert (tmp_path / "results.json").exists()
    assert (tmp_path / "summary.md").exists()
