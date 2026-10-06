"""V3 static canary — design ceq_arm_design.md §5.7 (R1, R3) + test 13.

``ceq.py`` must contain NO case/defect/intervention literals: the planner
menu comes only from ``load_interventions`` and the defect menu only from
the shared instruction string. A hidden fixed script (planner prompt-tuned
toward the known answer) or an oracle leak would require one of these
literals in the source.
"""
from __future__ import annotations

from pathlib import Path

from repliclaw.counterfactual.executor import load_interventions
from repliclaw.defect_adjudication import DEFECT_TAXONOMY
from repliclaw.experiments.v3 import ceq


def _forbidden_literals():
    """J-CODE W1 F2: the literal set is DERIVED from the shared sources, so it
    covers ALL intervention ids and ALL defect classes, not a hand-maintained
    subset. Index-based fixed scripts remain covered by the behavioral
    adaptivity test (test_ceq_adaptivity_offline)."""
    lits = set()
    for spec in load_interventions():
        lits.add(spec.intervention_id)
    lits.update(DEFECT_TAXONOMY)
    # Design §6 test-13 list + §5.7 sealed-content terms (R3 static) + case id.
    lits.update(
        (
            "I_R_retrieval_fix",
            "I_P_policy_conflict",
            "I_J_judge_fix",
            "policy_rag_v1",
            "load_oracle",
            "true_cause",
            "oracle",
        )
    )
    return sorted(lits)


def test_no_fixed_script():
    src = Path(ceq.__file__).read_text(encoding="utf-8")
    offenders = [lit for lit in _forbidden_literals() if lit in src]
    assert not offenders, f"ceq.py contains forbidden literals: {offenders}"


def test_menu_and_hypotheses_imported_not_hardcoded():
    """The intervention menu + hypothesis mapping come from shared modules
    (imported names, not in-source literals) — the structural half of R1."""
    src = Path(ceq.__file__).read_text(encoding="utf-8")
    assert "load_interventions" in src  # menu source (design §3)
    assert "load_case" in src
    # Hypothesis->arm mapping is imported, never defined by literal in ceq.py.
    assert "ARM_BY_HYP" in src
    # No per-hypothesis branching: the module has no H_R/H_P/H_J literals.
    for hyp in ("H_R", "H_P", "H_J"):
        assert hyp not in src, f"hardcoded hypothesis literal {hyp} in ceq.py"
    # The case id is imported as CASE_ID, not spelled out.
    assert "CASE_ID" in src
