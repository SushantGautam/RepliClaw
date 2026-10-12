# Compound-causal verification matrix

Repo SHA: `832b3b0390e65f285bfc73804521e0d1b1e740bc`; seed 0; offline deterministic executor (`_base.run_canonical` + `_base.replay`); 0 LLM calls.

OBSERVED outcomes from actual target reruns (not expected values).

| case | arm | intervention | measured | observed | required | meets |
|---|---|---|---|---|---|---|
| drift_sign_and_v1 | I0_baseline | none (as-run system: sign bug + uncalibrated instrument) | 485.178711 | mismatch | mismatch | yes |
| drift_sign_and_v1 | I1_fix_sign | fix correction routine to subtract blank drift (instrument uncalibrated) | 479.706706 | pass | pass | yes |
| drift_sign_and_v1 | I2_recalibrate | recalibrate instrument: bias removed from readout, logged drift = 0 | 479.706706 | pass | pass | yes |
| drift_sign_and_v1 | I3_fix_both | fix correction sign AND recalibrate instrument (both-fix sanity arm) | 479.706706 | pass | pass | yes |
| flowmeter_single_cause_v1 | I0_baseline | none (as-shipped meter config) | 95737.9784 | mismatch | mismatch | yes |
| flowmeter_single_cause_v1 | I1_fix_calibration | restore firmware 3.4.1 pulse calibration | 101417.35 | pass | pass | yes |
| flowmeter_single_cause_v1 | I2_account_dropped | account for logged dropped pulse events (counter is 0 all window) | 95737.9784 | mismatch | mismatch | yes |

| case | case_sha256 | replay authentic | leak-check hits |
|---|---|---|---|
| drift_sign_and_v1 | `cbd0982a3dfb1bec…` | yes | 0 |
| flowmeter_single_cause_v1 | `b619445bf76764b5…` | yes | 0 |

Requirement structure: single-cause case -- exactly one latent cause; only I1_fix_calibration passes, the plausible non-cause I2_account_dropped still fails. AND case -- failure only with BOTH causes; each single fix (I1, I2) passes; both-fix sanity (I3) passes.

Artifacts: `artifacts/<case_id>/{manifest.json,interventions/<arm>/…}`; hidden-field documentation: `HIDDEN_FIELDS.md`.

**ALL REQUIREMENTS MET: true**
