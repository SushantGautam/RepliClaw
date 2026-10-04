"""A4 (PREREG-2026-10-v1.2-AMENDMENT): the post-evidence RESOLVE verdict
prompt must carry the machine-verified public evidence view — and provably
NOT the sealed oracle.

All tests here are OFFLINE (FakeLLMClient only; no network, no live key).
Named-test -> A4 gate mapping:

* A4 gate 1 (separate flagged PR): property of this branch — this file is the
  PR's test fixture; the PR touches only the verdict-prompt construction.
* **A4 gate 2** (deterministic FakeLLMClient parity re-run of all 3 live
  arms) -> :func:`test_a4_gate2_three_arm_determinism_and_golden_stability`.
  The "before" side is the pre-amendment baseline captured from run-branch
  ``dc0e78f`` and committed under ``tests/fixtures/a4_prebranch_dc0e78f/``;
  the structural comparison is via the schema+values assertion (every
  pre-existing ``final_verdict.json`` field keeps its value; the only deltas
  are the verdict-prompt payload and the new ``evidence_cited`` field).
* **A4 gate 3** (7-test live-arm contract suite green) -> ``tests/test_eess_
  live.py`` (asserted green by the GATE command, not by this file).
* **A4 gate 4** (contradictory-evidence regression, Hotspots Critical 2) ->
  :func:`test_a4_gate4_contradictory_evidence_regression`.
* Oracle-free requirement (A4 negative path; cf. A6 test 2) ->
  :func:`test_verdict_prompt_injects_verified_evidence_and_no_oracle_content`
  and :func:`test_evidence_block_guard_fails_loud_on_oracle_substring`.
* ``evidence_cited`` round-trip ->
  :func:`test_evidence_cited_round_trips_into_verdicts`.

Evidence-record field mapping (records are the escrow ledger's
``EvidenceObservation.model_dump(mode="json")`` — the SAME verified public
records the deterministic selection policies consume via
``evidence_view(self.escrow.evidence())``):

* ``evidence_id``    <- ``observation_id``  (content-derived ``obs_`` id)
* ``run_id``         <- ``run_id``          (counterfactual-execution run id)
* ``arm``            <- ``data.intervention_id``
* ``outcome``        <- ``data.severity``   (per-arm outcome label)
* ``snapshot_sha``   <- ``provenance.config_sha256``

The arm code NEVER reads ``experiments/policy_rag/oracle/oracle.json``. Only
THIS test reads it — to build the value-level forbidden-substring canary list
on top of the oracle's field-name list, exactly the negative-path
construction the amendment requires.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

from repliclaw.comparators.arms import ArmSpec
from repliclaw.comparators.budget import BudgetEnvelope, BudgetLedger
from repliclaw.defect_adjudication import DEFECT_TAXONOMY
from repliclaw.eess_live import (
    EESSLiveA1Arm,
    EESSLiveA3Arm,
    EESSLiveS5Arm,
    EscrowedEscrow,
    FakeLLMClient,
)
from repliclaw.eess_live.fake import VERDICT_MARKER
from repliclaw.eess_live.orchestrator import (
    AGENT_IDS,
    CASE_ID,
    EVIDENCE_FORBIDDEN_SUBSTRINGS,
    LiveEESSOrchestrator,
    _evidence_block,
)
from repliclaw.escrow import EvidenceObservation
from repliclaw.models import Claim
from repliclaw.needmarket.policy import LocalEigPolicy
from repliclaw.slice.derive import ARM_BY_HYP

SEED = 20261010
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "a4_prebranch_dc0e78f"
ORACLE_PATH = Path(__file__).resolve().parents[1] / "experiments" / "policy_rag" / "oracle" / "oracle.json"

BASELINE_ARM = "I0_baseline"
# Hypothesis committed by each agent (the orchestrator's HYP_BY_AGENT).
AGENT_HYP = {"alpha": "H_R", "beta": "H_P", "gamma": "H_J"}
# The canonical (FakeLLMClient) sealed commitment, identical for all agents.
COMMITMENT = "The corrected-retrieval arm changes the target output."
# Stable anchors delimiting the evidence block inside a verdict prompt.
_BLOCK_HEADER = (
    "Machine-verified public evidence for this hypothesis "
    "(verified records only; sealed oracle content is NOT included):\n"
)
_BLOCK_FOOTER = "Respond with JSON containing conclusion"
# Wall-clock fields excluded from determinism/golden comparisons.
WALL_KEYS = ("wall_s", "ts")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _claim() -> Claim:
    return Claim(
        claim_id="claim_live_test",
        statement="The baseline policy-RAG system fails to cite the controlling provision.",
        domain="policy_rag",
    )


def _envelope() -> BudgetEnvelope:
    # Identical envelope across arms and reruns (matched-cap parity, A6).
    return BudgetEnvelope(max_tokens=60_000, max_wall_s=900.0, max_agents=3)


class CapturingFakeLLMClient(FakeLLMClient):
    """FakeLLMClient that RECORDS every prompt handed to ``chat``.

    ``chat_json`` delegates to ``chat`` (with one retry), so capturing at the
    ``chat`` level sees exactly what the orchestrator sent to the model.
    """

    def __init__(self, *args: Any, **kw: Any) -> None:
        super().__init__(*args, **kw)
        self.prompts: List[str] = []

    def chat(self, prompt: str, system: str = "s", max_tokens: int | None = None) -> str:
        self.prompts.append(prompt)
        return super().chat(prompt, system=system, max_tokens=max_tokens)


def _fresh_clients() -> Dict[str, CapturingFakeLLMClient]:
    return {agent: CapturingFakeLLMClient() for agent in AGENT_IDS}


def _make_orch(
    tmp: Path,
    on_event: Any = None,
    clients: Dict[str, CapturingFakeLLMClient] | None = None,
) -> Tuple[LiveEESSOrchestrator, Dict[str, CapturingFakeLLMClient]]:
    """A canonical S5-config orchestrator (EscrowedEscrow + LocalEigPolicy)
    at the contract seed/envelope — the cleanest real seam for RESOLVE-time
    evidence: the real ledger, the real phase gate."""
    esc = EscrowedEscrow(tmp / "escrow")
    cs = clients if clients is not None else _fresh_clients()
    orch = LiveEESSOrchestrator(
        claim=_claim(),
        out_root=tmp / "runs",
        escrow=esc,
        policy_factory=lambda _a: LocalEigPolicy({}),
        client_factory=lambda a: cs[a],
        envelope=_envelope(),
        harness_seed=SEED,
        on_event=on_event,
    )
    return orch, cs


def _verdict_prompts(clients: Dict[str, CapturingFakeLLMClient]) -> Dict[str, str]:
    """agent_id -> its RESOLVE verdict prompt (marker-keyed, like the fake)."""
    out: Dict[str, str] = {}
    for agent in AGENT_IDS:
        matches = [p for p in clients[agent].prompts if VERDICT_MARKER in p]
        assert len(matches) == 1, f"agent {agent}: expected exactly 1 verdict prompt, got {len(matches)}"
        out[agent] = matches[0]
    return out


def _block_lines(prompt: str) -> List[str]:
    """The verdict prompt's evidence block, as its list of record lines."""
    start = prompt.index(_BLOCK_HEADER) + len(_BLOCK_HEADER)
    end = prompt.index(_BLOCK_FOOTER, start)
    block = prompt[start:end].rstrip("\n")
    lines = [ln for ln in block.splitlines() if ln.strip()]
    assert lines and all(ln.startswith("- evidence_id=") for ln in lines), f"malformed evidence block: {block!r}"
    return lines


