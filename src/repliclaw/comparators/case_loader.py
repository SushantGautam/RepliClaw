"""Same-task case loading for the P08 runner CLI (checklist item 4 / C1).

Every arm must be handed the SAME :class:`~repliclaw.models.Claim` for a given
case — a single source of truth built from the case's own frozen files (never
from per-arm hardcoded data, and never from the sealed oracle). The sealed
oracle is a SCORER-ONLY input; :func:`load_arm_claim` must never read it (a
test asserts the oracle path is never opened).

The loader resolves a CLI ``--case`` value to a :class:`CaseSpec` describing:

* the canonical case id,
* the sealed oracle path (scorer-only; arms must never read it),
* whether the offline EESS slice is applicable (it is rooted to the canonical
  ``policy_rag_v1`` case by construction, so running it against any other claim
  is a same-task violation and is refused, never silently re-routed),
* whether the case is a secondary (no-LLM) case.

The WIP this re-derives from attempted ``from ...case import
FALSIFIABLE_QUESTION`` for the tox21 case, but that symbol does not exist (the
question lives only in the module docstring); this build instead extracts it
from the module docstring via :mod:`ast` (no import, so the RDKit-dependent
tox21 module is never imported at claim-load time).
"""
from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .budget import BudgetEnvelope
from ..models import Claim

# Canonical case directories (relative to the repo root).
_POLICY_RAG_DIR = Path("experiments") / "policy_rag"
_TOX21_DIR = Path("src") / "repliclaw" / "counterfactual" / "cases" / "tox21_ar_agonist"

# CLI case-name -> (canonical case_id, relative dir).
_CASE_ALIASES = {
    "policy_rag": ("policy_rag_v1", _POLICY_RAG_DIR),
    "policy_rag_v1": ("policy_rag_v1", _POLICY_RAG_DIR),
    "tox21_ar_agonist": ("tox21_ar_agonist", _TOX21_DIR),
}


class CaseNotSupportedError(ValueError):
    """The given ``--case`` value does not identify a registered P08 case."""


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    repo_root: Path
    oracle_path: Optional[Path]  # scorer-only; arms must never read it
    offline_eess_ok: bool  # offline EESS slice is rooted to this case
    secondary: bool  # secondary case => offline (no-LLM) arms only

    def oracle(self) -> Path:
        if self.oracle_path is None:
            raise CaseNotSupportedError(
                f"case {self.case_id} has no sealed oracle"
            )
        return self.oracle_path


def repo_root() -> Path:
    """Repo root = three levels above this file (src/repliclaw/comparators/)."""
    return Path(__file__).resolve().parents[3]


def resolve_case(case: str, root: Optional[Path] = None) -> CaseSpec:
    """Resolve a CLI ``--case`` value (name or path) to a :class:`CaseSpec`.

    Accepts the canonical case name (``policy_rag`` / ``tox21_ar_agonist``) or
    the path to the case directory, relative to ``root`` (default: the repo
    root). Unknown values raise :class:`CaseNotSupportedError`.
    """
    root = Path(root) if root is not None else repo_root()
    key = str(case).strip().strip("/")
    name = Path(key).name if Path(key).is_absolute() else key

    # Name match (canonical id or a registered alias).
    if key in _CASE_ALIASES or name in _CASE_ALIASES:
        case_id, rel = _CASE_ALIASES[key if key in _CASE_ALIASES else name]
    else:
        # Path match (relative or absolute to the case directory).
        cand = Path(key)
        resolved = (
            cand.resolve()
            if cand.is_absolute()
            else (root / cand).resolve()
        )
        match = None
        for cid, rel in _CASE_ALIASES.values():
            if resolved == (root / rel).resolve():
                match = (cid, rel)
                break
        if match is None:
            raise CaseNotSupportedError(
                f"--case {case!r} is not a registered P08 case; expected one of "
                f"{sorted(c for c in _CASE_ALIASES)} or their directories"
            )
        case_id, rel = match

    secondary = case_id == "tox21_ar_agonist"
    return CaseSpec(
        case_id=case_id,
        repo_root=root,
        oracle_path=root / rel / "oracle" / "oracle.json",
        offline_eess_ok=not secondary,
        secondary=secondary,
    )


