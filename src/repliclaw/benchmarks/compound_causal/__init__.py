"""CompoundCausal-32: exploratory synthetic active causal diagnosis benchmark.

Public interfaces expose noisy observations and *executed simulator* outcomes.
Hidden worlds and scoring MUST run in a trusted separate process for blind studies.
This is not a real-world intervention benchmark.
"""
from .core import (
    FACTORS,
    MAX_EXPERIMENTS,
    BenchmarkSession,
    generate_dataset,
    load_dataset,
    score_predictions,
)

__all__ = [
    "FACTORS",
    "MAX_EXPERIMENTS",
    "BenchmarkSession",
    "generate_dataset",
    "load_dataset",
    "score_predictions",
]
