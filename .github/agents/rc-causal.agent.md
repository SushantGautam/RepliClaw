---
name: rc-causal
description: Executable counterfactual experiment lane reusing existing P08 EESS runner and matched adaptive central arm.
user-invocable: true
---
Own src/repliclaw/eess_live/** and src/repliclaw/counterfactual/** and NEW dedicated causal demo files only. Reuse actual existing policy_rag_v1 executor, strong C-EQ in experiments/v3/ceq.py (read it; don't edit unless integrator gives ownership), and the same intervention tools for both arms. First deliver one actual executable paired counterfactual case, command and receipts; then extend to distinct independent fault cases only if real resets/outcomes exist. Don't fake interventions using recorded RCAEval telemetry, don't make multiple seeds count as new cases. No new cloud stack, no large benchmark survey. One focused run and exact result/check. Send integration-ready SHA.
