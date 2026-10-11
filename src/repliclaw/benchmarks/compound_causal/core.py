"""CompoundCausal-32: deterministic, *executed* synthetic counterfactual cases.

Generates 32 cases in a balanced 2x2 design:
  {shared, distributed} evidence x {simple, compound} causes.
Simple includes clean negative controls. Compound has OR and AND interactions.

Agents must be restricted to a tool interface backed by BenchmarkSession in
a separate trusted process. Importing this module in a fully privileged agent
process is NOT an isolation boundary. Never mount private/oracles.jsonl in an
agent workspace. Synthetic simulator outcomes are not real AI-system tests.
"""
from __future__ import annotations

import copy
import hashlib
import itertools
import json
import random
import secrets
from pathlib import Path
from typing import Any

FACTORS = ("retrieval", "tool_data", "policy", "judge")
EVIDENCE_MODES = ("shared", "distributed")
LOGICS = ("clean", "single", "or", "and")
MAX_EXPERIMENTS = 6
MAX_OBSERVATIONS = 4
MAX_REPAIRS = 2
VERSION = "compound_causal_32/v1"

CONTEXTS = (
    "customer returns assistant",
    "account access assistant",
    "product catalog assistant",
    "payment support assistant",
    "shipment tracking assistant",
    "meeting scheduling assistant",
    "internal knowledge assistant",
    "inventory assistant",
)
SIGNAL_NAMES = {
    "retrieval": "retrieved-document consistency",
    "tool_data": "external-tool response consistency",
    "policy": "instruction-priority consistency",
    "judge": "independent evaluation consistency",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _normalize_repairs(repairs: Any) -> tuple[str, ...]:
    if not isinstance(repairs, (list, tuple)):
        raise ValueError("repairs must be an array of factor names")
    if len(set(repairs)) != len(repairs):
        raise ValueError("duplicate repair factor")
    if len(repairs) > MAX_REPAIRS or any(f not in FACTORS for f in repairs):
        raise ValueError(f"choose 0-{MAX_REPAIRS} distinct factors from {FACTORS}")
    return tuple(f for f in FACTORS if f in repairs)


def _noisy_signals(rng: random.Random, hidden: set[str]) -> dict[str, Any]:
    """Noisy *correlates*, never perfect oracle-derived labels."""
    observations: dict[str, Any] = {}
    for factor in FACTORS:
        elevated = rng.random() < (0.68 if factor in hidden else 0.28)
        independent_alarm = rng.random() < (0.57 if factor in hidden else 0.35)
        observations[factor] = {
            "measurement": SIGNAL_NAMES[factor],
            "trace_indicator": "atypical" if elevated else "ordinary",
            "secondary_indicator": "alert" if independent_alarm else "clear",
            "notice": "These indicators can be false-positive or false-negative.",
        }
    return observations


def _generate(seed: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rng = random.Random(seed)
    cards: list[dict[str, Any]] = []
    oracles: list[dict[str, Any]] = []
    pairs = list(itertools.combinations(FACTORS, 2))
    for mode in EVIDENCE_MODES:
        for complexity in ("simple", "compound"):
            candidates: list[tuple[tuple[str, ...], str]] = []
            if complexity == "simple":
                candidates = [
                    ((), "clean"), ((), "clean"),
                    (("retrieval",), "single"), (("tool_data",), "single"),
                    (("policy",), "single"), (("judge",), "single"),
                    (("retrieval",), "single"), (("judge",), "single"),
                ]
            else:
                rng.shuffle(pairs)
                chosen = pairs[:4] + pairs[2:6]
                candidates = [(pair, "or") for pair in chosen[:4]]
                candidates += [(pair, "and") for pair in chosen[4:]]
            rng.shuffle(candidates)
            for idx, (causes, logic) in enumerate(candidates):
                nonce = f"{rng.getrandbits(128):032x}"
                case_id = "CC-" + hashlib.sha256(nonce.encode("ascii")).hexdigest()[:12]
                context = CONTEXTS[(idx + rng.randrange(len(CONTEXTS))) % len(CONTEXTS)]
                signals = _noisy_signals(rng, set(causes))
                card = {
                    "schema": VERSION,
                    "case_id": case_id,
                    "scenario": context,
                    "task": (
                        "Determine the smallest supported set of causal fault factors, "
                        "or conclude no defect. Diagnose interactions when justified "
                        "by counterfactual tests. Do not assume the reported complaint "
                        "implies a real defect."
                    ),
                    "candidate_factors": list(FACTORS),
                    "visible_channels": list(FACTORS),
                    "evidence_mode": mode,
                    # Shared cases begin with all evidence. Distributed cases must
                    # query channels; BOTH central and decentralized arms may query
                    # ALL channels using identical observe() budgets.
                    "initial_evidence": copy.deepcopy(signals) if mode == "shared" else {},
                    "max_interventions": MAX_EXPERIMENTS,
                    "max_channel_reads": MAX_OBSERVATIONS,
                    "max_repairs_per_intervention": MAX_REPAIRS,
                    # Commitment salted by the private nonce, so small hypothesis
                    # spaces cannot be brute-forced from an unsalted digest.
                    "world_commitment": _sha({"nonce": nonce, "causes": causes, "logic": logic}),
                }
                gold = {
                    "case_id": case_id,
                    "schema": VERSION,
                    "private_nonce": nonce,
                    "hidden_causes": list(causes),
                    "causal_logic": logic,
                    "stratum": f"{mode}/{complexity}",
                    "channel_evidence": signals,
                }
                cards.append(card)
                oracles.append(gold)
    paired = list(zip(cards, oracles))
    rng.shuffle(paired)
    cards = [c for c, _ in paired]
    oracles = [o for _, o in paired]
    if len({c["case_id"] for c in cards}) != 32:
        raise RuntimeError("benchmark case ID collision")
    return cards, oracles


def generate_dataset(root: Path | str, *, seed: int | None = None) -> dict[str, Any]:
    """Write public cards + PRIVATE gold. None => fresh non-published 128-bit seed.

    Fixed seeds are for development only. A blind heldout requires an
    evaluator-controlled private seed and an agent-inaccessible oracle store.
    """
    path = Path(root)
    if (path / "private" / "oracles.jsonl").exists():
        raise FileExistsError("refusing to overwrite existing private benchmark worlds")
    chosen_seed = secrets.randbits(128) if seed is None else int(seed)
    cards, oracles = _generate(chosen_seed)
    public_dir = path / "public"
    private_dir = path / "private"
    public_dir.mkdir(parents=True, exist_ok=True)
    private_dir.mkdir(parents=True, exist_ok=True)
    private_dir.chmod(0o700)
    public_bytes = "".join(_canonical(x) + "\n" for x in cards)
    gold_bytes = "".join(_canonical(x) + "\n" for x in oracles)
    (public_dir / "cases.jsonl").write_text(public_bytes, encoding="utf-8")
    private_file = private_dir / "oracles.jsonl"
    private_file.write_text(gold_bytes, encoding="utf-8")
    private_file.chmod(0o600)
    manifest = {
        "schema": VERSION,
        "n_cases": len(cards),
        "design": {"shared/simple": 8, "shared/compound": 8,
                   "distributed/simple": 8, "distributed/compound": 8},
        "source_type": "synthetic_structural_simulator",
        "claims": "exploratory simulation; no observed model/agent performance yet",
        "public_sha256": hashlib.sha256(public_bytes.encode("utf-8")).hexdigest(),
        "private_gold_must_not_be_mounted_in_agent_workspace": True,
        "seed_type": "random_private" if seed is None else "development_fixed",
    }
    (public_dir / "manifest.json").write_text(_canonical(manifest) + "\n", encoding="utf-8")
    return manifest


def load_dataset(root: Path | str) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Trusted evaluator-side loader. NEVER expose the second return value to agents."""
    path = Path(root)
    def read(p: Path) -> dict[str, dict[str, Any]]:
        return {d["case_id"]: d for line in p.read_text(encoding="utf-8").splitlines()
                if (d := json.loads(line))}
    cards = read(path / "public" / "cases.jsonl")
    gold = read(path / "private" / "oracles.jsonl")
    if len(cards) != len(gold) or set(cards) != set(gold):
        raise ValueError("public/private case roster mismatch")
    return cards, gold


class BenchmarkSession:
    """Tool-server runtime. Return ONLY card(), observe(), commit(), intervene().

    The trusted host keeps the oracle instance private and exports method results,
    NOT a Python object/reference or agent-readable filesystem containing gold.
    Same API and budgets for single, central and decentralized agents.
    """

    def __init__(self, public_case: dict[str, Any], private_world: dict[str, Any]) -> None:
        if public_case["case_id"] != private_world["case_id"]:
            raise ValueError("public/private case IDs do not match")
        self._card = copy.deepcopy(public_case)
        self._gold = copy.deepcopy(private_world)
        self._reads: list[dict[str, Any]] = []
        self._experiments: list[dict[str, Any]] = []
        self._pending: list[dict[str, Any]] = []
        self._revealed: list[dict[str, Any]] = []

    def card(self) -> dict[str, Any]:
        return copy.deepcopy(self._card)

    def observe(self, channel: str) -> dict[str, Any]:
        if channel not in FACTORS:
            raise ValueError(f"unknown observation channel {channel!r}")
        if len(self._reads) >= MAX_OBSERVATIONS:
            raise ValueError("channel-read budget exhausted")
        record = {"channel": channel, "evidence": copy.deepcopy(self._gold["channel_evidence"][channel])}
        self._reads.append(copy.deepcopy(record))
        return record

    def commit(
        self, agent_id: str, predicted_causes: list[str], planned_repairs: list[str],
        probability_incident: float,
    ) -> dict[str, Any]:
        """Seal a falsifiable pre-outcome forecast (no public content until reveal)."""
        if not agent_id or not isinstance(agent_id, str):
            raise ValueError("nonempty agent_id required")
        causes = _normalize_repairs(predicted_causes)
        intervention = _normalize_repairs(planned_repairs)
        if any(tuple(x["repairs"]) == intervention for x in self._experiments):
            raise ValueError("cannot make pre-outcome forecast after seeing this intervention")
        if not 0 <= probability_incident <= 1:
            raise ValueError("probability_incident must lie in [0,1]")
        packet = {
            "agent_id": agent_id, "predicted_causes": list(causes),
            "planned_repairs": list(intervention), "probability_incident": probability_incident,
            "sequence": len(self._pending) + len(self._revealed),
        }
        digest = _sha({"private_nonce": self._gold["private_nonce"], "packet": packet})
        self._pending.append({"commitment": digest, "packet": packet})
        return {"commitment": digest, "sealed": True}

    def intervene(self, repairs: list[str]) -> dict[str, Any]:
        """ACTUALLY recompute the simulator's causal structural equation."""
        factors = _normalize_repairs(repairs)
        if len(self._experiments) >= MAX_EXPERIMENTS:
            raise ValueError("intervention budget exhausted")
        faults = set(self._gold["hidden_causes"])
        remaining = faults.difference(factors)
        logic = self._gold["causal_logic"]
        if logic == "clean":
            incident = False
        elif logic in ("single", "or"):
            incident = bool(remaining)
        elif logic == "and":
            incident = bool(faults) and all(f in remaining for f in faults)
        else:
            raise RuntimeError("invalid private structural equation")
        receipt = {
            "case_id": self._card["case_id"],
            "execution_type": "deterministic_synthetic_structural_intervention",
            "repairs": list(factors),
            "incident": "present" if incident else "resolved",
            "attempt": len(self._experiments) + 1,
        }
        receipt["observation_sha256"] = _sha(receipt)
        self._experiments.append(copy.deepcopy(receipt))
        for pending in list(self._pending):
            if tuple(pending["packet"]["planned_repairs"]) == factors:
                packet = copy.deepcopy(pending["packet"])
                forecast = {
                    "commitment": pending["commitment"],
                    "packet": packet,
                    "observed_incident": incident,
                    "brier": round((packet["probability_incident"] - float(incident)) ** 2, 6),
                }
                self._revealed.append(forecast)
                self._pending.remove(pending)
        # Forecasts are revealed only AFTER the actual experiment is recorded.
        return {**receipt, "revealed_forecasts": [
            copy.deepcopy(x) for x in self._revealed
            if tuple(x["packet"]["planned_repairs"]) == factors
        ]}

    def public_history(self) -> dict[str, Any]:
        return {
            "case_id": self._card["case_id"],
            "observations": copy.deepcopy(self._reads),
            "interventions": copy.deepcopy(self._experiments),
            "revealed_forecasts": copy.deepcopy(self._revealed),
            "still_sealed_commitments": [x["commitment"] for x in self._pending],
            "used_interventions": len(self._experiments),
            "used_channel_reads": len(self._reads),
        }


def score_predictions(
    private_worlds: dict[str, dict[str, Any]],
    submissions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluator-only scorer. Predictions must be frozen BEFORE calling this."""
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for item in submissions:
        case_id = item["case_id"]
        if case_id in seen or case_id not in private_worlds:
            raise ValueError(f"duplicate or unknown prediction: {case_id}")
        seen.add(case_id)
        expected = private_worlds[case_id]
        pred_causes = _normalize_repairs(item.get("predicted_causes", []))
        pred_logic = item.get("predicted_logic")
        if pred_logic not in LOGICS and pred_logic != "abstain":
            raise ValueError("predicted_logic must be clean, single, or, and, or abstain")
        causes_exact = set(pred_causes) == set(expected["hidden_causes"]) and pred_logic != "abstain"
        full_exact = causes_exact and pred_logic == expected["causal_logic"]
        rows.append({
            "case_id": case_id, "stratum": expected["stratum"],
            "causes_exact": causes_exact, "cause_and_logic_exact": full_exact,
            "abstained": pred_logic == "abstain",
        })
    strata = sorted({w["stratum"] for w in private_worlds.values()})
    summary = {
        s: {
            "scored": sum(x["stratum"] == s for x in rows),
            "exact": sum(x["stratum"] == s and x["cause_and_logic_exact"] for x in rows),
        } for s in strata
    }
    return {
        "schema": VERSION,
        "total_cases": len(private_worlds),
        "scored_cases": len(rows),
        "exact_cause_and_logic": sum(x["cause_and_logic_exact"] for x in rows),
        "exact_causes": sum(x["causes_exact"] for x in rows),
        "abstentions": sum(x["abstained"] for x in rows),
        "by_stratum": summary,
        "per_case": rows,
        "note": "synthetic evaluator-only ground truth; no empirical arm superiority implied",
    }
