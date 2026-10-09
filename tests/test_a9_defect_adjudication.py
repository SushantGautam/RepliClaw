"""A9 (PREREG v1.2 §6b / M-1 fix) — arm-neutral defect-adjudication surface.

The round-2 science judge's M-1 (BLOCKING) defect: the P1 estimand (S5 vs S4)
scores M1 = correct root-cause diagnosis via the comparator's
``defect_class`` / ``target_artifact`` final-verdict fields, but BEFORE A9
those fields were hard-coded null on the strategy arms (S0/S3/S4) — no
comparator run could ever score M1, so P1 was an interface artifact. A9
registers ONE shared defect-adjudication block (defect_adjudication.py) used
byte-identically by BOTH the strategy finding prompt and the S5 RESOLVE
prompt, threads each arm's own diagnosis through Verdict -> final_verdict, and
adds a pre-bootstrap M1-interface canary that vetoes P1 when the estimand arm
(S4) is degenerate (no run with a non-null diagnosis).

Tests (A9.3, design-review C3–C9):

* (a) canary-degenerate unit test: all S4 runs null + S3/S0 non-null ->
  decision "m1_interface_degenerate", never SUPPORTED/FALSIFIED, canary
  reported per-arm;
* one non-null S4 run -> canary "ok", normal branch (S3-only ok must NOT
  mask an all-null S4: the veto is S4-specific);
* C4: the canary is a veto, NEVER a filter — recorded means unchanged;
* C5: _diagnosis_correct behavior pin (M1 definition unchanged);
* C9: the shared constant is byte-identical in the S5 RESOLVE prompt, every
  strategy finding prompt, and run_metadata's a9_defect_instruction_sha256;
* A9.2.6: run_metadata records the live LLMConfig fields (model / max_tokens /
  max_calls / timeout / temperature) + a9_defect_instruction_sha256;
* A9.2.1 new guard: the strategy finding prompt carries the
  EVIDENCE_FORBIDDEN_SUBSTRINGS oracle-leak guard;
* R-1: run_metadata.tree_sha is pinned to the ACTUAL ``git rev-parse HEAD``
  of the run tree at run start (mechanism tests, least-fragile form).

All offline: FakeLLMClient / hand-written schema-valid run dirs; no network.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from repliclaw.comparators import runner
from repliclaw.defect_adjudication import (
    DEFECT_ADJUDICATION_INSTRUCTION,
    DEFECT_TAXONOMY,
    defect_instruction_sha256,
)
from repliclaw.investigators import LLMClient, LLMInvestigator
from repliclaw.isolation import InvestigationContext
from repliclaw.models import Claim, InvestigatorConfig, InvestigatorRole
from repliclaw.p08 import score as sc
from test_a8_executor_parity import _a8_run

FAKE = "fake-v1"
OFFLINE = "deterministic"
CORRECT = ("retrieval_omission", "retrieval")  # matches oracle true_cause
WRONG = ("policy_conflict", "returns-policy")  # non-null but incorrect


def _runset(
    root: Path,
    *,
    s5: tuple | None = CORRECT,
    s4: tuple | None = CORRECT,
    s3: tuple | None = CORRECT,
    s0: tuple | None = CORRECT,
    s4_all_null: bool = False,
) -> None:
    """Write a schema-valid 3-run primary run-set (S5/S4 P1 pair, S3 RQ2, S0 RQ3).

    ``sX`` tuples are (defect_class, target_artifact); a ``None`` value models
    the pre-A9 structural null (both fields null). ``s4_all_null`` forces every
    S4 run null (the degenerate state) regardless of ``s4``.
    """
    for i in range(1, 4):
        d, t = s5 if s5 is not None else (None, None)
        _a8_run(root, "S5", f"run-{i:02d}", model=FAKE, offline_arm=False,
                defect=d, target=t)
        if s4_all_null or s4 is None:
            d, t = (None, None)
        else:
            d, t = s4
        _a8_run(root, "S4", f"run-{i:02d}", model=FAKE, offline_arm=False,
                defect=d, target=t)
        d, t = s3 if s3 is not None else (None, None)
        _a8_run(root, "S3", f"run-{i:02d}", model=FAKE, offline_arm=False,
                defect=d, target=t)
        d, t = s0 if s0 is not None else (None, None)
        _a8_run(root, "S0", f"run-{i:02d}", model=OFFLINE, offline_arm=True,
                defect=d, target=t)


# ---------------------------------------------------------------------------
# A9.2.4 / C3 — the M1 interface canary: S4-specific veto, per-arm report.
# ---------------------------------------------------------------------------
def test_a9_canary_degenerate_s4_vetoes_p1(tmp_path: Path) -> None:
    """(c) all S4 primary runs null (S3/S0 non-null) -> the P1 decision is
    "m1_interface_degenerate" (non-SUPPORTED, non-FALSIFIED) and the canary
    reports per-arm. This is the exact state the round-2 M-1 defect created:
    a non-null S3 must NOT mask a structurally-null S4 (the original
    any-of{S0,S3,S4} scoping would have let it pass)."""
    root = tmp_path / "degenerate"
    # S3 ok, S0 null (degenerate) — both REPORTED; only S4 vetoes.
    _runset(root, s5=CORRECT, s4=None, s3=CORRECT, s0=None, s4_all_null=True)
    res = sc.score_runs(root, "policy_rag_v1")
    p1 = res["p1_decision"]
    assert p1["decision"] == "m1_interface_degenerate"
    assert p1["decision"] not in (sc.P1_SUPPORTED, sc.P1_FALSIFIED, sc.P1_NOT_SUPPORTED)
    # Degraded shape: no ci95 / rule (same pattern as executor_parity_violation).
    assert "ci95" not in p1
    assert "rule" not in p1
    # Per-arm canary (C3): S4 degenerate; S3 ok, S0 degenerate — the report is
    # per-arm and the S3 "ok" does NOT mask the S4 veto.
    canary = p1["m1_canary"]
    assert canary["S4"] == "degenerate"
    assert canary["S3"] == "ok"
    assert canary["S0"] == "degenerate"
    # Executor parity is fine (S5/S4 both live) — the veto is the CANARY, not
    # the A8 guard.
    assert res["parity"]["ok"] is True


def test_a9_canary_s4_specific_not_any_of(tmp_path: Path) -> None:
    """C3 core: an all-null S4 with a non-null S3 MUST veto (any-of scoping is
    wrong), and one non-null S4 run must NOT (veto is all-null, not any-null)."""
    # (i) all-null S4, non-null S3 -> veto (the regression the brief names).
    root1 = tmp_path / "s4_null_s3_ok"
    _runset(root1, s5=CORRECT, s3=CORRECT, s4_all_null=True)
    res1 = sc.score_runs(root1, "policy_rag_v1")
    assert res1["p1_decision"]["decision"] == "m1_interface_degenerate"
    assert res1["p1_decision"]["m1_canary"]["S3"] == "ok"
    assert res1["p1_decision"]["m1_canary"]["S4"] == "degenerate"

    # (ii) one non-null S4 run (the other two null) -> canary "ok", normal
    # branch (veto fires only when EVERY S4 run is null).
    root2 = tmp_path / "s4_one_ok"
    for i in range(1, 4):
        _a8_run(root2, "S5", f"run-{i:02d}", model=FAKE, offline_arm=False,
                defect=CORRECT[0], target=CORRECT[1])
        if i == 1:
            _a8_run(root2, "S4", f"run-{i:02d}", model=FAKE, offline_arm=False,
                    defect=CORRECT[0], target=CORRECT[1])
        else:
            _a8_run(root2, "S4", f"run-{i:02d}", model=FAKE, offline_arm=False,
                    defect=None, target=None)
        _a8_run(root2, "S3", f"run-{i:02d}", model=FAKE, offline_arm=False,
                defect=CORRECT[0], target=CORRECT[1])
        _a8_run(root2, "S0", f"run-{i:02d}", model=OFFLINE, offline_arm=True,
                defect=None, target=None)
    res2 = sc.score_runs(root2, "policy_rag_v1")
    p1 = res2["p1_decision"]
    assert p1["decision"] != "m1_interface_degenerate"
    assert p1["m1_canary"]["S4"] == "ok"
    assert "ci95" in p1  # normal bootstrap branch
    assert p1["decision"] == sc.decision_branch(tuple(p1["ci95"]))


def test_a9_canary_veto_never_filter(tmp_path: Path) -> None:
    """C4 (MUST): the canary is a PRE-BOOTSTRAP VETO, never a filter — it must
    not drop null S4 runs from s4m or recompute means on survivors. Compare a
    run-set where S4 is non-null-but-wrong (M1 all 0.0, normal branch) with
    the identical run-set where S4's defect fields are null (same M1 values,
    degenerate veto): the recorded means MUST be byte-identical."""
    root_ok = tmp_path / "s4_wrong"
    _runset(root_ok, s5=CORRECT, s4=WRONG, s3=CORRECT, s0=CORRECT)
    res_ok = sc.score_runs(root_ok, "policy_rag_v1")
    assert res_ok["p1_decision"]["m1_canary"]["S4"] == "ok"
    assert "ci95" in res_ok["p1_decision"]

    root_deg = tmp_path / "s4_null"
    _runset(root_deg, s5=CORRECT, s4=None, s3=CORRECT, s0=CORRECT, s4_all_null=True)
    res_deg = sc.score_runs(root_deg, "policy_rag_v1")
    assert res_deg["p1_decision"]["decision"] == "m1_interface_degenerate"

    # Recorded means unchanged by the canary (veto, not filter):
    assert res_ok["p1_decision"]["s5_m1_mean"] == res_deg["p1_decision"]["s5_m1_mean"] == 1.0
    assert res_ok["p1_decision"]["s4_m1_mean"] == res_deg["p1_decision"]["s4_m1_mean"] == 0.0


# ---------------------------------------------------------------------------
# C5 — M1 definition unchanged (behavior pin).
# ---------------------------------------------------------------------------
def test_a9_m1_diagnosis_correct_unchanged(tmp_path: Path) -> None:
    """_diagnosis_correct stays exactly ``defect == oracle.true_cause and
    bool(target)`` for policy_rag_v1 — no exact-matching of target_artifact."""
    oracle = sc.load_oracle("policy_rag_v1")
    assert oracle["true_cause"] == "retrieval_omission"  # fixture invariant

    def m1(defect: Any, target: Any) -> bool:
        return sc._diagnosis_correct(
            {"case_id": "policy_rag_v1", "defect_class": defect, "target_artifact": target},
            oracle,
        )

    # Correct class + any non-null target -> True (target is bool()-checked,
    # NOT exact-matched — a different component name still scores).
    assert m1("retrieval_omission", "retrieval") is True
    assert m1("retrieval_omission", "returns-policy") is True
    # Wrong class -> False, regardless of target.
    assert m1("policy_conflict", "retrieval") is False
    assert m1(None, "retrieval") is False
    assert m1("none", None) is False
    # Correct class but null target -> False (both fields required).
    assert m1("retrieval_omission", None) is False
    # A target that merely CONTAINS the true cause is not special-cased.
    assert m1("retrieval_omission_extra", "retrieval") is False


# ---------------------------------------------------------------------------
# C9 / A9.2.1 — byte-identity of the shared block across both prompt hosts.
# ---------------------------------------------------------------------------
def test_a9_shared_block_byte_identical_s5_and_strategy(tmp_path: Path) -> None:
    """The registered constant appears verbatim in BOTH the S5 RESOLVE prompt
    and the strategy finding prompt, in its own clearly marked section, with a
    stable sha256 (C9 / A9.3d)."""
    from test_prompt_evidence import _make_orch

    orch, clients = _make_orch(tmp_path / "run")
    result = orch.run()
    assert result.status == "completed"
    from repliclaw.eess_live.orchestrator import VERDICT_MARKER

    s5_resolve = [p for p in clients["alpha"].prompts if VERDICT_MARKER in p]
    assert s5_resolve, "no RESOLVE verdict prompt captured"
    for p in s5_resolve:
        assert "# DEFECT DIAGNOSIS (required)\n" + DEFECT_ADJUDICATION_INSTRUCTION in p
        # The block is appended AFTER the evidence-block footer (evidence span
        # unchanged), and the oracle-leak guard still sees the full prompt.
        footer = "evidence_cited (list of evidence_ids you relied on)."
        assert p.index(footer) < p.index("# DEFECT DIAGNOSIS (required)")

    # Strategy finding prompt: the same constant, same marker, AFTER the
    # numeric ROLE METHOD / OUTPUT sections (C6).
    claim = Claim(
        claim_id="claim_a9",
        statement="The baseline policy-RAG system fails to cite the controlling provision.",
        domain="policy_rag",
        data={
            "test_prompt": "what is the review window?",
            "policy_docs": [{"title": "v2: within 30 days", "body": "within 30 days"}],
            "base_retrieval": ["v1: within 14 days"],
        },
    )
    captured: list[str] = []

    class _Stub(LLMClient):
        def chat_json(self, prompt: str) -> dict:
            captured.append(prompt)
            return {
                "conclusion": "uncertain", "confidence": 0.5,
                "defect_class": "retrieval_omission", "target_artifact": "retrieval",
            }

    inv = LLMInvestigator(
        InvestigatorConfig(agent_id="inv-1", role=InvestigatorRole.ANALYST), _Stub()
    )
    ctx = InvestigationContext(
        claim=claim,
        investigator=InvestigatorConfig(agent_id="inv-1", role=InvestigatorRole.ANALYST),
        task_instructions="Analyze the claim.",
    )
    finding = inv.run(ctx)
    assert finding["defect_class"] == "retrieval_omission"
    sp = captured[0]
    marker = "# DEFECT DIAGNOSIS (required)\n" + DEFECT_ADJUDICATION_INSTRUCTION
    assert marker in sp
    # C6: the defect clause is its own section AFTER the numeric method.
    assert sp.index("# ROLE METHOD") < sp.index(marker)
    # Same byte-identity: the S5 prompt and the strategy prompt share the
    # exact block, and the recorded sha is stable.
    s5_block = s5_resolve[0][s5_resolve[0].index(marker):]
    assert DEFECT_ADJUDICATION_INSTRUCTION in s5_block
    sha = defect_instruction_sha256()
    assert len(sha) == 64 and all(c in "0123456789abcdef" for c in sha)
    # The taxonomy menu is the registered vocabulary (C1).
    assert DEFECT_TAXONOMY == {
        "retrieval_omission", "policy_conflict", "judge_stale",
        "generation_error", "data_error", "none",
    }
    for label in DEFECT_TAXONOMY:
        assert label in DEFECT_ADJUDICATION_INSTRUCTION


def test_a9_strategy_prompt_oracle_leak_guard(tmp_path: Path) -> None:
    """A9.2.1 new guard: the strategy finding prompt is checked against
    EVIDENCE_FORBIDDEN_SUBSTRINGS — an oracle leak into claim data must raise,
    never reach the model."""
    claim = Claim(
        claim_id="claim_leak",
        statement="leak test",
        domain="policy_rag",
        data={"note": "true_cause is in here"},
    )
    cfg = InvestigatorConfig(agent_id="inv-2", role=InvestigatorRole.ANALYST)
    inv = LLMInvestigator(cfg, _StubClient())
    ctx = InvestigationContext(
        claim=claim, investigator=cfg, task_instructions="t"
    )
    with pytest.raises(RuntimeError, match="forbidden oracle"):
        inv.run(ctx)


class _StubClient(LLMClient):
    def chat_json(self, prompt: str) -> dict:
        raise AssertionError("client must not be reached — guard raises first")


# ---------------------------------------------------------------------------
# A9.2.6 / N-1 — run_metadata records LLMConfig fields + instruction sha256.
# ---------------------------------------------------------------------------
def _run_cli(arm: str, case: str, *extra: str, monkeypatch: pytest.MonkeyPatch, out: Path) -> int:
    monkeypatch.delenv("REPLICLAW_LLM_ALLOW_LIVE", raising=False)
    return runner.main(["--arm", arm, "--case", case, "--out", str(out), *extra])


def test_a9_run_metadata_records_llmconfig_and_instruction_sha(tmp_path: Path, monkeypatch) -> None:
    """A live strategy arm (S4) run_metadata records model/max_tokens/
    max_calls/timeout/temperature + a9_defect_instruction_sha256 (N-1)."""
    out = tmp_path / "s4"
    code = _run_cli("S4", "policy_rag", "--client-factory", "fake",
                    monkeypatch=monkeypatch, out=out)
    assert code == 0
    meta = json.loads((out / "run-01" / "run_metadata.json").read_text())
    assert meta["offline_arm"] is False
    assert meta["model"] == "fake-v1"
    # Live LLMConfig identity (A9.2.6): the fake client's declared config.
    for key in ("max_tokens", "max_calls", "timeout", "temperature"):
        assert key in meta, f"run_metadata missing {key!r} (A9.2.6)"
        assert meta[key] is not None, f"{key} must be non-null for a live arm"
    assert meta["a9_defect_instruction_sha256"] == defect_instruction_sha256()
    # The final verdict carries the arm's own diagnosis (A9.2.2 / A9.3a).
    fv = json.loads((out / "run-01" / "final_verdict.json").read_text())
    assert fv["defect_class"] == "retrieval_omission"
    assert fv["target_artifact"] == "retrieval"


def test_a9_run_metadata_offline_arm_records_sha_and_nulls(tmp_path: Path, monkeypatch) -> None:
    """An offline arm (S0 on the secondary no-LLM case) records the
    instruction sha256 but null config knobs (it made no LLM call)."""
    out = tmp_path / "s0"
    code = _run_cli("S0", "tox21_ar_agonist", monkeypatch=monkeypatch, out=out)
    assert code == 0
    meta = json.loads((out / "run-01" / "run_metadata.json").read_text())
    assert meta["offline_arm"] is True
    assert meta["model"] == "deterministic"
    for key in ("max_tokens", "max_calls", "timeout", "temperature"):
        assert meta[key] is None, f"{key} must be null for an offline arm"
    assert meta["a9_defect_instruction_sha256"] == defect_instruction_sha256()


# ---------------------------------------------------------------------------
# R-1 — run_metadata.tree_sha is the ACTUAL ``git rev-parse HEAD`` of the run
# tree at run start (round-2 finding: the pin must be the actual HEAD, so the
# signed run tree matches what was executed). Verified two ways:
#   (1) real-git: the recorded value equals ``git rev-parse HEAD`` of the repo
#       the runner is actually executing in (offline AND live arms — the single
#       run_metadata writer serves both);
#   (2) mechanism (least-fragile for CI): via the monkeypatched ``_tree_sha``
#       git seam, the recorded value is exactly whatever the run-tree git call
#       returns at write time, and the call is made on the run tree (cwd).
# ---------------------------------------------------------------------------
def test_r1_tree_sha_records_actual_head_real_git(tmp_path: Path, monkeypatch) -> None:
    """run_metadata.tree_sha equals the ACTUAL HEAD of the repo the runner
    executes in — for the offline path (S0) and the live path (S4), which
    share the single run_metadata writer."""
    # The run tree is this worktree (the runner resolves it from cwd).
    run_tree = Path.cwd()
    actual_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=run_tree,
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    assert len(actual_head) == 40, f"unexpected HEAD: {actual_head!r}"

    # Offline arm (deterministic) — the pre-A9 secondary path.
    code = _run_cli("S0", "tox21_ar_agonist", monkeypatch=monkeypatch, out=tmp_path / "out")
    assert code == 0
    meta = json.loads((tmp_path / "out" / "run-01" / "run_metadata.json").read_text())
    assert meta["tree_sha"] == actual_head, (
        f"offline arm tree_sha {meta['tree_sha']!r} != actual run-tree HEAD "
        f"{actual_head!r} (R-1: the pin must be the actual HEAD)"
    )
    # Live strategy arm (fake client) — same writer, must match too.
    code2 = _run_cli("S4", "policy_rag", "--client-factory", "fake",
                     monkeypatch=monkeypatch, out=tmp_path / "out2")
    assert code2 == 0
    meta2 = json.loads((tmp_path / "out2" / "run-01" / "run_metadata.json").read_text())
    assert meta2["tree_sha"] == actual_head, (
        f"live arm tree_sha {meta2['tree_sha']!r} != actual run-tree HEAD "
        f"{actual_head!r} (R-1: the pin must be the actual HEAD)"
    )


def test_r1_tree_sha_is_run_tree_head_at_write_time(tmp_path: Path, monkeypatch) -> None:
    """Mechanism (least-fragile) form: whatever the run tree's ``git rev-parse
    HEAD`` returns at write time is what run_metadata records. We patch the
    runner's ``_tree_sha`` (the single git seam) to (i) capture the root it is
    called with and (ii) return a sentinel — the recorded tree_sha must equal
    the sentinel, AND every call must have been made on the run tree (cwd)."""
    calls: list[Path] = []
    sentinel = "r" * 40

    def fake_tree_sha(root: Path) -> str:
        calls.append(Path(root))
        return sentinel

    monkeypatch.setattr(runner, "_tree_sha", fake_tree_sha)
    code = _run_cli("S0", "tox21_ar_agonist", monkeypatch=monkeypatch, out=tmp_path / "out")
    assert code == 0
    meta = json.loads((tmp_path / "out" / "run-01" / "run_metadata.json").read_text())
    assert meta["tree_sha"] == sentinel, (
        "recorded tree_sha must be exactly what the run-tree git call returned "
        "at write time (R-1 mechanism)"
    )
    assert calls, "runner never resolved the run-tree HEAD"
    assert all(c == Path.cwd() for c in calls), (
        f"tree_sha must be resolved on the run tree (cwd); got {calls}"
    )