def _block_ids(prompt: str) -> List[str]:
    return [ln.split()[1].split("=", 1)[1] for ln in _block_lines(prompt)]


def _line_id(line: str) -> str:
    return line.split()[1].split("=", 1)[1]


def _relevant_obs_ids(evidence: List[Dict[str, Any]], hypothesis_id: str) -> List[str]:
    """Mirror of the orchestrator's relevance filter (documented mapping):
    a record is in scope for the hypothesis when its arm maps to it OR it is
    the shared baseline arm (the counterfactual comparator every hypothesis
    references)."""
    out = []
    for rec in evidence:
        data = rec.get("data") or {}
        if data.get("hypothesis") == hypothesis_id or data.get("intervention_id") == BASELINE_ARM:
            out.append(str(rec["observation_id"]))
    return sorted(out)


def _trace_shape(traces: List[Dict[str, Any]]) -> List[Tuple]:
    """Wall-clock-free trace shape: (seq, type, agent, canonical payload)."""
    return [
        (t["seq"], t["type"], t["agent_id"], json.dumps(t["payload"], sort_keys=True, default=str))
        for t in traces
    ]


def _strip_wall(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _strip_wall(v) for k, v in obj.items() if k not in WALL_KEYS}
    if isinstance(obj, list):
        return [_strip_wall(v) for v in obj]
    return obj


