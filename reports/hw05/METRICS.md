# HW5 Metrics

Configuration: `HOMEWORK=5`, `SID4=2562`, `PORT_BASE=8762`, `PREFIX=s2562`, `SEED=2562`, `VERIFY_SEED=262562`, `DOMAIN_ID=2`, model `qwen3:1.7b`.

| Injected failure rate | Calls | Success rate | Mean latency (ms) | p99 latency (ms) |
|---:|---:|---:|---:|---:|
| 0% | 50 | 100.0% | 0.3893 | 4.0646 |
| 20% | 50 | 100.0% | 0.6679 | 4.7125 |
| 50% | 50 | 92.0% | 1.5600 | 5.0689 |

## Retry demonstrations

- First-attempt success, retry success after one failure, and exhausted failure are recorded in `raw/retry_demonstrations.json`.

## Ollama scenarios

| Scenario | Steps | Stop reason | Tool calls |
|---:|---:|---|---:|
| 1 | 1 | completed | 1 |
| 2 | 1 | completed | 1 |
| 3 | 1 | completed | 1 |
| 4 | 1 | completed | 1 |
