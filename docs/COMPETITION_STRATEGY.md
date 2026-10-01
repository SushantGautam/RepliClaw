> **SUPERSEDED STRATEGY V1 BELOW (preserved for historical rationale).** Active v2: [RepliClaw Evidence-Escrow Swarm](EVIDENCE_ESCROW_SWARM.md), [Novelty vs AutoScientists/AgentRx](PRIOR_ART_NOVELTY_GATE.md), [Flagship SimpleAudit interventions](FLAGSHIP_CASE.md), [Experimental protocol](EXPERIMENT_PROTOCOL_V2.md), [current plan](../IMPLEMENTATION_PLAN.md). No firstness or winning guarantees. Preserve existing agents' work with [migration guide](AGENT_MIGRATION.md).

---

# ScienceClaw 2026: RepliClaw competition strategy
Last verified: 2026-10-08. This is the active *new* research program; the six-task prototype is a baseline, not the final scientific result.

## Mission and falsifiable hypothesis
Build **RepliClaw: a decentralized scientific replication and falsification collective** that can independently assess claims, commit before seeing peers, expose contradictory evidence, publish unmet scientific needs, autonomously select qualified participants, execute follow-up experiments, and return provenance-linked verdicts.

**Primary hypothesis:** Under matched resources and blinded held-out tasks, independent commit/reveal plus decentralized evidence-conditional follow-up improves scientific claim verification/recovery versus the strongest single-agent and centralized multi-agent comparators. This is a hypothesis, not an established result. Report negative/null findings honestly.

### What the organizer actually requires
Official: https://scienceclawhack.ai/ (checked 2026-10-08)
- Problem significance and complexity **20%**
- Scientific/technical impact **25%**
- Decentralized agency **20%**
- Collective capability **25%**
- Execution and validation **10%**
- Collaboration bonus **up to +10** for material cross-team reuse.

A functioning scientific system with measured results is required; architecture diagrams alone do not score. Event Oct 30–Nov 1, 2026; early application Oct 16, expected decisions Oct 19. **Do not invent final submission format or final upload deadline**; verify later against official instructions. Team sizes 2–5.

## Honest baseline inventory (as of 2026-10-08)
Already present: Python package, 3 method roles, context gating, SHA-256 commit/reveal integrity, evidence graph, fixed-path follow-up, five nominal strategies, CLI/Python verify surface, OTel span hooks, deterministic fixtures, saved live LLM demo and tests.
Committed artifacts: `artifacts/benchmark/`, `artifacts/demo/`, `artifacts/demo-llm/`.
Existing deterministic six-fixture benchmark: RepliClaw 6/6 correctness; NOT a general scientific result.
Existing live LLM misleading-case demo: all five strategies return REFUTED; **no live-model performance advantage has yet been shown**. Preserve and report this inconvenient fact.

## Material gaps (confirmed by source inspection)
G1 **Not sufficiently decentralized**: `protocol.py::_fulfill_need` chooses a role and invokes a follow-up directly; the NeedItem/Reactor adapter does not establish a truly independent claim/dispatch loop.
G2 **Isolation overclaimed**: investigators execute sequentially in the protocol's Python process, with context-level gating. Commit happens after all initial findings. No demonstrated hostile-process or tool/filesystem isolation.
G3 **Weak baseline fidelity**: `run_open_debate` sets revealed peer material, but `LLMInvestigator.run` calls `to_prompt_block(revealed=False)`; debate may not actually see peer conclusions. `isolated_vote` uses shared evidence-aware verdict logic, not necessarily simple majority voting.
G4 **Self-reported executable evidence**: model-produced `executable=True` lacks proof of an independently run command/log/artifact.
G5 **Evaluation threats**: six closely shaped fixtures, no held-out real scientific benchmark, no matched model/token/compute budgets, no repeated seeded runs, no estimates of uncertainty; current recovery metric partly measures correct verdict on faulted items rather than a measured wrong→correct transition.
G6 **Independence metric insufficient**: different agent IDs are not proof of independent methods, evidence, models, tools, or errors.
G7 **No documented third-party integration**: cross-team API exists but actual external reuse is not yet evidenced.
G8 **Confidence not calibrated**: weighted heuristic 'confidence' should be identified as score until calibration is empirically assessed.
G9 **Demo unrepresentative**: deterministic demo shows emerging need; live-LLM demo does not (no conflict was observed).

## Product/proof strategy
Use a narrow, consequential scientific question requiring real computation. Recommended flagship candidate: molecular toxicity model validation (e.g., Tox21) with *ethically sourced, reproducible* data splits and leakage/metric-shift checks. It is a candidate; first run a feasibility experiment and select based on actually reproducible code/data. Add a small external scientific evaluation (e.g., executable rediscovery tasks) as a generalization check. Avoid claims of a novel domain discovery until independently verified.

Hero demo must show an actual claim → at least three independent runnable investigations → hash-only commitments → sealed reveal → disagreement/uncertainty → a published need autonomously claimed by an eligible worker → a fresh executable experiment → a provenance-linked, uncertainty-aware verdict. If evidence does not conflict, display it honestly; select an observed challenging case for the demo without corrupting evaluation.

## Measurable experiment
Pre-register held-out questions and reference labels/data lineage before running evaluations. Compare:
1. strong single agent (matched total spend);
2. static centralized DAG;
3. isolated multi-agent simple vote;
4. actual shared-context debate;
5. full RepliClaw;
6. ablations (no blind, no adaptive follow-up, no evidence diversity; optional centralized adaptive follow-up).
Control same model/tool capabilities, data access, task order and capped total budget where applicable. Record prompts, models, versions, calls, tokens, CPU/GPU time, latency, seeds, interventions, artifacts and run hashes.
Report task-level correctness, false accept/reject with explicit denominators, abstention, calibration (if probabilities), recovery from *observed* pre-followup error/uncertainty, inter-agent error correlation with sufficient cases, cost-quality frontier and confidence intervals. Use blinded held-out cases, repeated seeds and error taxonomy; do not claim p-values from six examples.
Ask the scientific reviewer to reject comparisons where baselines are intentionally crippled or given inferior tools.

## Winning artifacts
- Reproducible executable scientific result, one-command demo, raw output, code, provenance;
- budget-matched baseline + ablation report including negative results;
- evidence of genuine autonomous and decentralized need-fulfillment (not a scripted node);
- proof of strong isolation and commitment ordering;
- external-team `verify()` integration and acknowledgement of benefit where permitted;
- short demo narrative and application aligned exactly to rubric.
Do not build a new dashboard/database when SimpleAuditStudio, ScienceClaw or OTel can satisfy the need.

## Event and submission accuracy
Application at https://scienceclawhack.ai/apply.html before Oct 16 early deadline; event Oct 30–Nov 1. The official public rubric does not yet confirm a final upload form, video length or repo visibility requirement; the event team must confirm these before hand-in. Keep `docs/SUBMISSION_CHECKLIST.md` current.

## Source links
- https://scienceclawhack.ai/
- https://code.visualstudio.com/docs/agents/run/subagents
- https://code.visualstudio.com/docs/agents/guides/delegate-two-tasks
- https://code.visualstudio.com/docs/agent-customization/custom-agents