def _load_json(p: Path) -> Any:
    return json.loads(p.read_text())


# The oracle's SEALED field names (the negative path the amendment names).
# NOTE: ``case`` / ``hypothesis`` / ``schema`` are deliberately EXCLUDED — they
# are public references (the case id, the hypothesis id, the schema version)
# and the word ``hypothesis`` is used verbatim in the A4 template, so their
# presence in a prompt is NOT a leak. Only the sealed content below is.
SEALED_ORACLE_FIELDS = {
    "true_cause",
    "reference_truth",
    "seeded_fault",
    "fault_marker",
    "expected_arm_outcomes",
    "supports_hypothesis",
}


def _public_identifiers() -> set:
    """Public identifiers that legitimately appear in a verdict prompt.

    The evidence block (and template) intentionally carries the case id, the
    arm keys, the per-arm outcome labels, and the hypothesis ids — the SAME
    vocabulary the oracle uses for its per-arm rows. Those are PUBLIC
    identifiers, not sealed content, so an oracle VALUE that is exactly one
    of them (e.g. ``I0_baseline``) is not a leak canary.
    """
    pub = {CASE_ID, BASELINE_ARM, *AGENT_HYP.values(), *ARM_BY_HYP.values()}
    # Per-arm outcome labels of the verified records in a canonical S5 run
    # (the critical/pass vocabulary of the case's severities).
    pub |= {"critical", "pass", "no_defect"}
    # A9 (M-1 fix): the registered defect taxonomy is PUBLIC adjudication
    # vocabulary — the shared defect-instruction block (defect_adjudication.py)
    # lists these labels as a menu for BOTH arms, so their presence in a
    # prompt is not a sealed-oracle leak. (The oracle's true_cause value
    # happens to equal one of the six labels; the menu is a registered
    # interface, not the answer — the oracle file itself is still never read
    # by arm code.)
    pub |= DEFECT_TAXONOMY
    return pub


def _forbidden_substrings() -> List[str]:
    """Sealed-oracle field names + sealed value canaries, read in the TEST.

    Read in the TEST ONLY — arm code never opens the oracle file. The list is
    the union of:
    * the hardcoded ``EVIDENCE_FORBIDDEN_SUBSTRINGS`` (the sealed field names
      + the ``repliclaw.sealed_oracle`` schema marker), and
    * every oracle.json sealed field name that is present, and
    * every oracle string VALUE that is (a) at least 8 chars long AND (b) not
      itself a public identifier.

    Public words/ids (``hypothesis``, ``case``, ``schema`` field names; and
    values like ``H_R`` / ``I0_baseline`` / ``critical``) are NOT canaries:
    they legitimately appear in the template and evidence block.
    """
    subs: List[str] = list(EVIDENCE_FORBIDDEN_SUBSTRINGS)
    oracle = _load_json(ORACLE_PATH)
    assert "true_cause" in oracle, "oracle schema changed: rebuild the forbidden list"

    def add_values(o: Any) -> None:
        if isinstance(o, str):
            subs.append(o)
        elif isinstance(o, dict):
            for v in o.values():
                add_values(v)
        elif isinstance(o, list):
            for v in o:
                add_values(v)

    for key in oracle:
        if key in SEALED_ORACLE_FIELDS:  # sealed field name (not 'case'/'hypothesis')
            subs.append(key)
    add_values(oracle)  # every oracle string value -> value canary candidate

    pub = _public_identifiers()
    seen = set()
    out: List[str] = []
    for s in subs:
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return [
        s
        for s in out
        if (len(s) >= 8 or s in SEALED_ORACLE_FIELDS or s in EVIDENCE_FORBIDDEN_SUBSTRINGS)
        and s not in pub
    ]


