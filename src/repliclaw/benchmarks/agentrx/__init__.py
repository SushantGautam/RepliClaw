"""AgentRx read-only benchmark adapter (observational track O-A).

Loads the pinned ``microsoft/AgentRx`` dataset (4 JSONL files, sha256-verified),
exposes the 10-category taxonomy pinned to agentrx@7a18c797, builds the 73-case
eval-set manifest, and scores external (prediction, case) pairs against the
official AgentRx metric schema. No LLM, no judge, no execution, no causal
intervention — see ``README.md`` in this package.

Also hosts the D-V3-010-authorized SimulaChat OpenAI-compatible client
(:mod:`.simula`) and the read-only runtime patch that wires it into
AgentRx@7a18c797 (:mod:`.agentrx_patch`) — a **model-substitution**
baseline, never the official AgentRx baseline.
"""
from .agentrx_patch import (
    CALLS_SERVED,
    SimulaPatchState,
    apply_simula_patch,
    stamp_model_substitution_metadata,
)
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
from .simula import (
    MODEL_SUBSTITUTION_LABEL,
    SimulaChatClient,
    SimulaChatConfig,
    SimulaChatMissingEnvError,
    load_config,
    simula_mk_client,
)
from .simula import (
    LLMAgent as SimulaLLMAgent,
)
from .taxonomy import FailureCase, category_code, normalize_category

__all__ = [
    "MODEL_SUBSTITUTION_LABEL",
    "SimulaChatClient",
    "SimulaChatConfig",
    "SimulaChatMissingEnvError",
    "SimulaLLMAgent",
    "SimulaPatchState",
    "apply_simula_patch",
    "load_config",
    "simula_mk_client",
    "stamp_model_substitution_metadata",
    "CALLS_SERVED",
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
