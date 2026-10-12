"""Offline AgentRx metrics — baseline-agnostic scorer.

Computes the official AgentRx metric schema (contract §7, from
``agentrx/judge/judge.py`` summary writer + ``agentrx/reports/analyze_metrics.py``)
over ``(prediction, case)`` pairs. Predictions come from an EXTERNAL predictor
callable — this module contains no LLM, no judge, and no execution:

* root-cause category accuracy: a case is correct iff
  ``predicted_failure_case == gt root_cause.category_code``
  (``str(most_common_failure) == str(gt_failure_case)`` in the official code);
* step-number accuracy: ``step_mean = mean(predicted step numbers)``,
  exact if ``round(step_mean) == gt_step``, within ±k if
  ``abs(round(step_mean) - gt_step) <= k``;
* denominators: ``Correct cases + Incorrect cases`` for accuracy;
  ``total_cases`` (cases with >= 1 step prediction) for step metrics —
  per the official code-verified denominators (contract §7).

Output is a per-metric :class:`ScorerOutput` table conforming to
``repliclaw.scorer_output/v1``; raw per-case rows are the authoritative record.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import mean
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from ..common.records import ScorerCaseRow, ScorerOutput
from .loader import AgentRxCASE

#: Formula id pinning this exact metric definition (agentrx official schema).
FORMULA_VERSION = "agentrx_official/v1"

STEP_TOLERANCES: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)


@dataclass(frozen=True)
class Prediction:
    """External predictor output for one case.

    ``failure_case``: predicted root-cause category int (0 = NO_ERROR_PREDICTED
    sentinel, treated as a wrong prediction per upstream).
    ``step_numbers``: predicted root-cause step numbers (the official judge
    averages its per-iteration predictions; a single-iteration predictor passes
    one value). ``round(step_mean)`` is used per the official formula.
    """

    case_id: str
    failure_case: int
    step_numbers: Tuple[int, ...] = ()
    model: Optional[str] = None
    endpoint: Optional[str] = None
    judge_mode: Optional[str] = None
    exec_mode: Optional[str] = None
    run_id: Optional[str] = None

    @property
    def step_mean(self) -> Optional[float]:
        return mean(self.step_numbers) if self.step_numbers else None

    def provenance(self) -> Dict[str, str]:
        """Model/endpoint/mode record required in any baseline G1 record (Science Judge F8)."""
        return {
            "model": self.model or "unknown",
            "endpoint": self.endpoint or "unknown",
            "judge_mode": self.judge_mode or "unknown",
            "exec_mode": self.exec_mode or "unknown",
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def score_case(case: AgentRxCASE, pred: Prediction) -> Dict[str, Any]:
    """Per-case metric rows for one (case, prediction) pair."""
    gt_cat = case.root_cause.category_code
    gt_step = case.root_cause.step_number
    cat_correct = int(pred.failure_case) == gt_cat

    step_mean = pred.step_mean
    step_rows: Dict[str, Tuple[bool, Optional[float]]] = {}
    if step_mean is not None:
        rounded = round(step_mean)
        for tol in STEP_TOLERANCES:
            step_rows[f"step_within_{tol}"] = (abs(rounded - gt_step) <= tol, float(abs(rounded - gt_step)))
    else:
        for tol in STEP_TOLERANCES:
            step_rows[f"step_within_{tol}"] = (False, None)

    return {
        "case_id": case.case_id,
        "category_correct": cat_correct,
        "gt_category": gt_cat,
        "predicted_category": int(pred.failure_case),
        "gt_step": gt_step,
        "step_mean": step_mean,
        "step_rows": step_rows,
        "trajectory_length": case.trajectory_length,
    }


def _metric(
    name: str,
    rows: List[ScorerCaseRow],
    numerator: int,
    denominator: int,
    run_ids: Tuple[str, ...],
) -> ScorerOutput:
    value = (numerator / denominator) if denominator else None
    return ScorerOutput(
        metric=name,
        value=value,
        numerator=numerator,
        denominator=denominator if denominator else None,
        formula_version=FORMULA_VERSION,
        per_case=tuple(rows),
        scored_at=_utc_now(),
        run_ids=run_ids,
    )


def score_predictions(
    cases: Iterable[AgentRxCASE],
    predictions: Iterable[Prediction],
) -> Dict[str, ScorerOutput]:
    """Score (case, prediction) pairs against the official AgentRx metric schema.

    Returns metrics: ``root_cause.category_accuracy`` (denominator =
    Correct + Incorrect cases), ``step_number.accuracy`` (exact) and
    ``step_number.accuracy_within_pm{1..5}`` (denominator = cases with at
    least one step prediction, = the official ``total_cases`` for step metrics).
    Per-case tables are the authoritative record.
    """
    cases_by_id = {c.case_id: c for c in cases}
    pred_list = list(predictions)
    for p in pred_list:
        if p.case_id not in cases_by_id:
            raise ValueError(f"prediction for unknown case_id {p.case_id!r}")
    run_ids = tuple(sorted({p.run_id for p in pred_list if p.run_id}))
    rows_by_metric: Dict[str, List[ScorerCaseRow]] = {
        "root_cause.category_accuracy": [],
        "step_number.accuracy": [],
        **{f"step_number.accuracy_within_pm{t}": [] for t in range(1, 6)},
    }
    n_correct = 0
    n_incorrect = 0
    n_with_steps = 0
    for p in pred_list:
        res = score_case(cases_by_id[p.case_id], p)
        if res["category_correct"]:
            n_correct += 1
        else:
            n_incorrect += 1
        rows_by_metric["root_cause.category_accuracy"].append(
            ScorerCaseRow(
                case_id=p.case_id,
                value=res["category_correct"],
                eligible=True,
                note=(
                    f"pred_cat={res['predicted_category']} gt_cat={res['gt_category']} "
                    f"step_mean={res['step_mean']} gt_step={res['gt_step']}"
                ),
            )
        )
        if res["step_mean"] is None:
            for tol in (0, *range(1, 6)):
                rows_by_metric[f"step_number.accuracy_within_pm{tol}" if tol else "step_number.accuracy"].append(
                    ScorerCaseRow(case_id=p.case_id, value=False, eligible=False, note="no step predictions")
                )
            continue
        n_with_steps += 1
        for tol in (0, *range(1, 6)):
            ok, dist = res["step_rows"][f"step_within_{tol}"]
            rows_by_metric[f"step_number.accuracy_within_pm{tol}" if tol else "step_number.accuracy"].append(
                ScorerCaseRow(case_id=p.case_id, value=ok, eligible=True, note=f"distance={dist}")
            )

    out: Dict[str, ScorerOutput] = {}
    out["root_cause.category_accuracy"] = _metric(
        "root_cause.category_accuracy",
        rows_by_metric["root_cause.category_accuracy"],
        n_correct,
        n_correct + n_incorrect,
        run_ids,
    )
    out["step_number.accuracy"] = _metric(
        "step_number.accuracy",
        rows_by_metric["step_number.accuracy"],
        sum(1 for r in rows_by_metric["step_number.accuracy"] if r.value is True),
        n_with_steps,
        run_ids,
    )
    for t in range(1, 6):
        name = f"step_number.accuracy_within_pm{t}"
        out[name] = _metric(
            name,
            rows_by_metric[name],
            sum(1 for r in rows_by_metric[name] if r.value is True),
            n_with_steps,
            run_ids,
        )
    return out


def predict_and_score(
    cases: Iterable[AgentRxCASE],
    predictor: Callable[[AgentRxCASE], Prediction],
) -> Dict[str, ScorerOutput]:
    """Baseline-agnostic entry point: run an external predictor, then score."""
    cases = list(cases)
    return score_predictions(cases, [predictor(c) for c in cases])


__all__ = [
    "FORMULA_VERSION",
    "Prediction",
    "STEP_TOLERANCES",
    "predict_and_score",
    "score_case",
    "score_predictions",
]
