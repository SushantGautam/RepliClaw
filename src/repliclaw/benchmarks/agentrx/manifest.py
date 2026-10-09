"""Eval-set manifest for the AgentRx read-only adapter (73 cases).

One :class:`CaseManifest` per annotated trajectory, using the shared
``repliclaw.benchmarks.common.records`` types so every case pins the same
upstream bytes and strata. ``ground_truth`` is a pointer-only record (path +
sha256 of the annotated file) — the scorer is the only consumer allowed to
dereference it.

Heldout split rule (documented, deterministic, label-free):
  stratified 50/50 by domain, seed 20261009. Within each domain, cases are
  ordered by ``case_id`` (locale-independent string sort), and every 2nd case
  in that order is assigned to the heldout half. Assignment depends only on
  case_id and domain strata — never on annotation labels, categories, or any
  outcome field. All 73 manifests carry ``heldout=False`` by default; the
  split is a *rule* to be applied when a heldout split is actually consumed,
  and :func:`assign_heldout_split` implements it for auditability.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Set, Tuple

from ..common.records import CaseManifest, GroundTruthPointer
from .loader import (
    DOMAIN_MAGENTIC,
    DOMAIN_TAU,
    PINNED_FILES,
    PINNED_REPO_SHA,
    AgentRxCASE,
    AgentRxEvalSet,
)

SOURCE_BENCHMARK = "agentrx"

#: Data directory the pinned files were verified against (see loader).
#: Declared salt for the split rule (20261009). The rule below is pure
#: order-based (case_id sort + every-2nd selection) and does not consume RNG,
#: so the seed is recorded for auditability only — a future rule variant
#: seeded on this value must re-derive from it explicitly.
HOLDOUT_SEED = 20261009
HOLDOUT_FRACTION = 0.5

#: Annotated ground-truth files (pointer-only targets for ground_truth).
GT_FILES = {DOMAIN_TAU: "tau_retail.jsonl", DOMAIN_MAGENTIC: "magentic_one.jsonl"}


def assign_heldout_split(cases: Sequence[AgentRxCASE]) -> Set[str]:
    """Return the set of case_ids in the heldout half under the documented rule.

    Rule: stratify by domain; within each domain sort by case_id; take every
    2nd case (indices 1, 3, 5, …) as heldout. Label-free: depends only on
    case_id and the domain stratum. With 29 tau + 44 magentic this yields
    14 + 22 = 36 heldout cases.
    """
    heldout: Set[str] = set()
    for domain in (DOMAIN_TAU, DOMAIN_MAGENTIC):
        ordered = sorted(c.case_id for c in cases if c.domain == domain)
        heldout.update(ordered[1::2])
    return heldout


@dataclass(frozen=True)
class AgentRxManifestSet:
    manifests: Tuple[CaseManifest, ...]
    data_hashes: Dict[str, str]
    unannotated_excluded_ids: Tuple[str, ...]

    @property
    def n_cases(self) -> int:
        return len(self.manifests)


def build_eval_set_manifests(eval_set: AgentRxEvalSet, heldout_split: bool = False) -> AgentRxManifestSet:
    """Build the 73 CaseManifest records from a loaded eval set.

    ``heldout_split=False`` (default) marks every case ``heldout=False``;
    ``heldout_split=True`` applies :func:`assign_heldout_split`.
    """
    heldout_ids = assign_heldout_split(eval_set.cases) if heldout_split else set()
    manifests: List[CaseManifest] = []
    for case in eval_set.cases:
        gt_file = GT_FILES[case.domain]
        manifests.append(
            CaseManifest(
                case_id=case.case_id,
                source_benchmark=SOURCE_BENCHMARK,
                pinned_sha=PINNED_REPO_SHA,
                data_hashes={name: eval_set.data_hashes[name] for name in PINNED_FILES},
                strata={"domain": case.domain, "benchmark": "agentrx"},
                heldout=(case.case_id in heldout_ids),
                ground_truth=GroundTruthPointer(
                    pointer=f"huggingface://microsoft/AgentRx/{gt_file}",
                    sha256=eval_set.data_hashes[gt_file],
                ),
                notes="Observational trace; 14 unannotated raw magentic trajectories excluded from eval set.",
            )
        )
    return AgentRxManifestSet(
        manifests=tuple(manifests),
        data_hashes=dict(eval_set.data_hashes),
        unannotated_excluded_ids=tuple(eval_set.unannotated_magentic_ids),
    )


__all__ = [
    "AgentRxManifestSet",
    "GT_FILES",
    "HOLDOUT_FRACTION",
    "HOLDOUT_SEED",
    "SOURCE_BENCHMARK",
    "assign_heldout_split",
    "build_eval_set_manifests",
]
