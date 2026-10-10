"""G2 leak canaries (Stage-2, W2a) — RCAEval side of the G2 gate, unblocked by
the S1 remediation (J-CODE W1 F1 / J-SCI W1 S1, C-SCI-1): the heldout manifest
is now the artifact the leak canary scans.

For every one of the 42 heldout CANDIDATE manifests built from the pinned
``data/cases.parquet``:

(a) no ground-truth service name (``root_cause_service``) appears in any
    agent-visible manifest field (``strata`` / ``notes`` / ``source_benchmark``);
(b) the ground-truth pointer is a URI (scheme-qualified) and never an
    existing in-repo file path — the pointer must stay evaluator-side;
(c) the upstream case-id service-embedding fact + the opaque-id runtime
    requirement are documented — pinned against
    ``case_manifest.schema.json`` (present) and, as a G2 hardening, against
    the ``rcaeval/manifest.py`` module docstring (currently absent — pinned
    by a strict xfail so the gap stays visible until it is closed).

Offline: reads only the pinned index and the in-repo schema file. No LLM,
no network, no ground-truth content is copied anywhere.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from repliclaw.benchmarks.rcaeval import (
    build_heldout_manifest,
    select_heldout_cases,
)
from repliclaw.benchmarks.rcaeval import manifest as rca_manifest

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA = REPO_ROOT / "data" / "cases.parquet"
SCHEMA = REPO_ROOT / "src" / "repliclaw" / "benchmarks" / "common" / "schemas" / "case_manifest.schema.json"

EXPECTED_TOTAL = 42
_URI_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")


@pytest.fixture(scope="module")
def index() -> pd.DataFrame:
    assert DATA.exists(), f"fixture {DATA} missing — copy the pinned cases.parquet"
    return pd.read_parquet(DATA)


@pytest.fixture(scope="module")
def manifests(index: pd.DataFrame):
    cases = select_heldout_cases(index)
    assert len(cases) == EXPECTED_TOTAL, f"heldout candidate count drifted: {len(cases)}"
    data_hashes = {c: {"metrics.parquet": "0" * 64} for c in cases}
    return build_heldout_manifest(index, data_hashes)


def test_all_42_heldout_manifests_are_leak_free(index: pd.DataFrame, manifests) -> None:
    """(a) + (b): for EVERY heldout candidate manifest:

    * no ground-truth service name (full index vocabulary of
      ``root_cause_service`` values) occurs in strata, notes, or
      source_benchmark — the agent-visible surface is label-free;
    * the ground-truth pointer exists, is a URI (scheme-qualified), and is
      never an existing in-repo file path (evaluator-side locator only).

    Documented residual (S1): the default pointer
    ``hf://phamquiluan/RCAEval/cases.parquet#case=<upstream_id>`` names the
    upstream case id, which itself embeds the root-cause service — the
    upstream-identifiers limitation the schema note records. It is a
    pointer, not ground-truth content, and the runtime requirement (opaque
    case ids for agents) covers the serving surface; the scorer-only access
    gate at G4 covers the pointer surface.
    """
    assert len(manifests) == EXPECTED_TOTAL
    service_names = {str(s) for s in index["root_cause_service"].astype(str)}
    service_names.discard("")

    for m in manifests:
        visible = {
            "strata": str(m.strata),
            "notes": m.notes or "",
            "source_benchmark": m.source_benchmark,
        }
        for field, text in visible.items():
            leaked = sorted(svc for svc in service_names if svc in text)
            assert not leaked, f"{m.case_id}: ground-truth service(s) {leaked} in {field}"

        gt = m.ground_truth
        assert gt is not None, f"{m.case_id}: ground-truth pointer missing"
        pointer = gt.pointer
        assert _URI_RE.match(pointer), f"{m.case_id}: pointer is not a URI: {pointer!r}"
        # URI scheme must not be a file-system reference into the repo.
        assert not pointer.startswith("file://"), f"{m.case_id}: file:// pointer: {pointer!r}"
        # Defense in depth: even if a scheme ever regressed, a pointer that
        # resolves to an existing in-repo file is a leak surface.
        candidate = REPO_ROOT / pointer
        assert not candidate.exists(), f"{m.case_id}: pointer resolves in-repo: {pointer!r}"


def test_schema_documents_case_id_service_embedding_and_opaque_id() -> None:
    """(c, present): the schema's ``case_id`` description carries the
    upstream fact (case ids embed the root-cause service) and the runtime
    requirement (agents get opaque random ids; the upstream id stays
    evaluator-side)."""
    import json

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    case_id_desc = schema["properties"]["case_id"]["description"].lower()
    assert "embed" in case_id_desc, "schema case_id note must document the service-embedding fact"
    assert "opaque" in case_id_desc, "schema case_id note must document the opaque-id runtime requirement"
    assert "evaluator" in case_id_desc
    # The ground-truth field stays content-free by schema contract.
    gt_desc = schema["properties"]["ground_truth"]["description"].lower()
    assert "evaluator-only" in gt_desc


@pytest.mark.xfail(
    strict=True,
    reason=(
        "G2 canary vs ACTUAL behavior: rcaeval/manifest.py's MODULE docstring "
        "does not document the upstream case-id service-embedding fact or the "
        "opaque-id runtime requirement — that documentation currently lives "
        "only in case_manifest.schema.json (case_id note) and in the "
        "test_manifest_strata_leak_free test docstring. J-SCI W1 S1 / J-CODE "
        "W1 F1 make the fact load-bearing for the G2 gate, so pinning it in "
        "the module that BUILDS the manifests is the G2 hardening this canary "
        "tracks. If this xfail ever PASSES, the docstring was closed — keep "
        "the test, drop the xfail."
    ),
)
def test_module_docstring_documents_case_id_service_embedding() -> None:
    doc = (rca_manifest.__doc__ or "").lower()
    assert "embed" in doc, "module docstring must document the upstream case-id service-embedding fact"
    assert "opaque" in doc, "module docstring must document the opaque-id runtime requirement"