# ---------------------------------------------------------------------------
# A4 negative path / A6 test 2: the verdict prompt carries the agent's
# hypothesis, its sealed commitment, >=1 machine-verified evidence record for
# the hypothesis — and NO oracle field, value canary, or path.
# ---------------------------------------------------------------------------
def test_verdict_prompt_injects_verified_evidence_and_no_oracle_content(tmp_path: Path):
    orch, clients = _make_orch(tmp_path / "run")
    result = orch.run()
    assert result.status == "completed"

    prompts = _verdict_prompts(clients)
    evidence = orch.escrow.evidence()
    forbidden = _forbidden_substrings()
    # A9 re-pin (M-1 fix): the oracle's true_cause VALUE ("retrieval_omission")
    # is no longer a value canary — it is one of the six labels of the
    # REGISTERED public defect taxonomy (defect_adjudication.DEFECT_TAXONOMY),
    # which the shared defect-instruction block legitimately names in BOTH
    # arms' prompts. Use the fault_marker value canary instead to pin the
    # value-level leak coverage (it is not taxonomy vocabulary).
    assert "14-day-stale-top1" in forbidden
    # The taxonomy menu itself must NOT be in the forbidden list: it is the
    # registered public adjudication vocabulary (C1), not sealed content.
    assert not (set(DEFECT_TAXONOMY) & set(forbidden))

    for agent in AGENT_IDS:
        p = prompts[agent]
        hyp = AGENT_HYP[agent]

        # A4 normative template anchors (verbatim content of the amendment).
        assert f"HYPOTHESIS_ID: {hyp}\n" in p
        assert f"Your pre-outcome commitment (sealed before evidence was observed): '{COMMITMENT}'\n" in p
        assert _BLOCK_HEADER in p
        assert "evidence_cited (list of evidence_ids you relied on)." in p

        # >= 1 machine-verified record for the hypothesis, with the real
        # field mapping (observation/run ids, arm, per-arm outcome label, sha).
        expected_ids = _relevant_obs_ids(evidence, hyp)
        assert len(expected_ids) >= 1
        assert _block_ids(p) == expected_ids, f"{agent}: block ids != the hypothesis's verified records"
        by_id = {rec["observation_id"]: rec for rec in evidence}
        for ln in _block_lines(p):
            rec = by_id[_line_id(ln)]
            data, prov = rec["data"], rec["provenance"]
            assert f"run_id={rec['run_id']}" in ln
            assert f"arm={data['intervention_id']}" in ln
            assert f"outcome={data['severity']}" in ln
            assert f"snapshot_sha={prov['config_sha256']}" in ln

        # NO oracle: no field name, no value canary, no oracle path.
        assert "true_cause" not in p
        for sub in forbidden:
            assert sub not in p, f"verdict prompt for {agent} leaks oracle content {sub!r}"
        assert "experiments/policy_rag/oracle" not in p


# ---------------------------------------------------------------------------
# The fail-loud guard: a corrupted record carrying a forbidden substring must
# raise — never leak sealed content into the LLM.
# ---------------------------------------------------------------------------
def test_evidence_block_guard_fails_loud_on_oracle_substring():
    rec = {
        "observation_id": "obs_" + "0" * 16,
        "run_id": f"{CASE_ID}::I_R_retrieval_fix::seed0",
        "data": {"intervention_id": "I_R_retrieval_fix", "severity": "critical", "hypothesis": "H_R"},
        "provenance": {"config_sha256": "c" * 64},
    }
    assert _evidence_block([rec], "H_R").startswith("- evidence_id=")

    bad = dict(rec)
    bad["data"] = {**rec["data"], "severity": "true_cause_exposed"}
    with pytest.raises(RuntimeError, match="forbidden oracle"):
        _evidence_block([bad], "H_R")


# ---------------------------------------------------------------------------
# A4 gate 4 (Hotspots Critical 2): the SAME committed packet run twice at
# identical budget/model/settings under two verified *contradictory* public
# evidence views. The second record is published through the REAL escrow
# ledger at RESOLVE (publish_evidence is legal in EXECUTE and RESOLVE — no
# fake ledger bypass). Asserts: both the canonical and the contradictory
# observation ids reach the LLM-visible prompt; the sealed oracle content
# does not; the commitment text is byte-identical; the ONLY prompt delta is
# the inserted record line.
# ---------------------------------------------------------------------------
_EXTRA_OBS_ID = "obs_" + "a" * 16


