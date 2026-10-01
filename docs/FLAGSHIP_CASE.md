# Flagship: AI assistant failure attribution by counterfactual audit
**Test design only**, not implemented. Based on Hans presentation slide 8 (illustrative return-policy chatbot); no dataset/results or "finding" is implied.

## Test environment
A tiny deterministic simulated shopping assistant with a known policy, simple order lookup and retrieval system plus evaluator. Use versioned documents and frozen model/RAG configs. Alternate audited model: a real LLM endpoint, with deterministic fixture fallback for hermetic CI. Never accidentally leak oracle flags into target model prompt or investigator contexts.
Example public policy text ("returns within 30 days, excluding clearance items"), a specific order's purchase date and channel, a failed reply, and tool/retrieval traces. The hidden evaluator knows which intervention family changes outcome. Construct independent cases where missing policy, conflicting interpretation, retrieval ordering and judge rubric each matter, plus clean and ambiguous controls. Avoid safety-critical policy instructions that could be mistaken for real healthcare/legal advice.

## Scientific hypothesis register (agents may propose others)
H_R (retrieval): critical current policy passage absent, suppressed or ranked below cutoff.
H_P (policy application): passage available but target model fails to apply an exclusion or precedence rule.
H_J (judge mismatch): target's answer is defensible but the evaluator uses stale reference/rubric.
H_C (combined): interactions of H_R and H_J, or H_R and H_P.
Agent predictions must name a distinguishing intervention and expected observation *before running it*, sealed by v2 escrow.

## Controlled interventions
I_R: hold the model/prompt/judge constant and replace retrieved passage with full/current policy; run target; collect answer + tracer events.
I_P: hold retrieval constant and modify policy conflict explicitness/order; run target; record change in violations.
I_J: hold target response constant and swap evaluator to validated policy-aligned references; run the judge and calculate changed classification.
I_C: factorial retrieval × judge interventions; preserve agent permissions and control cost. Compare with no-change baseline and account for stochastic model outputs using paired seeds where supported (seed reproducibility is model-dependent).

## Quality oracle & outcome
Independent evaluation checks recorded target answer and policy-grounded conclusions against the frozen true policy; label whether root cause is identified with validated interventions, whether predicted observation occurred, and which hypotheses are supported/contradicted/unresolved. If interventions do not isolate a cause, say **UNRESOLVED** and log what would distinguish it.

## Scientific target (not observed)
One case should support a nontrivial causal discrimination: e.g., I_R fixes target output but I_J does not (retrieval supported); OR I_J reverses a mistaken audit verdict without changing target output (judge error). Agent choices must not be scripted to this result. Include deceptive but plausible explanations so blind disagreement is meaningful.
Second case ideally identifies a different failure family; final evaluation hides which is which and uses held-out case variants.

## Minimal runnable asset plan
- reusable \`experiments/simpleaudit_counterfactual/\` config/data generator, freeze manifests and hashes;
- \`SimpleAuditExecutor\` adapter: accept (scenario, intervention, model, judge, seed, cost cap), return immutable run ID, actual output, trace, provenance;
- transition ledger: published observation, hypothesis revisions, signed/hashed pre-outcome forecasts, autonomous task proposals/claims;
- test: same observable case → two interventions → distinct actual outputs and independently validated explanation where appropriate;
- test: no oracle metadata accessible to investigator or model prompt;
- integration from v1 tests without breaking existing CLI.

## Demo trace
At time t0 three investigators create predictions, show only commitments. At t1 a worker **independently** chooses intervention I_R, obtains SimpleAudit actual run. At t2 verified public evidence is published and at t3 another chooses I_J based on new evidence. Verify this t3 choice changes relative to the same agent's choice under its t0 evidence snapshot. At t4 final validated report labels alternative explanations and costs.
This sequence is a **minimum scientific acceptance scenario**, not permission to force agents to follow these test names. Use a deterministic policy/fallback for reliable CI, plus a true live-agent trial showing emergent selections without manually scripting outcomes.

## Relation to competitor SOTA
AgentRx https://github.com/microsoft/AgentRx works on trajectories and constraint violations; this project specifically tests whether **active controlled interventions plus evidence escrow/local coordination** provide additional ability to distinguish failure causes, not simply identify the first bad step. AutoScientists https://github.com/mims-harvard/AutoScientists covers decentralized discovery; this project must show its domain-specific trust/causal mechanism distinctly.
