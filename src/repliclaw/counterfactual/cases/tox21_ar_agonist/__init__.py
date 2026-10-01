"""P06 second scientific case: Tox21 AR-agonist directed functionalization.

See :mod:`.case` for the falsifiable question, data provenance, and arms.
Import the case with ``from repliclaw.counterfactual.cases.tox21_ar_agonist import
load_case`` (or ``from ...case import Tox21ArAgonistCase``).
"""
from repliclaw.counterfactual.cases.tox21_ar_agonist.case import (
    Tox21ArAgonistCase,
    load_case,
)

__all__ = ["Tox21ArAgonistCase", "load_case"]