def _contradictory_obs() -> EvidenceObservation:
    """A second verified public record whose outcome label CONTRADICTS the
    canonical I_R run (canonical: severity critical, window 30d)."""
    return EvidenceObservation(
        observation_id=_EXTRA_OBS_ID,
        case_id=CASE_ID,
        producer_id="alpha",
        run_id=f"{CASE_ID}::I_R_retrieval_fix::seed1",
        kind="verified_run",
        summary="Contradictory verified observation for the A4 gate-4 regression.",
        data={
            "intervention_id": "I_R_retrieval_fix",
            "severity": "pass",  # contradicts the canonical run's "critical"
            "hypothesis": "H_R",
        },
        provenance={"config_sha256": "b" * 64},
        published_at="2026-10-08T00:00:00+00:00",
    )


def _run_view(tmp: Path, contradictory: bool) -> Tuple[LiveEESSOrchestrator, Dict[str, str]]:
    orch_holder: Dict[str, Any] = {}
    cs = _fresh_clients()
    cs_holder: Dict[str, Any] = {"clients": cs}

    def on_event(type_: str, payload: Dict[str, Any]) -> None:
        if type_ == "phase" and payload.get("payload", {}).get("phase") == "RESOLVE":
            # RESOLVE phase is current; the ledger gate allows publish_evidence.
            orch_holder["orch"].escrow.ledger.publish_evidence(_contradictory_obs())

    esc = EscrowedEscrow(tmp / "escrow")
    orch = LiveEESSOrchestrator(
        claim=_claim(),
        out_root=tmp / "runs",
        escrow=esc,
        policy_factory=lambda _a: LocalEigPolicy({}),
        client_factory=lambda a: cs_holder["clients"][a],
        envelope=_envelope(),
        harness_seed=SEED,
        on_event=on_event if contradictory else None,
    )
    orch_holder["orch"] = orch
    result = orch.run()
    assert result.status == "completed"
    return orch, _verdict_prompts(cs)


def test_a4_gate4_contradictory_evidence_regression(tmp_path: Path):
    orch1, prompts1 = _run_view(tmp_path / "v1", contradictory=False)
    orch2, prompts2 = _run_view(tmp_path / "v2", contradictory=True)

    # The contradictory record went through the real ledger, once.
    assert len(orch1.escrow.evidence()) == 4
    assert len(orch2.escrow.evidence()) == 5
    assert any(r["observation_id"] == _EXTRA_OBS_ID for r in orch2.escrow.evidence())

    for agent in AGENT_IDS:
        p1, p2 = prompts1[agent], prompts2[agent]

        # (commitment) byte-identical across the two views:
        l1 = [ln for ln in p1.splitlines() if ln.startswith("Your pre-outcome commitment")]
        l2 = [ln for ln in p2.splitlines() if ln.startswith("Your pre-outcome commitment")]
        assert l1 == l2 and l1

        # (a) actual + contradictory observation ids present; ONLY delta is
        #     the inserted line.
        if agent == "alpha":  # the agent whose hypothesis I_R maps to
            ids1, ids2 = set(_block_ids(p1)), set(_block_ids(p2))
            assert _EXTRA_OBS_ID in ids2, "contradictory observation id must reach the prompt"
            assert ids2 - ids1 == {_EXTRA_OBS_ID}, "only the extra record may change the block"
            assert ids1 < ids2, "canonical records must all still be present"
        else:
            assert p1 == p2, f"{agent}: unrelated-hypothesis prompt must be byte-identical"

        # Line-level diff: the single inserted line carries the new id.
        s1, s2 = set(p1.splitlines()), set(p2.splitlines())
        added = [ln for ln in p2.splitlines() if ln not in s1]
        removed = [ln for ln in p1.splitlines() if ln not in s2]
        assert removed == [], f"no canonical line may be lost: {removed}"
        if agent == "alpha":
            assert len(added) == 1 and added[0].startswith(f"- evidence_id={_EXTRA_OBS_ID}")
        else:
            assert added == []

        # (b) sealed oracle content absent from BOTH views.
        for sub in _forbidden_substrings():
            assert sub not in p2, f"gate-4 prompt leaks oracle content {sub!r}"
            assert sub not in p1


