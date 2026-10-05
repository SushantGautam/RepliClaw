# Release readiness checklist
Last checked: 2026-10-08.
Independent research project — SimuMet AI Safety research department (https://www.simulamet.no/research/research-departments/ai-safety).
(This file began life as an event hand-in checklist; the project is now an independent public research project, so it is maintained here as the release/publication readiness checklist.)

## Scope
The release must evidence: a meaningful science problem, a functioning decentralized collective, measured scientific/technical results, and reuse/collaboration where it occurs. External reviewers should be able to rerun everything from the released artifacts.

## Release readiness (evidence package)
- [ ] Code freeze: all SHAs recorded, branch state verified, no in-flight unmerged experiment code
- [ ] Actual scientific problem and falsifiable hypothesis, external domain expert input if available
- [ ] Runnable system plus clean-install reproduction
- [ ] Real research case, data/source license, code, run manifest, saved raw execution logs
- [ ] Blind commit → reveal → unexpected need → independently claimed experiment → verdict demo
- [ ] Controlled, matched-budget baselines and ablation study with failures and intervals
- [ ] Agent action/independence proof and independent reviewer approval records
- [ ] Third-party integration example and acknowledgement (only when actually achieved)
- [ ] Concise README, command, figures, short demo and fallback artifacts
- [ ] Paper/preprint and project website ready; claims in README/website exactly match the published result statement

## Citation and license
- [ ] License file present and consistent with data/model provenance
- [ ] Suggested citation block (project name, artifact/commit SHA, date)
- [ ] Upstream attributions: lamm-mit/scienceclaw (vendored at `deps/scienceclaw`), SimpleAudit/SimpleAuditStudio, and any dataset/model licenses

## V2 alignment (2026-10-08, retained for continuity)
Public description and claim-boundary disclosures live in [APPLICATION_V2.md](APPLICATION_V2.md). [DEMO_AND_FINAL_HANDIN_V2.md](DEMO_AND_FINAL_HANDIN_V2.md) has the evidence-package details. First get real validated causal finding and honest comparison; no manufactured score. Team must check Hans/Michael/Sushant approvals before release.