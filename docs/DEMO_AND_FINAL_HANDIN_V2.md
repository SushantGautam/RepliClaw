# Winning demo and final hand-in package — evidence-led plan
Status: PROPOSED preparation, NOT final organizer rules. Official site checked Oct 8 2026 does NOT publish an exact final upload form/video duration/hand-in clock time. Recheck and confirm with organizers. Deadline for **early application is Oct 16**, not necessarily the final artifact deadline.

## Live demo story (target 3–4 min internally, revise if actual organizer instructions differ)
1. **Problem (20s)**: A policy assistant gives wrong return advice. It might be retrieval, reasoning, policy conflict or erroneous judge.
2. **Competing hypotheses (30s)**: 3 differentiated scientific investigators state predicted discriminating interventions. Only commitment hashes, not their private conclusions, are visible pre-reveal.
3. **Verified experiments (60s)**: real SimpleAudit runs modify a *controlled factor*, show immutable manifests, traces, machine-produced observations and expected/outcome pairs.
4. **Emergence (45s)**: a new verified finding changes another investigator's next chosen test; no orchestrator-selected hard-coded role. Show a timestamped before/after evidence-map replay.
5. **Outcome (35s)**: competing hypotheses supported/contradicted/unresolved, one checked root cause where evidence permits, unexpected caveat, reusable regression test.
6. **Science comparison (45s)**: strong adaptive manager vs open-sharing swarm vs escrow swarm under matched budgets, **real observed metrics only**; include a case where decentralized system does not win if relevant.
7. **Collaboration (15s)**: another team's actual end-to-end invocation or label bonus unachieved. End on rerun command/trace.

## Evidence package
- One-command clean environment setup + offline replay; live tokens optional to reproduce only expensive model behavior.
- Two-stage demo: archived authentic run/replay (reliable) plus bounded real run (optional). Never pretend a replay is a new live run.
- Hypothesis graph, private pre-outcome forecasts, commitment/reveal integrity, actual execution logs and interventions, event timeline, final report.
- Real controlled intervention case + at least one differentiated held-out case, independently validated.
- Matched S0/S3/S4/S5 and ablations, pre-registered metrics, explicit small-sample caveats.
- Screenshot/short video backup, sources/README, known limitations and stop conditions.
- Reviewer G4/G5/G6 reports and source SHA + data licensing information.
- Third-party reuse docs + evidence of actual team adoption if achieved; avoid invented partner names.

## Rubric-aligned judge's evidence
20 problem: consequences of misdiagnosing AI failures and falsifiable root-cause alternatives.
25 impact: validated new information from actual counterfactual intervention and reusable regression artifact.
20 decentralization: distinct tools/private beliefs + local task bids/leases + replay-proven evidence-induced pivot, no central scientific manager.
25 collective: matched-budget accuracy/cost/time evidence vs adaptive central manager and ablations.
10 execution: fresh install, real audit and reproducible provenance.
+10 collaboration: demonstrably used by another team's experiment; independent acknowledgement.

## High-risk presentation traps
A pretty dashboard with no new scientific finding; live-only demo vulnerable to API outages; impossible claims of newness vs AutoScientists and AgentRx; 100% toy benchmark presented as general superiority; LLM-reported "executions"; demo shortcuts that secretly direct agents to expected root cause; claiming final requirements not published. Never use these.

## Timeline, all targets
2026-10-08–10: freeze team application story; checkpoint WIP; novelty/design spike; get first causal SimpleAudit intervention working.
2026-10-11–15: early application finalized and **submitted before Oct 16**; red/green baselines; autonomous local selection test; independent reviewer.
2026-10-16–23: scientific case refinement, held-out evaluation, no-escrow and central-manager comparisons; external-test invitations.
2026-10-24–29: blind trial, paper-grade limitations, video backup, fresh install, official organizer final instructions check.
2026-10-30–Nov 1: event, collaboration, actual final delivery under whatever requirements organizers communicate.

## Response to disappointing results
If adaptive central manager wins: show which mechanism fails, the negative research result and an accurately scoped reusable evidence-escrow auditing tool. If local choice does not adapt: simplify it rather than claiming emergence. Judge-worthy science is more valuable than a false "100% win".

## P1 result statement — mandatory disclosures (A9.4/C7 + S-1 + N-2 + R-2)
**Governing rule (science round 3, 2026-10-09, MUST-1): no P1/P2/P3 result may be reported — in any demo,
application update, or this handin — until every item below is included verbatim or faithfully paraphrased.**
Source: `docs/application/P1_RESULT_DISCLOSURES_DRAFT.md` (cleared to fold by the round-3 verdict;
prereg `PREREG-2026-10-v1.2-AMENDMENT.md` §6b A9.4; round-3 report
`docs/reviews/SCIENCE-JUDGE-A1-A9-ROUND3-APPROVE-WITH-CONDITIONS-20261009.md`).

1. **Attribution.** A P1-SUPPORTED outcome (if reached) establishes "running the
   counterfactual interventions improves defect diagnosis **on this single seeded case**
   (`policy_rag_v1`)" — it does NOT establish "decentralized autonomy improves diagnosis".
   Attribute the mechanism to **counterfactual-intervention identifiability**, not to
   autonomy or decentralization in the abstract.
2. **Base-case confound.** From base data alone, `retrieval_omission` and `judge_stale`
   are causally non-identifiable (base retrieval AND base judge both point at the 14-day
   staleness). Only S5's interventions disambiguate (I_R changes the retrieved target;
   I_J flips the verdict with byte-identical downstream output; I_P is byte-identical,
   ruling out policy conflict). A comparator arm scoring M1 ≈ 0 is a **valid scientific
   result** — the treatment supplies the identifiability the baseline lacks — not
   "starvation".
3. **M1 definition.** M1 is a **5-way exact-match classification**
   (`defect_class == oracle.true_cause` with `bool(target_artifact)`). The shared defect
   taxonomy is given to **ALL arms equally** — a menu, not the answer; S5's defect token
   is partly taxonomy-assisted, and so is every comparator's, equally.
4. **Scope.** **Single seeded case, no generalization.** No "autonomy beats central
   workflows" claim; the novelty framing stays within `docs/PRIOR_ART_NOVELTY_GATE.md`'s
   defensible mechanism bundle.
5. **S-1 (offline fixture stand-in).** The offline deterministic arm's
   `_deterministic_defect` returns a registered `("retrieval_omission","retrieval")` pair
   from base data alone so the parity fixture stays executable and scoreable. It is a
   **fixture stand-in, not a causally justified diagnosis** (it inherits the §2 confound);
   it is never exercised in the primary live P1.
6. **N-2 (budget granularity).** Strategy arms' `budget_ledger.json` writes a single
   synthetic **aggregate** call (`llm_calls:1`, `completion_tokens:0`, all tokens as
   `prompt_tokens`) — per-run totals are correct; per-call granularity is aggregate for
   strategy arms (S5 records genuine per-call usage). Disclose in any token comparison.
7. **R-2 (token floors).** S4/S3/S0 live-token floors are measured on the first
   pre-flight live run and recorded pre-window (`floor_r2.json`, protocol
   `docs/experiments/R2_TOKEN_FLOOR_PREFLIGHT_PROTOCOL.md`). Do not report comparator
   token cost as final until then. Backstops: 60k/arm cap, 10.8M master ceiling, S0
   stopping rule.
