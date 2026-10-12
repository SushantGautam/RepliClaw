"""Compound two-cause AND-interaction counterfactual case: batch-assay
drift audit. The failure (wrong batch mean) manifests ONLY when BOTH latent
causes are present at once -- the flipped correction sign AND the
uncalibrated (nonzero-drift) instrument. Each cause alone is latent. See
:mod:`.case` for arms and hidden-field documentation.
"""
from repliclaw.counterfactual.cases.drift_sign_and.case import DriftSignAndCase, load_case

__all__ = ["DriftSignAndCase", "load_case"]
