"""Shared infrastructure for all benchmark lanes (Stage 2).

Modules:
    records      -- dataclasses round-tripping with the JSON Schemas in schemas/
    validation   -- dependency-free draft-2020-12 subset validator
    provenance   -- capture / verify run provenance
    resume       -- idempotent, atomic run-state helper
"""
from .provenance import ProvenanceError, capture_provenance, verify_provenance
from .records import (
    CASE_MANIFEST_SCHEMA,
    PROVENANCE_SCHEMA,
    RUN_RECORD_SCHEMA,
    RUN_STATUSES,
    SCORER_OUTPUT_SCHEMA,
    CaseManifest,
    Environment,
    GroundTruthPointer,
    Provenance,
    RunRecord,
    ScorerCaseRow,
    ScorerOutput,
    TokenUsage,
    UpstreamRepo,
)
from .resume import RunState, RunStateError, run_id_for
from .validation import (
    SCHEMA_FILES,
    ValidationError,
    ValidationReport,
    canonical_payload_sha256,
    has_jsonschema,
    validate,
    validate_record,
)

__all__ = [
    "CASE_MANIFEST_SCHEMA",
    "PROVENANCE_SCHEMA",
    "RUN_RECORD_SCHEMA",
    "SCORER_OUTPUT_SCHEMA",
    "RUN_STATUSES",
    "CaseManifest",
    "Environment",
    "GroundTruthPointer",
    "Provenance",
    "RunRecord",
    "ScorerCaseRow",
    "ScorerOutput",
    "TokenUsage",
    "UpstreamRepo",
    "SCHEMA_FILES",
    "ValidationError",
    "ValidationReport",
    "canonical_payload_sha256",
    "has_jsonschema",
    "validate",
    "validate_record",
    "ProvenanceError",
    "capture_provenance",
    "verify_provenance",
    "RunState",
    "RunStateError",
    "run_id_for",
]
