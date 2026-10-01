"""P02 — frozen SimpleAudit counterfactual intervention (public API, contract §5).

This package turns the controlled returns-policy RAG hero case into the FIRST
executable, reproducible counterfactual AI-failure experiment: independent
one-factor arms run through the REAL SimpleAudit engine, each producing a
byte-deterministic, replay-verifiable artifact set.
"""
from __future__ import annotations

from repliclaw.counterfactual.case import (
    ALL_FACTORS,
    CaseSpec,
    InterventionSpec,
    canonical_bytes,
    sha256_bytes,
)
from repliclaw.counterfactual.executor import (
    ARM_FILES,
    InterventionRun,
    SimpleAuditExecutor,
    engine_metadata,
    load_case,
    load_interventions,
    persist_arm,
    replay,
    run_canonical,
    run_case,
    write_case_manifest,
)
from repliclaw.counterfactual.frozen_backend import extract_window_days

__all__ = [
    "ALL_FACTORS",
    "ARM_FILES",
    "CaseSpec",
    "InterventionRun",
    "InterventionSpec",
    "SimpleAuditExecutor",
    "canonical_bytes",
    "engine_metadata",
    "extract_window_days",
    "load_case",
    "load_interventions",
    "persist_arm",
    "replay",
    "run_canonical",
    "run_case",
    "sha256_bytes",
    "write_case_manifest",
]
