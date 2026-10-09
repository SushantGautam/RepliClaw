"""Tests for the AgentRx offline scorer (micro-fixture with hand-computed metrics).

Micro-fixture (4 cases, hand-computed):

  case            gt_cat  gt_step  pred_cat  pred_steps   => cat_ok  step_mean  exact  ±1  ±2
  m1              1       3        1         (3, 4)       => yes     3.5->4     no     no   yes
  m2              2       5        3         (6, 6)       => no      6.0->6     no     yes  yes
  m3              8       10       8         ()           => yes     n/a        n/a    n/a  n/a
  m4              7       2        0         (10)         => no      10.0->10   no     no   no

Expected (official denominators: Correct+Incorrect for category; cases with
>=1 step prediction for step metrics):
  root_cause.category_accuracy        = 2/4  = 0.5
  step_number.accuracy                = 0/3  = 0.0
  step_number.accuracy_within_pm1     = 1/3  (m2 only: |6-5|=1)
  step_number.accuracy_within_pm2     = 2/3  (m1 |4-3|=1, m2)
  step_number.accuracy_within_pm3..5  = 2/3  (m4 distance 8, never in range)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from repliclaw.benchmarks.agentrx.loader import AgentRxCASE, AnnotatedFailure, RootCause, TrajectoryStep
from repliclaw.benchmarks.agentrx.manifest import assign_heldout_split, build_eval_set_manifests
from repliclaw.benchmarks.agentrx.scoring import Prediction, score_predictions
from repliclaw.benchmarks.common.validation import validate_record

DATA_DIR = Path("/Users/sushantgautam/Documents/stg2-worktrees/agentrx-data")


def _mk_case(case_id: str, domain: str, gt_cat: int, gt_step: int, gt_label: str, n_steps: int = 12) -> AgentRxCASE:
    return AgentRxCASE(
        case_id=case_id,
        domain=domain,
        instruction=f"instruction for {case_id}",
        steps=tuple(TrajectoryStep(index=i, substeps=[]) for i in range(1, n_steps + 1)),
        failures=(
            AnnotatedFailure(
                failure_id="1",
                step_number=gt_step,
                step_reason="r",
                failure_category=gt_label,
                category_reason="c",
                failed_agent="Assistant",
            ),
        ),
        root_cause=RootCause(
            failure_id="1", reason="rc", step_number=gt_step, category=gt_label, category_code=gt_cat
        ),
        failure_summary="s",
        raw_trajectory_id=case_id,
    )


FIXTURE_CASES = (
    _mk_case("m1", "tau_retail", 1, 3, "Instruction Adherence Failure"),
    _mk_case("m2", "tau_retail", 2, 5, "Invention of New Information"),
    _mk_case("m3", "magentic_one", 8, 10, "Guardrails Triggered"),
    _mk_case("m4", "magentic_one", 7, 2, "Intent Not Supported"),
)

FIXTURE_PREDICTIONS = (
    Prediction(case_id="m1", failure_case=1, step_numbers=(3, 4), run_id="run-x"),
    Prediction(case_id="m2", failure_case=3, step_numbers=(6, 6), run_id="run-x"),
    Prediction(case_id="m3", failure_case=8, step_numbers=(), run_id="run-x"),
    Prediction(case_id="m4", failure_case=0, step_numbers=(10,), run_id="run-x"),
)


def test_micro_fixture_metric_math():
    out = score_predictions(FIXTURE_CASES, FIXTURE_PREDICTIONS)

    cat = out["root_cause.category_accuracy"]
    assert cat.value == 0.5
    assert cat.denominator == 4
    assert cat.numerator == 2

    step_exact = out["step_number.accuracy"]
    assert step_exact.value == 0.0
    assert step_exact.denominator == 3  # m3 has no step predictions

    assert out["step_number.accuracy_within_pm1"].value == pytest.approx(2 / 3)
    assert out["step_number.accuracy_within_pm2"].value == pytest.approx(2 / 3)
    assert out["step_number.accuracy_within_pm3"].value == pytest.approx(2 / 3)
    assert out["step_number.accuracy_within_pm4"].value == pytest.approx(2 / 3)
    assert out["step_number.accuracy_within_pm5"].value == pytest.approx(2 / 3)

    # per-case table is the authoritative record
    rows = {r.case_id: r.value for r in cat.per_case}
    assert rows == {"m1": True, "m2": False, "m3": True, "m4": False}
    step_rows = {r.case_id: (r.value, r.eligible) for r in step_exact.per_case}
    assert step_rows == {"m1": (False, True), "m2": (False, True), "m3": (False, False), "m4": (False, True)}
    assert out["root_cause.category_accuracy"].run_ids == ("run-x",)


def test_predictions_must_match_cases():
    with pytest.raises(ValueError, match="unknown case_id"):
        score_predictions(FIXTURE_CASES, [Prediction(case_id="nope", failure_case=1)])


def test_all_correct_prediction_gives_one():
    preds = tuple(
        Prediction(
            case_id=c.case_id,
            failure_case=c.root_cause.category_code,
            step_numbers=(c.root_cause.step_number,),
        )
        for c in FIXTURE_CASES
    )
    out = score_predictions(FIXTURE_CASES, preds)
    assert out["root_cause.category_accuracy"].value == 1.0
    assert out["step_number.accuracy"].value == 1.0
    for t in range(1, 6):
        assert out[f"step_number.accuracy_within_pm{t}"].value == 1.0


@pytest.mark.skipif(not DATA_DIR.is_dir(), reason="pinned agentrx-data not present")
def test_manifest_split_rule_deterministic_and_label_free():
    from repliclaw.benchmarks.agentrx.loader import load_agentrx_eval_set

    es = load_agentrx_eval_set(DATA_DIR)
    from repliclaw.benchmarks.agentrx.loader import AgentRxEvalSet

    heldout = assign_heldout_split(es.cases)
    # rule: every 2nd case by case_id within each domain
    for domain in ("tau_retail", "magentic_one"):
        ordered = sorted(c.case_id for c in es.cases if c.domain == domain)
        assert heldout & {c.case_id for c in es.cases if c.domain == domain} == set(ordered[1::2])
    assert len(heldout) == 14 + 22  # 29 -> 14, 44 -> 22
    # deterministic: same input -> same output, regardless of input order
    assert assign_heldout_split(list(reversed(es.cases))) == heldout

    default = build_eval_set_manifests(es)
    assert default.n_cases == 73
    assert all(not m.heldout for m in default.manifests)
    for m in default.manifests:
        m.validate()
        assert m.source_benchmark == "agentrx"
        assert m.pinned_sha.startswith("7a18c797")
        assert m.strata["domain"] in ("tau_retail", "magentic_one")
        assert m.ground_truth is not None and "microsoft/AgentRx" in m.ground_truth.pointer
        assert len(m.data_hashes) == 4

    split = build_eval_set_manifests(es, heldout_split=True)
    assert sum(1 for m in split.manifests if m.heldout) == 36
    # label-free: same split regardless of category labels on cases
    relabeled = AgentRxEvalSet(
        cases=tuple(
            AgentRxCASE(
                c.case_id,
                c.domain,
                c.instruction,
                c.steps,
                c.failures,
                RootCause(c.root_cause.failure_id, "x", c.root_cause.step_number, "Shuffled Label", 9),
                c.failure_summary,
                c.raw_trajectory_id,
            )
            for c in es.cases
        ),
        data_hashes=es.data_hashes,
        unannotated_magentic_ids=es.unannotated_magentic_ids,
        notes=es.notes,
    )
    assert assign_heldout_split(relabeled.cases) == heldout


def test_scorer_output_validates_against_schema():
    out = score_predictions(FIXTURE_CASES, FIXTURE_PREDICTIONS)
    for metric, result in out.items():
        report = validate_record("scorer_output", result.to_dict())
        assert report.ok, f"{metric}: {report.errors}"


def test_manifest_records_validate_against_schema():
    # offline build on the fixture (no dataset load required)
    from repliclaw.benchmarks.agentrx.loader import PINNED_FILES, AgentRxEvalSet

    es = AgentRxEvalSet(
        cases=FIXTURE_CASES,
        data_hashes={name: "0" * 64 for name in PINNED_FILES},
        unannotated_magentic_ids=(),
        notes="n",
    )
    ms = build_eval_set_manifests(es)
    for m in ms.manifests:
        assert m.validate().ok, m.case_id
