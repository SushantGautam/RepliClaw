# Falsification Comparison — Results

**Mode:** LIVE (real LLM calls)
**Dataset:** adversarial_audit_rx441/v1 (sha256 `c3d4c9399f87f188…`)
**Claims:** C1
**Arms:** escrowed_independent, open_sharing, central_adaptive, single_investigator
**Matched per-claim caps:** total_tokens=16000, total_calls=16 (bounds tool calls), n_team=4, model=default, temperature=0.2

## Results table (arms × metrics)

| Arm | Acc | Trap acc | Abstain | Tokens | Tool calls | LLM calls | Wall (s) | Ind acc | False-consensus |
|-----|-----|----------|---------|--------|------------|-----------|----------|---------|-----------------|
| escrowed_independent | 0.0% | 0.0% | 100.0% | 18441 | 2 | 12 | 9.3756 | 100.0% | 100.0% |
| open_sharing | 100.0% | 100.0% | 0.0% | 24913 | 0 | 8 | 16.893 | 100.0% | — |
| central_adaptive | 100.0% | 100.0% | 0.0% | 6189 | 1 | 2 | 3.1657 | 100.0% | — |
| single_investigator | 100.0% | 100.0% | 0.0% | 2806 | 0 | 1 | 2.2679 | 100.0% | — |

## Per-arm per-claim verdicts

### escrowed_independent

| Claim | Expected | Predicted | Correct | Trap |
|-------|----------|-----------|---------|------|
| C1 | FALSE | ABSTAIN | ✗ | yes |

### open_sharing

| Claim | Expected | Predicted | Correct | Trap |
|-------|----------|-----------|---------|------|
| C1 | FALSE | FALSE | ✓ | yes |

### central_adaptive

| Claim | Expected | Predicted | Correct | Trap |
|-------|----------|-----------|---------|------|
| C1 | FALSE | FALSE | ✓ | yes |

### single_investigator

| Claim | Expected | Predicted | Correct | Trap |
|-------|----------|-----------|---------|------|
| C1 | FALSE | FALSE | ✓ | yes |
