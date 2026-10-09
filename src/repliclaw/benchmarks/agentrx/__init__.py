"""AgentRx read-only benchmark adapter (observational track O-A).

Loads the pinned ``microsoft/AgentRx`` dataset (4 JSONL files, sha256-verified),
exposes the 10-category taxonomy pinned to agentrx@7a18c797, builds the 73-case
eval-set manifest, and scores external (prediction, case) pairs against the
official AgentRx metric schema. No LLM, no judge, no execution, no causal
intervention — see ``README.md`` in this package.
"""
from .loader import (
    AgentRxCASE,
    AgentRxEvalSet,
    AnnotatedFailure,
    DatasetHashMismatchError,
    DatasetLoadError,
    RootCause,
    TrajectoryStep,
    load_agentrx_eval_set,
)
from .manifest import AgentRxManifestSet, assign_heldout_split, build_eval_set_manifests
from .scoring import Prediction, predict_and_score, score_case, score_predictions
from .taxonomy import FailureCase, category_code, normalize_category

__all__ = [
    "AgentRxCASE",
    "AgentRxEvalSet",
    "AgentRxManifestSet",
    "AnnotatedFailure",
    "DatasetHashMismatchError",
    "DatasetLoadError",
    "FailureCase",
    "Prediction",
    "RootCause",
    "TrajectoryStep",
    "assign_heldout_split",
    "build_eval_set_manifests",
    "category_code",
    "load_agentrx_eval_set",
    "normalize_category",
    "predict_and_score",
    "score_case",
    "score_predictions",
]
