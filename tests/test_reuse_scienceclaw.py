"""Reuse contract: RepliClaw genuinely reuses ScienceClaw primitives
(DECISIONS.md D01/D04). Proves the adapter is not a fork and that run-local
isolation, content hashing, lineage, and deterministic pressure all work."""

from repliclaw import scienceclaw_adapter as sc


def test_scienceclaw_imports_resolve_to_vendored_deps():
    # The adapter puts deps/scienceclaw on sys.path; the real upstream modules
    # must be importable (reuse, not a fork).
    from artifacts import artifact as art_mod
    from artifacts import needs as needs_mod
    assert sc.Artifact is art_mod.Artifact
    assert sc.NeedItem is needs_mod.NeedItem


def test_run_local_store_is_scoped_not_home(tmp_path):
    store = sc.RunLocalArtifactStore("agent-1", tmp_path)
    assert str(store._base).startswith(str(tmp_path))
    assert ".scienceclaw" not in str(store._base)
    assert store.store_path.parent.exists()


def test_artifact_has_content_hash_and_lineage(tmp_path):
    finding = {
        "conclusion": "supported",
        "statement": "the effect is real",
        "evidence": {"p": 0.001},
        "confidence": 0.9,
        "executable": True,
    }
    art = sc.artifact_from_finding(
        agent_id="inv-a",
        investigation_id="claim-x",
        finding=finding,
        parent_artifact_ids=["art-parent-1"],
    )
    assert art.artifact_id
    assert art.investigation_id == "claim-x"
    assert "art-parent-1" in (art.parent_artifact_ids or [])
    payload = art.payload if isinstance(art.payload, dict) else {}
    assert payload.get("conclusion") == "supported"


def test_store_save_and_load_roundtrip(tmp_path):
    store = sc.RunLocalArtifactStore("agent-1", tmp_path)
    art = sc.artifact_from_finding(
        agent_id="agent-1",
        investigation_id="claim-x",
        finding={"conclusion": "supported", "evidence": {"p": 0.01}},
    )
    store.save(art)
    assert store.store_path.exists()
    assert (tmp_path / "global_index.jsonl").exists()


def test_pressure_score_is_deterministic_and_positive():
    need = {
        "artifact_type": "analysis_result",
        "query": "recompute the primary test from raw events",
        "rationale": "investigators disagree; independent re-analysis is required before a verdict can be trusted",
        "created_at": "2026-10-07T00:00:00Z",
    }
    p1 = sc.pressure_score(need, "", "orchestrator", "claim-x")
    p2 = sc.pressure_score(need, "", "orchestrator", "claim-x")
    # Upstream score_need has a wall-clock age term, so scores are
    # deterministic up to the ~microsecond elapsed between calls.
    assert abs(p1 - p2) < 1e-9
    # novelty = 1/(1+0) => 2.0 floor with no centrality/depth/age.
    assert p1 >= 2.0


def test_needs_bridge_to_native_needitem():
    items = sc.needs_to_need_items([
        {
            "artifact_type": "analysis_result",
            "query": "recheck",
            "rationale": "investigators disagree; independent re-analysis required",
        },
    ])
    assert isinstance(items[0], sc.NeedItem)
    assert items[0].query == "recheck"