def _tox21_statement(root: Path) -> str:
    """Extract the falsifiable question from the tox21 case module docstring.

    The WIP imported a non-existent ``FALSIFIABLE_QUESTION`` symbol; this
    re-derives the same text by parsing the module docstring with :mod:`ast`
    (no import, so the RDKit-dependent case module is never loaded at claim
    time). The question is the paragraph under the ``FALSIFIABLE QUESTION``
    section header, up to the next ``----`` rule.
    """
    case_py = root / _TOX21_DIR / "case.py"
    source = case_py.read_text(encoding="utf-8")
    doc = ast.get_docstring(ast.parse(source)) or ""
    m = re.search(
        r"FALSIFIABLE\s+QUESTION\s*\n-{3,}\s*\n(.*?)(?:\n\s*\n[A-Z][A-Z ]+\n-{3,}|\Z)",
        doc,
        re.DOTALL,
    )
    if m is None:
        raise CaseNotSupportedError(
            "could not locate the FALSIFIABLE QUESTION section in the "
            "tox21 case docstring"
        )
    return " ".join(m.group(1).split())


def load_arm_claim(case_name: str, root: Optional[Path] = None) -> Claim:
    """Build the ONE shared :class:`Claim` for a case, identical for every arm.

    * ``policy_rag`` is built from
      :func:`repliclaw.counterfactual.executor.load_case` (``policy_rag_v1``).
    * ``tox21_ar_agonist`` uses the case's falsifiable question (docstring) as
      its statement.

    This function NEVER opens the sealed oracle — arm-side code has no access
    to the ground truth (a test asserts the oracle path is never read).
    """
    spec = resolve_case(case_name, root)

    if spec.case_id == "policy_rag_v1":
        from ..counterfactual.executor import load_case as _load_case

        cs = _load_case("policy_rag_v1")
        scenario = cs.scenario
        claim = Claim(
            claim_id=f"claim-{spec.case_id}",
            statement=scenario["expected_behavior"],
            domain="policy_rag",
            subclaims=[scenario["description"]],
            data={
                "test_prompt": scenario["test_prompt"],
                "policy_docs": cs.policy_docs,
                "base_retrieval": cs.base_retrieval,
                "order": cs.order,
                "base_policy_conflict": cs.base_policy_conflict,
                "base_judge_reference_days": getattr(
                    cs, "base_judge_reference_days", None
                ),
            },
        )
        return claim

    if spec.case_id == "tox21_ar_agonist":
        return Claim(
            claim_id=f"claim-{spec.case_id}",
            statement=_tox21_statement(spec.repo_root),
            domain="tox21",
            data={"case_id": spec.case_id},
        )

    raise CaseNotSupportedError(spec.case_id)


def default_envelope(case_name: str) -> BudgetEnvelope:
    """The default matched envelope for a case (task spec: 60k / 900 s / 4).

    ``case_name`` is accepted for a stable, documented signature; the default
    envelope is uniform across the supported cases. The prereg v1.1 §5.1 LLM
    baseline envelope is 60,000 / 900 s / 3 agents; the CLI default uses 4
    agents so that S3's evidence-driven follow-up agent (its 4th distinct
    investigator) completes instead of tripping the agent cap — see the
    runner report for this deviation.
    """
    _ = case_name  # uniform default; the name is recorded by the caller.
    return BudgetEnvelope(max_tokens=60_000, max_wall_s=900.0, max_agents=4)


def assert_same_task(arm_name: str, spec: CaseSpec, claim: Claim) -> None:
    """Refuse any arm/claim combination that would run different tasks.

    The same-task rule (C1) is claim-identity: EVERY arm must receive the
    case's own shared claim built by :func:`load_arm_claim`. The offline EESS
    slice executes the canonical ``policy_rag_v1`` slice by construction, so it
    may only be paired with that case; any other pairing is an error, never a
    silent re-route (prereg v1.1 §3.3 / C1).
    """
    if claim.claim_id != f"claim-{spec.case_id}":
        raise CaseNotSupportedError(
            f"claim {claim.claim_id!r} does not match case {spec.case_id!r}; "
            "every arm must receive the case's shared claim (same task, C1)"
        )
    rooted = {"eess": "policy_rag_v1", "eess_offline": "policy_rag_v1"}
    required = rooted.get(arm_name)
    if required is not None and spec.case_id != required:
        raise CaseNotSupportedError(
            f"arm {arm_name!r} executes the canonical {required} slice by "
            f"construction; it cannot be paired with case {spec.case_id!r} "
            "(same-task requirement, C1)"
        )


__all__ = [
    "CaseNotSupportedError",
    "CaseSpec",
    "assert_same_task",
    "default_envelope",
    "load_arm_claim",
    "repo_root",
    "resolve_case",
]
