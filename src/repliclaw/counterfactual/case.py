"""Frozen case + intervention spec for the P02 counterfactual hero case.

``CaseSpec`` is the frozen, hashable description of a controlled experiment:
scenario, public policy documents, the order under test, and the BASE value of
every single-factor dimension (retrieval, policy-conflict rendering, judge
reference rubric, model prompt).

``InterventionSpec`` declares which factor(s) it perturbs relative to the base
case. Causal arms (I_R, I_P, I_J) change exactly ONE factor; the I_C control
changes the documented TWO-factor combination (retrieval + judge reference).

Canonical bytes are compact, sort-keyed JSON, so sha256 is stable across runs
and platforms (contract §5 single-factor + replay rules).
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict

# The four single-factor dimensions a counterfactual arm may perturb.
FACTOR_RETRIEVAL = "retrieval"
FACTOR_POLICY_CONFLICT = "policy_conflict"
FACTOR_JUDGE_REFERENCE = "judge_reference"
FACTOR_MODEL_PROMPT = "model_prompt"

ALL_FACTORS = (
    FACTOR_RETRIEVAL,
    FACTOR_POLICY_CONFLICT,
    FACTOR_JUDGE_REFERENCE,
    FACTOR_MODEL_PROMPT,
)


def canonical_bytes(obj: Any) -> bytes:
    """Compact, key-sorted canonical JSON -> stable sha256."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class CaseSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: str
    case_version: str = "v1"
    target_model_id: str  # e.g. "deterministic-rag-assistant/v1"
    scenario: Dict[str, Any]  # {name, description, test_prompt, expected_behavior}
    policy_docs: List[Dict[str, Any]]  # public policy document set
    order: Dict[str, Any]  # the order under test
    base_retrieval: List[str]  # base retrieved snippets (stale top-1, 30-day absent)
    base_policy_conflict: str  # base policy-conflict rendering
    base_judge_reference_days: int  # base (stale) rubric reference
    base_model_prompt: str  # base system prompt

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self.model_dump(mode="json"))

    @property
    def sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())

    def base_config(self) -> Dict[str, Any]:
        """The base value of every single-factor dimension."""
        return {
            FACTOR_RETRIEVAL: list(self.base_retrieval),
            FACTOR_POLICY_CONFLICT: self.base_policy_conflict,
            FACTOR_JUDGE_REFERENCE: self.base_judge_reference_days,
            FACTOR_MODEL_PROMPT: self.base_model_prompt,
        }


class InterventionSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    intervention_id: str
    case_id: str
    # A causal arm sets exactly ONE override; the I_C control sets
    # retrieval + judge_reference_days (the documented 2-factor interaction).
    retrieval: Optional[List[str]] = None
    policy_conflict: Optional[str] = None
    judge_reference_days: Optional[int] = None
    model_prompt: Optional[str] = None

    def changed_factors(self) -> List[str]:
        out: List[str] = []
        if self.retrieval is not None:
            out.append(FACTOR_RETRIEVAL)
        if self.policy_conflict is not None:
            out.append(FACTOR_POLICY_CONFLICT)
        if self.judge_reference_days is not None:
            out.append(FACTOR_JUDGE_REFERENCE)
        if self.model_prompt is not None:
            out.append(FACTOR_MODEL_PROMPT)
        return out

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self.model_dump(mode="json"))

    @property
    def sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())

    def resolve(self, case: CaseSpec) -> Dict[str, Any]:
        """Merge base factor values with this intervention's overrides."""
        cfg = case.base_config()
        if self.retrieval is not None:
            cfg[FACTOR_RETRIEVAL] = list(self.retrieval)
        if self.policy_conflict is not None:
            cfg[FACTOR_POLICY_CONFLICT] = self.policy_conflict
        if self.judge_reference_days is not None:
            cfg[FACTOR_JUDGE_REFERENCE] = self.judge_reference_days
        if self.model_prompt is not None:
            cfg[FACTOR_MODEL_PROMPT] = self.model_prompt
        return cfg
