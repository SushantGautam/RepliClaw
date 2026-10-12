"""Focused checks for the adversarial scientific-audit dataset (RX-441).

Verifies the dataset is well-formed and FAIR:
  * the loader returns distinct, disjoint per-source partitions;
  * no single source contains the full answer (a single source alone is
    insufficient to correctly resolve all claims);
  * ground truth is NOT reachable through the public evidence loader
    (evaluator-only isolation);
  * at least one misleading, one contradictory, and one unreliable artifact
    are present and tagged.
"""
from __future__ import annotations

import json
from pathlib import Path

import repliclaw.benchmarks.adversarial_audit as aa
from repliclaw.benchmarks.adversarial_audit import data as aa_data
from repliclaw.benchmarks.adversarial_audit import ground_truth as gt


def test_loader_returns_distinct_per_source_partitions() -> None:
    sources = aa.source_ids()
    assert len(sources) >= 4, "expected at least 4 named sources"

    all_artifacts = aa.load_evidence()
    assert len(all_artifacts) >= 12, "expected at least 12 evidence artifacts"

    partition_ids: dict[str, set[str]] = {}
    for sid in sources:
        part = aa.evidence_for_source(sid)
        assert part, f"source {sid} has no artifacts"
        ids = {a["artifact_id"] for a in part}
        # every artifact in the partition is actually attributed to this source
        assert all(a["source"] == sid for a in part)
        partition_ids[sid] = ids

    # partitions are pairwise disjoint
    for i, a in enumerate(sources):
        for b in sources[i + 1:]:
            assert partition_ids[a] & partition_ids[b] == set(), (
                f"sources {a} and {b} share artifacts"
            )
    # partitions exactly cover the full evidence set
    union = set().union(*partition_ids.values())
    assert union == {a["artifact_id"] for a in all_artifacts}


def test_no_single_source_contains_the_full_answer() -> None:
    """No one source holds all required (decisive) artifacts for all claims."""
    required = gt.required_artifacts()
    assert required, "ground truth must define required artifacts per claim"

    # sanity: every claim's decisive evidence spans >= 2 sources
    artifact_source = {a["artifact_id"]: a["source"] for a in aa.load_evidence()}
    for claim_id, arts in required.items():
        srcs = {artifact_source[x] for x in arts}
        assert len(srcs) >= 2, f"claim {claim_id} resolvable from a single source {srcs}"

    for sid in aa.source_ids():
        have = {a["artifact_id"] for a in aa.evidence_for_source(sid)}
        resolves_all = all(set(arts) <= have for arts in required.values())
        assert not resolves_all, (
            f"source {sid} alone contains the full answer for every claim"
        )


def test_ground_truth_not_reachable_via_public_loader() -> None:
    # 1) public claim records carry no answer/rationale keys
    for claim in aa.load_claims():
        assert "answer" not in claim
        assert "rationale" not in claim

    # 2) public artifacts carry no evaluator-only fields
    for art in aa.load_evidence():
        for field in ("answer", "rationale", "trap_tags", "required_artifacts"):
            assert field not in art, f"evaluator-only field {field!r} leaked into {art['artifact_id']}"

    # 3) the serialized public surface does not contain any ground-truth
    #    answer or rationale text
    public_blob = json.dumps(
        {
            "claims": aa.load_claims(),
            "evidence": aa.load_evidence(),
            "dataset": aa.load_dataset(),
            "manifest": aa.load_manifest(),
        },
        ensure_ascii=False,
    )
    for record in gt.load_ground_truth()["answers"]:
        assert record["rationale"] not in public_blob, (
            f"ground-truth rationale for {record['claim_id']} leaked into public output"
        )
        assert record["correct_conclusion"] not in public_blob

    # 4) the manifest carries a ground-truth POINTER only, never content
    manifest = aa.load_manifest()
    gtp = manifest["ground_truth"]
    assert "pointer" in gtp and "sha256" in gtp
    assert "answer" not in json.dumps(gtp) and "rationale" not in json.dumps(gtp)

    # 5) structural: the public loader code never names the private dir as a
    #    path component (docstring prose is fine; executable code is not).
    data_src = Path(aa_data.__file__).read_text(encoding="utf-8")
    assert '"private"' not in data_src and "'private'" not in data_src, (
        "public loader must not construct a path into data/private/"
    )
    assert "_PRIVATE_DIR" not in data_src, "public loader must not define a private dir"


def test_misleading_contradictory_unreliable_artifacts_present_and_tagged() -> None:
    ann = {a["artifact_id"]: a for a in gt.load_trap_annotations()["annotations"]}
    # every annotated artifact must exist in the public evidence
    public_ids = {a["artifact_id"] for a in aa.load_evidence()}
    assert set(ann) <= public_ids, "trap annotations reference unknown artifacts"

    tags = {aid: set(a["trap_tags"]) for aid, a in ann.items()}
    assert any("misleading_statistic" in t for t in tags.values()), "no misleading artifact tagged"
    assert any("contradiction" in t for t in tags.values()), "no contradictory artifact tagged"
    assert any("unreliable_source" in t for t in tags.values()), "no unreliable artifact tagged"
    # and there is genuinely supporting evidence too
    assert any("supporting" in t for t in tags.values()), "no supporting artifact tagged"


def test_score_submission_roundtrip() -> None:
    # a perfect (careful cross-referencing) submission scores 1.0
    perfect = gt.answers()
    result = gt.score_submission(perfect)
    assert result["accuracy"] == 1.0 and result["correct"] == result["total"]

    # a naive global-aggregate submission (trust every headline) is penalized
    naive = {"C1": "TRUE", "C2": "FALSE", "C3": "TRUE", "C4": "TRUE",
             "C5": "TRUE", "C6": "TRUE", "C7": "TRUE"}
    naive_result = gt.score_submission(naive)
    assert naive_result["accuracy"] < 0.5, (
        "naive global aggregation should be clearly worse than careful cross-referencing"
    )
