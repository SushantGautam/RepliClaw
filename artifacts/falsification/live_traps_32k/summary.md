# Falsification Comparison — Results

**Mode:** LIVE (real LLM calls)
**Dataset:** adversarial_audit_rx441/v1 (sha256 `c3d4c9399f87f188…`)
**Claims:** C1, C2, C3, C5, C6
**Arms:** escrowed_independent, open_sharing, central_adaptive, single_investigator
**Matched per-claim caps:** total_tokens=32000, total_calls=16 (bounds tool calls), n_team=4, model=default, temperature=0.2

## Results table (arms × metrics)

| Arm | Acc | Trap acc | Abstain | Tokens | Tool calls | LLM calls | Wall (s) | Ind acc | False-consensus |
|-----|-----|----------|---------|--------|------------|-----------|----------|---------|-----------------|
| escrowed_independent | 20.0% | 20.0% | 80.0% | 131474 | 18 | 79 | 68.8901 | 90.0% | 100.0% |
| open_sharing | 100.0% | 100.0% | 0.0% | 143982 | 14 | 47 | 95.0951 | 100.0% | — |
| central_adaptive | 100.0% | 100.0% | 0.0% | 50824 | 5 | 17 | 18.9597 | 100.0% | — |
| single_investigator | 100.0% | 100.0% | 0.0% | 14133 | 0 | 5 | 12.2683 | 100.0% | — |

## Per-arm per-claim verdicts

### escrowed_independent

| Claim | Expected | Predicted | Correct | Trap |
|-------|----------|-----------|---------|------|
| C1 | FALSE | FALSE | ✓ | yes |
| C2 | TRUE | ABSTAIN | ✗ | yes |
| C3 | FALSE | ABSTAIN | ✗ | yes |
| C5 | FALSE | ABSTAIN | ✗ | yes |
| C6 | FALSE | ABSTAIN | ✗ | yes |

### open_sharing

| Claim | Expected | Predicted | Correct | Trap |
|-------|----------|-----------|---------|------|
| C1 | FALSE | FALSE | ✓ | yes |
| C2 | TRUE | TRUE | ✓ | yes |
| C3 | FALSE | FALSE | ✓ | yes |
| C5 | FALSE | FALSE | ✓ | yes |
| C6 | FALSE | FALSE | ✓ | yes |

### central_adaptive

| Claim | Expected | Predicted | Correct | Trap |
|-------|----------|-----------|---------|------|
| C1 | FALSE | FALSE | ✓ | yes |
| C2 | TRUE | TRUE | ✓ | yes |
| C3 | FALSE | FALSE | ✓ | yes |
| C5 | FALSE | FALSE | ✓ | yes |
| C6 | FALSE | FALSE | ✓ | yes |

### single_investigator

| Claim | Expected | Predicted | Correct | Trap |
|-------|----------|-----------|---------|------|
| C1 | FALSE | FALSE | ✓ | yes |
| C2 | TRUE | TRUE | ✓ | yes |
| C3 | FALSE | FALSE | ✓ | yes |
| C5 | FALSE | FALSE | ✓ | yes |
| C6 | FALSE | FALSE | ✓ | yes |