# ---------------------------------------------------------------------------
# evidence_cited round-trip: the LLM's cited ids (a real id from its own
# prompt) land in agent_verdicts and in final_verdict.json — checkable
# offline against the run's sealed artifacts.
# ---------------------------------------------------------------------------
def test_evidence_cited_round_trips_into_verdicts(tmp_path: Path):
    class CitingClient(CapturingFakeLLMClient):
        """Verdicts by citing exactly one evidence id from its own prompt.

        Sets ``_verdict_payload`` per call then delegates to
        :meth:`super().chat` so the fixed per-call usage delta (and the
        arm's snapshot-delta accounting) is advanced exactly as in a real
        run — never an early return with zero usage.
        """

        def chat(self, prompt: str, system: str = "s", max_tokens: int | None = None) -> str:
            if VERDICT_MARKER in prompt:
                ids = _block_ids(prompt)
                assert ids, "verdict prompt must carry evidence ids to cite"
                self._verdict_payload = {
                    "conclusion": "supported",
                    "confidence": 0.9,
                    "defect_class": "retrieval_omission",
                    "target_artifact": "retrieval",
                    "statement": "s",
                    "evidence_cited": [ids[0]],
                }
            return super().chat(prompt, system=system, max_tokens=max_tokens)

    clients: Dict[str, CapturingFakeLLMClient] = {a: CitingClient() for a in AGENT_IDS}
    arm = EESSLiveS5Arm(lambda a: clients[a], harness_seed=SEED)
    env = _envelope()
    arm.run(
        _claim(),
        BudgetLedger(env),
        ArmSpec(arm_name="S5", claim_id="claim_live_test", envelope=env),
        tmp_path / "S5",
    )
    run_dir = tmp_path / "S5" / "run-01"

    fv = _load_json(run_dir / "final_verdict.json")
    by_agent = {v["agent_id"]: v for v in fv["agent_verdicts"]}
    assert set(by_agent) == set(AGENT_IDS)

    # Ground truth for "real id": the escrow evidence of THIS run. (S5 keeps
    # a real ledger, so the sealed artifacts live under run_dir/escrow/.)
    orch_evidence = [
        json.loads(ln) for ln in (run_dir / "escrow" / "evidence.jsonl").read_text().splitlines()
    ]
    all_ids = {r["observation_id"] for r in orch_evidence}
    for agent in AGENT_IDS:
        cited = by_agent[agent]["evidence_cited"]
        expected = _relevant_obs_ids(orch_evidence, AGENT_HYP[agent])
        assert isinstance(cited, list) and len(cited) == 1
        assert cited[0] in expected, f"{agent} cited {cited!r} which was not in its prompt"
        assert cited[0] in all_ids, "cited id must exist in the run's sealed artifacts"

    # A client that cites nothing yields [] (advisory, never crashes).
    class NoCiteClient(CapturingFakeLLMClient):
        def chat(self, prompt: str, system: str = "s", max_tokens: int | None = None) -> str:
            if VERDICT_MARKER in prompt:
                self._verdict_payload = {"conclusion": "refuted", "confidence": 0.4}
            return super().chat(prompt, system=system, max_tokens=max_tokens)

    arm2 = EESSLiveS5Arm(lambda _a: NoCiteClient(), harness_seed=SEED)
    arm2.run(
        _claim(),
        BudgetLedger(_envelope()),
        ArmSpec(arm_name="S5", claim_id="claim_live_test", envelope=_envelope()),
        tmp_path / "S5nc",
    )
    fv2 = _load_json(tmp_path / "S5nc" / "run-01" / "final_verdict.json")
    for v in fv2["agent_verdicts"]:
        assert v["evidence_cited"] == []


# ---------------------------------------------------------------------------
# A4 gate 2: deterministic FakeLLMClient parity re-run of ALL THREE live arms
# (eess / eess_no_escrow / eess_random_select).
#
# (i)  Two fresh reruns are byte-identical in trace structure, verdict-prompt
#      payloads, and (wall-stripped) final_verdict + budget_ledger.
# (ii) The ONLY delta vs the pre-amendment behavior is the prompt payload +
#      the new evidence_cited field: every pre-existing field of
#      final_verdict.json keeps its value against the committed pre-amendment
#      golden (run-branch dc0e78f artifact, tests/fixtures/
#      a4_prebranch_dc0e78f/), and the non-verdict trace payloads are
#      unchanged.
# ---------------------------------------------------------------------------
def _run_arm_captured(arm_cls: type, tmp: Path) -> Tuple[Any, Any, Any, Any]:
    clients = _fresh_clients()
    arm = arm_cls(lambda a: clients[a], harness_seed=SEED)
    env = _envelope()
    arm.run(
        _claim(),
        BudgetLedger(env),
        ArmSpec(arm_name=arm_cls.arm_label, claim_id="claim_live_test", envelope=env),
        tmp / arm_cls.arm_label,
    )
    run_dir = tmp / arm_cls.arm_label / "run-01"
    fv = _load_json(run_dir / "final_verdict.json")
    bl = _load_json(run_dir / "budget_ledger.json")
    traces = [json.loads(ln) for ln in (run_dir / "traces.jsonl").read_text().splitlines()]
    return clients, fv, bl, traces


