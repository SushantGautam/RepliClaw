"""Single-cause counterfactual case: flow meter totalization audit.

Exactly one latent cause (stale pulse calibration, sealed in
``oracle/oracle.json``) makes the pipeline's window total wrong; fixing it
alone makes the target pass. See :mod:`.case` for arms and hidden-field
documentation.
"""
from repliclaw.counterfactual.cases.flowmeter_single_cause.case import (
    FlowmeterSingleCauseCase,
    load_case,
)

__all__ = ["FlowmeterSingleCauseCase", "load_case"]
