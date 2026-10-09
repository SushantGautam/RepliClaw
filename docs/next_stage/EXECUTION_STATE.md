# Stage 2 — authoritative execution state (dev only)

**Timestamp:** 2026-10-09 (planning; update timestamp and HEAD at next agent action).
**Development branch:** `dev` (created from public `main` at 97a455947895e48fb551503e8fd1158d03a293af).
**Public-facing branch:** `main`; never update without explicit human release approval.
**Current milestone:** C00 documentation created / implementation NOT STARTED. This is an instruction and research planning checkpoint, not new experimental evidence.
**Experiment authorization:** NOT GRANTED for stage-2 live campaign; G4 cannot pass until specific human approval.
**V3 protocol:** DRAFT, not preregistered, not approved.

## P08 historical evidence — must remain unchanged
120 live runs / six arms / one seeded case `policy_rag_v1`; M1 S5/A1/A3=1.00, S4=.20, S0=.15, S3=.05; P1-v1.2 protocol contrast supported but not attribution to decentralization. M3 corrected from 0 to .50; 1,716,411 total tokens; no oracle leak detected. See `docs/experiments/P1_RESULT_STATEMENT_20261009.md`. Historical CI is within-case, not evidence of generalization.

## Milestones
| ID | Status as of document creation | Exit |
|---|---|---|
| C00 Documentation and dev agent rules | DONE for content creation; pending independent doc QA | new dev branch + AGENTS + review + protocol + fleet + seed |
| C01 Upstream version/license/access | NOT STARTED | source pins/access/provenance |
| C02 Published baseline reproduction | NOT STARTED | official executable baseline/scorer |
| C03 Intervention-matched parity | NOT STARTED | dynamic strong central, same causal tools |
| C04 Oracle/isolation + reset canaries | NOT STARTED | independent pass |
| C05 Bounded multi-case pilot | NOT STARTED | human scope authorization + exploratory evidence |
| C06 Frozen prereg + approval keys | NOT STARTED | science sign-off + explicit full-run authorization |
| C07 Case-level heldout study | NOT STARTED | case-weighted scores, reproducibility |
| C08 Human-approved main release | NOT STARTED | curated public results |

## Blockers / risk register
- AgentRx official HF data gated; confirm permitted access and release split/count.
- Different public AgentRx release descriptions show two vs three benchmark domains and nine vs ten taxonomy categories. Reconcile exact pinned version, NEVER quietly convert.
- RCAEval recorded failures are not counterfactual replay; data larger than a small smoke; select by predeclared strata.
- AIOpsLab may need Kubernetes/Helm/deployment and safe reset proof; deployment incurs resource cost and needs human approval.
- P08 high accuracies ceiling-saturated on one case; diverse heldout independent cases required.
- Stage-2 provider/token/time/cluster budget unspecified; **do not launch paid/live experiment**.
- AGENTS and fleet instructions on a public `dev` branch are publicly visible to anyone browsing GitHub; never use for secrets.

## First actions for orchestrator
1. Read AGENTS.md and both docs/next_stage/{LITERATURE_AND_BENCHMARK_DECISION,EXPERIMENT_PROTOCOL_V3_DRAFT}.md.
2. Spawn independent read-only L1 AgentRx, L2 RCAEval, L3 AIOpsLab contract probes; L5 science methods; L6 schemas; integrate source pins.
3. Create lane/worktree log; verify baseline official commands and expected exact metric schema; report blockages with evidence.
4. Request approval only for truly necessary paid model/cluster/holdout activity; continue offline parallel work.
5. Update this file at every checkpoint; **do not edit historical P08 artifacts**.
