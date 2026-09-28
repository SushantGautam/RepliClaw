# Vendored ScienceClaw subset (pruned)

Pruned snapshot of https://github.com/lamm-mit/scienceclaw at commit:

    ab9aba130200e0a7dd4c76dca5cf945169f8c44a

Only the import-safe subset needed by RepliClaw is vendored:

- `artifacts/` — `Artifact`, `ArtifactStore`, `NeedItem`, `ArtifactReactor`, `pressure` scoring
- `core/` — `llm_client`, `skill_registry`, `skill_executor`

Heavy, non-hermetic parts (`memory/`, full `skills/` tree, `benchmarks/`,
`visualization/`) are intentionally excluded to keep RepliClaw installable and
testable in a clean environment. RepliClaw reuses these modules via
`repliclaw/scienceclaw_adapter.py` and does NOT modify them. See `DECISIONS.md` D01.
