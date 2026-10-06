"""J-SCI C-SCI-1 (S1 residual): scorer-only ground-truth access gate.

Pins the hard access gate:
  a. ``ScorerContext.resolve`` returns the correct label from a synthetic
     index (synthetic service names — NO real RCAEval ground-truth rows in
     this test source, so the test itself is not a label-peek surface);
  b. every resolve is recorded in the context's audit log;
  c. ``assert_no_agent_access`` raises on a leaked label and passes when
     absent;
  d. static caller-restriction scan: only the documented allowed-caller set
     may reference the resolve path inside ``src/repliclaw/``;
  e. ``CaseManifest`` round-trip still carries the pointer only — never the
     ground-truth content.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from repliclaw.benchmarks.common.gating import (
    GroundTruthLeakError,
    ScorerContext,
    assert_no_agent_access,
)
from repliclaw.benchmarks.common.records import CaseManifest, GroundTruthPointer
from repliclaw.benchmarks.rcaeval import manifest as rcaeval_manifest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src" / "repliclaw"

# Synthetic ground-truth values. Deliberately NOT real RCAEval service names,
# so no label value from the actual dataset appears anywhere in this module.
SYN_LABELS = {"alpha_svc": "svc_alpha", "beta_svc": "svc_beta"}


def _synthetic_index() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "case": ["alpha_svc", "beta_svc"],
            "root_cause_service": ["svc_alpha", "svc_beta"],
        }
    )


def test_resolve_returns_label_from_synthetic_index() -> None:
    scorer = ScorerContext(index=_synthetic_index(), label_column="root_cause_service")
    assert scorer.resolve("alpha_svc") == "svc_alpha"
    assert scorer.resolve("beta_svc", caller_tag="unit_test") == "svc_beta"
    with pytest.raises(KeyError):
        scorer.resolve("not_a_case")


def test_resolve_is_audited() -> None:
    ticks = iter(
        [
            "2026-10-10T00:00:00+00:00",
            "2026-10-10T00:00:01+00:00",
            "2026-10-10T00:00:02+00:00",
            "2026-10-10T00:00:03+00:00",
        ]
    )
    scorer = ScorerContext(
        index=_synthetic_index(),
        label_column="root_cause_service",
        clock=lambda: next(ticks),
    )
    assert scorer.audit == []
    scorer.resolve("alpha_svc", caller_tag="tag_a")
    scorer.resolve("beta_svc", caller_tag="tag_b")
    assert [(e.case_id, e.timestamp, e.caller) for e in scorer.audit] == [
        ("alpha_svc", "2026-10-10T00:00:00+00:00", "tag_a"),
        ("beta_svc", "2026-10-10T00:00:01+00:00", "tag_b"),
    ]
    # resolve_many audits each id individually
    scorer.resolve_many(["alpha_svc", "alpha_svc"], caller_tag="batch")
    assert len(scorer.audit) == 4
    assert [e.caller for e in scorer.audit[-2:]] == ["batch", "batch"]


def test_heldout_ground_truth_goes_through_scorer_context() -> None:
    # The RCAEval evaluator-only helper resolves through the same audited path.
    label = rcaeval_manifest.heldout_ground_truth("alpha_svc", _synthetic_index())
    assert label == "svc_alpha"


def test_canary_raises_on_leak_and_passes_when_absent(tmp_path: Path) -> None:
    clean = tmp_path / "agent_report.txt"
    clean.write_text("diagnosis: the incident looks like a cache storm\n", encoding="utf-8")
    assert_no_agent_access([clean], expected_labels=SYN_LABELS.values())

    leaked = tmp_path / "agent_notes.txt"
    leaked.write_text("hypothesis: svc_alpha is the root cause\n", encoding="utf-8")
    with pytest.raises(GroundTruthLeakError, match="svc_alpha"):
        assert_no_agent_access([clean, leaked], expected_labels=SYN_LABELS.values())

    # Missing artifact files are skipped, not errors; empty label set is a no-op.
    assert_no_agent_access([tmp_path / "missing.txt"], expected_labels=SYN_LABELS.values())
    assert_no_agent_access([clean], expected_labels=())


def test_static_caller_restriction_scan() -> None:
    """Only the allowed-caller set may reference the ground-truth resolve path.

    Allowed callers inside ``src/repliclaw/`` (documented here as required by
    C-SCI-1):
      * ``benchmarks/common/gating.py`` — the gate itself (ScorerContext
        definition, the ONLY sanctioned reader);
      * ``benchmarks/rcaeval/manifest.py`` — the evaluator-only wrapper
        ``heldout_ground_truth`` (imports ScorerContext; never exposed via
        the package ``__init__``).
    Everything else under ``src/repliclaw/`` — in particular all
    agent/lane-facing modules — must not mention the resolve path at all.
    Test code (``tests/``) is excluded from the scan by construction.
    """
    resolve_path_refs = re.compile(r"\b(heldout_ground_truth|ScorerContext|assert_no_agent_access)\b")
    allowed = {
        SRC_ROOT / "benchmarks" / "common" / "gating.py",
        SRC_ROOT / "benchmarks" / "rcaeval" / "manifest.py",
    }
    offenders: list[tuple[Path, int, str]] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        if path in allowed:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if resolve_path_refs.search(line):
                offenders.append((path, lineno, line.strip()))
    assert offenders == [], f"agent-side code references the ground-truth resolve path: {offenders}"

    # The wrapper must NOT be exported through the public package surface —
    # evaluators import it directly from the module.
    pkg_init = (SRC_ROOT / "benchmarks" / "rcaeval" / "__init__.py").read_text(encoding="utf-8")
    assert "heldout_ground_truth" not in pkg_init, "heldout_ground_truth must stay non-exported"


def test_case_manifest_roundtrip_contains_pointer_only() -> None:
    manifest = CaseManifest(
        case_id="synthetic_case_1",
        source_benchmark="synthetic",
        pinned_sha="a" * 40,
        data_hashes={"metrics.parquet": "b" * 64},
        strata={"suite": "SX"},
        heldout=True,
        ground_truth=GroundTruthPointer(
            pointer="hf://example/synthetic/cases.parquet#case=synthetic_case_1",
            sha256="c" * 64,
        ),
    )
    wire = manifest.to_dict()
    assert wire["ground_truth"] == {
        "pointer": "hf://example/synthetic/cases.parquet#case=synthetic_case_1",
        "sha256": "c" * 64,
    }
    assert "svc_alpha" not in str(wire), "resolved label must never be embedded in the manifest"
    assert "svc_beta" not in str(wire)

    restored = CaseManifest.from_dict(wire)
    assert restored == manifest
    assert isinstance(restored.ground_truth, GroundTruthPointer)
    assert restored.ground_truth.pointer == manifest.ground_truth.pointer
    assert restored.validate().ok
