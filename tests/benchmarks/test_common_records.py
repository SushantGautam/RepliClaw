"""Round-trip + validation tests for the shared benchmark record dataclasses.

Deterministic and offline: all timestamps are fixed literals, no git, no
network. Validates the validator itself against known-good and known-bad
payloads (its own schema files are the ground truth).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from repliclaw.benchmarks.common.records import (
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
from repliclaw.benchmarks.common.validation import (
    SCHEMA_FILES,
    has_jsonschema,
    validate_record,
)

SCHEMAS_DIR = Path(__file__).resolve().parents[2] / "src/repliclaw/benchmarks/common/schemas"


def _sample_run_record() -> RunRecord:
    return RunRecord(
        run_id="tox21_ar_agonist::adaptive_manager::seed7",
        arm="adaptive_manager",
        case="tox21_ar_agonist",
        seed=7,
        model="gpt-5.2",
        provider="openai",
        started_at="2026-10-09T10:00:00Z",
        finished_at="2026-10-09T10:04:31Z",
        status="completed",
        token_usage=TokenUsage(input=12000, output=3500, cached=9000, total=15500, usage_present=True, llm_calls=42),
        tool_call_counts={"search": 11, "run_experiment": 4},
        intervention_counts={"abstain": 2, "correct_target": 1},
        wall_s=271.5,
        abort_reason=None,
    )


def _sample_case_manifest() -> CaseManifest:
    return CaseManifest(
        case_id="tox21_ar_agonist",
        source_benchmark="tox21",
        pinned_sha="a" * 40,
        data_hashes={"data/case.json": "b" * 64},
        strata={"toxicity": "active", "source": "reproduced"},
        heldout=True,
        ground_truth=GroundTruthPointer(pointer="oracles/tox21_ar_agonist.json", sha256="c" * 64),
    )


def _sample_provenance() -> Provenance:
    return Provenance(
        run_id="tox21_ar_agonist::adaptive_manager::seed7",
        captured_at="2026-10-09T10:00:01Z",
        repliclaw_git_sha="d" * 40,
        repliclaw_dirty=False,
        dependency_pins={"pydantic": "2.9.0", "repliclaw": "0.1.0"},
        environment=Environment(python_version="3.12.1", platform="macOS-15.0-x86_64", timezone="UTC"),
        upstream_repos={"tox21-upstream": UpstreamRepo(url="https://example.org/tox21", sha="e" * 40)},
        dataset_sha256s={"data/case.json": "b" * 64},
    )


def _sample_scorer_output() -> ScorerOutput:
    return ScorerOutput(
        metric="accuracy",
        value=0.6,
        denominator=5,
        formula_version="accuracy/v1",
        per_case=(
            ScorerCaseRow(case_id="case_a", value=True, eligible=True),
            ScorerCaseRow(case_id="case_b", value=False, eligible=True),
        ),
        numerator=3,
        scored_at="2026-10-09T11:00:00Z",
        run_ids=["r1", "r2"],
    )


# ---------------------------------------------------------------------------
# Schema files are well-formed and self-describe
# ---------------------------------------------------------------------------


def test_schema_files_are_valid_json_and_draft_2020_12():
    for kind, (filename, schema_id) in SCHEMA_FILES.items():
        doc = json.loads((SCHEMAS_DIR / filename).read_text(encoding="utf-8"))
        assert doc["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert doc["$id"] == schema_id


# ---------------------------------------------------------------------------
# Round-trips
# ---------------------------------------------------------------------------


def test_run_record_round_trip_preserves_all_fields():
    rec = _sample_run_record()
    assert rec.to_dict() == RunRecord.from_dict(rec.to_dict()).to_dict()
    # from_dict -> validate must be clean
    assert RunRecord.from_dict(rec.to_dict()).validate().ok


def test_run_record_aborted_round_trip():
    aborted = RunRecord(
        run_id="c::a::seed0",
        arm="a",
        case="c",
        seed=0,
        model="m",
        provider="p",
        started_at="2026-10-09T10:00:00Z",
        finished_at="2026-10-09T10:01:00Z",
        status="aborted_budget",
        token_usage=TokenUsage(input=1, output=2, cached=None, total=3, usage_present=True, llm_calls=1),
        wall_s=60.0,
        abort_reason="token budget exceeded",
    )
    rt = RunRecord.from_dict(aborted.to_dict())
    assert rt.status == "aborted_budget"
    assert rt.abort_reason == "token budget exceeded"
    assert rt.token_usage.cached is None
    assert rt.validate().ok


def test_run_record_completed_requires_null_abort_reason():
    with pytest.raises(ValueError, match="abort_reason"):  # completed + reason set
        RunRecord(
            run_id="c::a::seed0", arm="a", case="c", seed=0, model="m", provider="p",
            started_at="2026-10-09T10:00:00Z", finished_at="2026-10-09T10:01:00Z",
            status="completed", token_usage=TokenUsage(1, 1, None, 2, True), wall_s=1.0,
            abort_reason="boom",
        )
    with pytest.raises(ValueError, match="abort_reason"):
        RunRecord(
            run_id="c::a::seed0", arm="a", case="c", seed=0, model="m", provider="p",
            started_at="2026-10-09T10:00:00Z", finished_at="2026-10-09T10:01:00Z",
            status="aborted_error", token_usage=TokenUsage.absent(1), wall_s=1.0,
            abort_reason=None,
        )


def test_case_manifest_round_trip():
    m = _sample_case_manifest()
    assert m.to_dict() == CaseManifest.from_dict(m.to_dict()).to_dict()
    assert CaseManifest.from_dict(m.to_dict()).validate().ok


def test_provenance_round_trip():
    p = _sample_provenance()
    assert p.to_dict() == Provenance.from_dict(p.to_dict()).to_dict()
    assert Provenance.from_dict(p.to_dict()).validate().ok


def test_scorer_output_round_trip_and_sorting():
    s = _sample_scorer_output()
    assert s.to_dict() == ScorerOutput.from_dict(s.to_dict()).to_dict()
    assert ScorerOutput.from_dict(s.to_dict()).validate().ok
    unsorted = ScorerOutput.from_dict(s.to_dict())
    swapped = [unsorted.per_case[1].to_dict(), unsorted.per_case[0].to_dict()]
    d = s.to_dict()
    d["per_case"] = swapped
    with pytest.raises(ValueError, match="sorted"):
        ScorerOutput.from_dict(d)


def test_token_usage_absent_is_never_zero_filled():
    usage = TokenUsage.absent(llm_calls=3)
    assert usage.to_dict()["input"] is None
    assert usage.to_dict()["usage_present"] is False
    # Zero-filled usage with usage_present=False must be rejected, not accepted.
    with pytest.raises(ValueError, match="never zero-filled"):
        TokenUsage.from_dict(usage.to_dict() | {"input": 0})


def test_schema_string_mismatch_is_rejected():
    d = _sample_run_record().to_dict()
    d["schema"] = "something_else/v9"
    with pytest.raises(ValueError, match="schema string"):
        RunRecord.from_dict(d)


# ---------------------------------------------------------------------------
# The dependency-free validator catches real violations
# ---------------------------------------------------------------------------


def _mutate(d: dict, path: list, value) -> dict:
    node = d
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    return d


def test_validator_rejects_removed_required_field():
    d = _mutate(_sample_run_record().to_dict(), ["token_usage"], None)
    report = validate_record("run_record", d)
    assert not report.ok
    assert any("type" in e.message for e in report.errors)


def test_validator_rejects_unknown_status():
    d = _mutate(_sample_run_record().to_dict(), ["status"], "exploded")
    assert not validate_record("run_record", d).ok


def test_validator_rejects_additional_property():
    d = _sample_run_record().to_dict()
    d["unexpected"] = 1
    report = validate_record("run_record", d)
    assert not report.ok
    assert any("additional" in e.message for e in report.errors)


def test_validator_rejects_bad_run_id_pattern():
    d = _mutate(_sample_run_record().to_dict(), ["run_id"], "no_colon_here")
    assert not validate_record("run_record", d).ok


def test_validator_rejects_zero_filled_usage_when_usage_absent():
    d = _sample_run_record().to_dict()
    d["token_usage"] = {"input": 5, "output": 0, "cached": None, "total": 5, "usage_present": False, "llm_calls": 1}
    report = validate_record("run_record", d)
    assert not report.ok


def test_validator_rejects_aborted_status_with_absent_abort_reason():
    # J-CODE F4 (Wave 0): raw-schema path must reject an aborted run whose
    # abort_reason key is missing entirely, not only when it is null.
    d = _sample_run_record().to_dict()
    d["status"] = "aborted_budget"
    del d["abort_reason"]
    assert not validate_record("run_record", d).ok


def test_validator_rejects_usage_present_false_with_zero_filled_numerics():
    # J-CODE F5 (Wave 0): the never-zero-fill rule must hold at the schema
    # level (raw-JSON path), not only in the dataclass.
    d = _sample_run_record().to_dict()
    d["token_usage"] = {
        "input": 0, "output": 0, "cached": 0, "total": 0,
        "usage_present": False, "llm_calls": 1,
    }
    assert not validate_record("run_record", d).ok


def test_validator_rejects_usage_present_true_with_string_numerics():
    d = _sample_run_record().to_dict()
    d["token_usage"] = {"input": "5", "output": 0, "cached": 0, "total": 5, "usage_present": True, "llm_calls": 1}
    assert not validate_record("run_record", d).ok


def test_validator_accepts_usage_present_true_with_integers():
    d = _sample_run_record().to_dict()
    report = validate_record("run_record", d)
    assert report.ok, report.errors


def test_validator_rejects_non_zulu_timestamp():
    d = _mutate(_sample_run_record().to_dict(), ["started_at"], "2026-10-09 10:00:00+02:00")
    assert not validate_record("run_record", d).ok


def test_validator_rejects_non_integer_tool_counts():
    d = _sample_run_record().to_dict()
    d["tool_call_counts"] = {"search": "eleven"}
    assert not validate_record("run_record", d).ok


def test_validator_rejects_case_manifest_bad_hash():
    d = _sample_case_manifest().to_dict()
    d["data_hashes"]["data/case.json"] = "xyz"
    assert not validate_record("case_manifest", d).ok


def test_validator_rejects_scorer_bad_metric_name():
    d = _mutate(_sample_scorer_output().to_dict(), ["metric"], "Bad-Metric")
    assert not validate_record("scorer_output", d).ok


def test_validator_rejects_provenance_non_40hex_git_sha():
    d = _mutate(_sample_provenance().to_dict(), ["repliclaw_git_sha"], "unknown")
    assert not validate_record("provenance", d).ok


def test_unknown_kind_raises():
    with pytest.raises(KeyError):
        validate_record("nonsense", {})


def test_has_jsonschema_reports_env_truthfully():
    # The Stage-2 venv has no jsonschema installed; the fallback is used.
    # Whatever the environment, the flag must be a bool consistent with import.
    assert isinstance(has_jsonschema(), bool)
    if has_jsonschema():
        import jsonschema  # noqa: F401
