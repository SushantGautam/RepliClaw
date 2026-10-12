"""Focused offline checks for the CompoundCausal-32 simulator and oracle boundary."""
from __future__ import annotations

import json
from collections import Counter

import pytest

from repliclaw.benchmarks.compound_causal import (
    BenchmarkSession,
    generate_dataset,
    load_dataset,
    score_predictions,
)
from repliclaw.benchmarks.compound_causal.core import FACTORS


@pytest.fixture()
def generated(tmp_path):
    root = tmp_path / "cc"
    manifest = generate_dataset(root, seed=7122026)
    cards, gold = load_dataset(root)
    return root, manifest, cards, gold


def test_generation_balance_and_replay(generated, tmp_path):
    root, manifest, cards, gold = generated
    assert len(cards) == len(gold) == 32
    assert Counter(w["stratum"] for w in gold.values()) == {
        "shared/simple": 8, "shared/compound": 8,
        "distributed/simple": 8, "distributed/compound": 8,
    }
    other = tmp_path / "second"
    generate_dataset(other, seed=7122026)
    assert (root / "public" / "cases.jsonl").read_bytes() == (other / "public" / "cases.jsonl").read_bytes()
    assert (root / "private" / "oracles.jsonl").read_bytes() == (other / "private" / "oracles.jsonl").read_bytes()
    assert manifest["seed_type"] == "development_fixed"
    assert set(cards) == set(gold)


def test_public_cards_cannot_reveal_hidden_causes(generated):
    root, _, cards, gold = generated
    public = (root / "public" / "cases.jsonl").read_text()
    for literal in ("hidden_causes", "causal_logic", "stratum", "private_nonce"):
        assert literal not in public
    for cid, card in cards.items():
        assert cid == gold[cid]["case_id"]
        assert card["case_id"].startswith("CC-")
        assert "world_commitment" in card
        assert "causal_logic" not in BenchmarkSession(card, gold[cid]).card()
        if card["evidence_mode"] == "distributed":
            assert not card["initial_evidence"]


def test_structural_interventions_recompute_instead_of_relabel(generated):
    _, _, cards, gold = generated
    counts = Counter()
    for case_id, world in gold.items():
        session = BenchmarkSession(cards[case_id], world)
        baseline = session.intervene([])
        factors = world["hidden_causes"]
        logic = world["causal_logic"]
        counts[logic] += 1
        assert (baseline["incident"] == "resolved") == (logic == "clean")
        if logic == "single":
            assert len(factors) == 1
            assert session.intervene([factors[0]])["incident"] == "resolved"
            other = next(f for f in FACTORS if f not in factors)
            assert session.intervene([other])["incident"] == "present"
        if logic == "or":
            assert len(factors) == 2
            assert session.intervene([factors[0]])["incident"] == "present"
            assert session.intervene([factors[1]])["incident"] == "present"
            assert session.intervene(factors)["incident"] == "resolved"
        if logic == "and":
            assert len(factors) == 2
            assert session.intervene([factors[0]])["incident"] == "resolved"
            assert session.intervene([factors[1]])["incident"] == "resolved"
    assert counts == {"clean": 4, "single": 12, "or": 8, "and": 8}


def test_blind_observation_and_escrow_order(generated):
    _, _, cards, gold = generated
    cid = next(k for k, v in cards.items() if v["evidence_mode"] == "distributed")
    session = BenchmarkSession(cards[cid], gold[cid])
    assert session.card()["initial_evidence"] == {}
    assert session.observe("policy")["channel"] == "policy"
    sealed = session.commit("inv-a", ["retrieval"], ["retrieval"], 0.4)
    assert "predicted_causes" not in json.dumps(sealed)
    assert len(session.public_history()["still_sealed_commitments"]) == 1
    result = session.intervene(["retrieval"])
    assert len(result["revealed_forecasts"]) == 1
    assert result["revealed_forecasts"][0]["commitment"] == sealed["commitment"]
    assert session.public_history()["still_sealed_commitments"] == []
    with pytest.raises(ValueError, match="after seeing"):
        session.commit("inv-b", ["judge"], ["retrieval"], 0.9)


def test_equal_tool_access_and_budgets_all_strata(generated):
    _, _, cards, gold = generated
    for cid in cards:
        session = BenchmarkSession(cards[cid], gold[cid])
        for f in FACTORS:
            session.observe(f)
        with pytest.raises(ValueError, match="channel-read budget"):
            session.observe("retrieval")
        for _ in range(6):
            session.intervene([])
        with pytest.raises(ValueError, match="intervention budget"):
            session.intervene([])
    # There is no arm_id distinction in the tool API: same action envelope.


def test_private_evaluator_exact_cause_and_interaction(generated):
    _, _, _, gold = generated
    submissions = [
        {"case_id": cid, "predicted_causes": world["hidden_causes"],
         "predicted_logic": world["causal_logic"]}
        for cid, world in gold.items()
    ]
    result = score_predictions(gold, submissions)
    assert result["exact_causes"] == result["exact_cause_and_logic"] == 32
    mutated = dict(submissions[0])
    mutated["predicted_logic"] = "abstain"
    result = score_predictions(gold, [mutated] + submissions[1:])
    assert result["exact_cause_and_logic"] == 31
    with pytest.raises(ValueError, match="duplicate"):
        score_predictions(gold, [submissions[0], submissions[0]])
