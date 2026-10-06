# Stage 2 — append-only decisions, amendments, failures and recovery

## D-V3-001 (2026-10-09, proposed design)
Decision: primary research estimand is decentralized escrow pipeline vs **adaptive centralized with the same executable counterfactual tools**, across independent heldout cases. Evidence: P08 S5/A1/A3=1.00, S4=.20, S3=.05; intervention presence explains the result, not autonomy. Alternatives: repeating P08 single-case (rejected), giving only swarm interventions (rejected). Stage-2 V3 prereg remains DRAFT.

## D-V3-002 (2026-10-09, proposed reuse)
Decision: external benchmark tracks are AgentRx + RCAEval observational, AIOpsLab executable/controlled, CAR method comparator only if replay semantics align. ScienceAgentBench verified transfer deferred. No custom dataset unless external benchmark feasibility genuinely fails and Science Judge approves a versioned controlled supplement.

## D-V3-003 (2026-10-09, safe release)
Decision: `dev` holds agent-facing docs, implementation and orchestration. Public-facing `main` receives only explicitly human-approved, reviewed release updates. Dev on public GitHub is still publicly browseable: no secrets/hidden labels/restricted datasets.

## D-V3-004 (2026-10-09, scientific integrity)
Decision: observational traces are not counterfactual experimental runs; intervention tool parity, safe environment reset, evaluator blindness and case-level uncertainty are preconditions for a causal coordination claim. Preserve all null results and legacy P08 data.

## Pending decisions
- exact dataset versions, access permissions, stratified splits, license constraints
- AIOpsLab cluster deployment/cost authorization and safe reset support
- detailed sample-size/power from pilot, primary scorer frozen version, number of arms
- exact model/provider, caps, full experimental cost budget, explicit two-key authorization
- when/how a curated public subset may be released to main

## Append future entries
For each: ID, UTC time, proposer, source hashes, issue/failed attempt, alternatives compared, independent reviews, chosen action, scope of prereg amendment, next verification and whether human authorized. Never rewrite an older entry to make a failure disappear.