def test_a4_gate2_three_arm_determinism_and_golden_stability(tmp_path: Path):
    for arm_cls in (EESSLiveS5Arm, EESSLiveA1Arm, EESSLiveA3Arm):
        label = arm_cls.arm_label

        # (i) determinism: two fresh reruns.
        cA, fvA, blA, trA = _run_arm_captured(arm_cls, tmp_path / f"{label}_a")
        cB, fvB, blB, trB = _run_arm_captured(arm_cls, tmp_path / f"{label}_b")
        assert json.dumps(_strip_wall(fvA), sort_keys=True) == json.dumps(_strip_wall(fvB), sort_keys=True)
        assert json.dumps(_strip_wall(blA), sort_keys=True) == json.dumps(_strip_wall(blB), sort_keys=True)
        assert _trace_shape(trA) == _trace_shape(trB)
        assert _verdict_prompts(cA) == _verdict_prompts(cB), f"{label}: prompt payloads must be byte-identical"

        # (ii) golden field-stability vs the PRE-AMENDMENT (dc0e78f) baseline.
        golden = _load_json(FIXTURES / f"final_verdict_{label}.json")
        assert set(golden) <= set(fvA), f"{label}: pre-existing keys must all persist"
        for key, gval in golden.items():
            if key in WALL_KEYS:
                continue
            if key == "agent_verdicts":
                g_by = {v["agent_id"]: v for v in gval}
                a_by = {v["agent_id"]: v for v in fvA["agent_verdicts"]}
                assert set(g_by) == set(a_by)
                for agent, gentry in g_by.items():
                    aentry = a_by[agent]
                    assert set(gentry) <= set(aentry), f"{label}/{agent}: pre-existing verdict keys must persist"
                    for k, gv in gentry.items():
                        assert aentry[k] == gv, f"{label}/{agent}: pre-existing field {k!r} changed"
                    assert set(aentry) - set(gentry) == {"evidence_cited"}, f"{label}/{agent}: unexpected new key"
                    assert isinstance(aentry["evidence_cited"], list)
            else:
                assert fvA[key] == gval, f"{label}: pre-existing field {key!r} changed vs pre-amendment golden"

        # The non-verdict trace payloads are byte-unchanged (the prompt itself
        # is never written to traces.jsonl — it is covered by the recorded
        # prompt-payload comparison above); event count and (seq, type, agent)
        # are identical.
        golden_traces = [json.loads(ln) for ln in (FIXTURES / f"traces_{label}.jsonl").read_text().splitlines()]
        g_shape = _trace_shape(golden_traces)
        a_shape = _trace_shape(trA)
        assert [(s, t, a) for (s, t, a, _p) in g_shape] == [(s, t, a) for (s, t, a, _p) in a_shape]
        assert len(g_shape) == len(a_shape)
        for ge, ae in zip(g_shape, a_shape):
            assert ge[3] == ae[3], f"{label}: trace payload changed at seq {ge[0]} (type {ge[1]})"


# ---------------------------------------------------------------------------
# Fixture sanity: the committed goldens are the PRE-amendment artifacts.
# ---------------------------------------------------------------------------
def test_golden_fixtures_are_pre_amendment():
    for label in ("S5", "A1", "A3"):
        fv = _load_json(FIXTURES / f"final_verdict_{label}.json")
        assert fv["schema"] == "p08.final_verdict/1"
        assert "evidence_cited" not in json.dumps(fv), "golden must be the PRE-amendment artifact"
        for v in fv["agent_verdicts"]:
            assert set(v) == {"agent_id", "verdict", "confidence"}
        assert (FIXTURES / f"traces_{label}.jsonl").is_file()
