# HW4 N+1 Metrics

- VERIFY_SEED: 262562
- Total requests: 180

| Version | Page size | SQL statements/request | p50 (ms) | p95 (ms) | p99 (ms) | p50 speedup |
|---|---:|---:|---:|---:|---:|---:|
| naive | 10 | 11 | 23.96 | 32.835 | 36.404 | - |
| naive | 50 | 51 | 68.424 | 98.369 | 111.576 | - |
| naive | 200 | 201 | 230.707 | 322.926 | 396.742 | - |
| optimized | 10 | 1 | 13.28 | 16.97 | 18.667 | 1.8 |
| optimized | 50 | 1 | 16.561 | 23.029 | 27.154 | 4.13 |
| optimized | 200 | 1 | 22.407 | 32.206 | 54.808 | 10.3 |

## HW4 RAG Evaluation

| Configuration | Retrieval accuracy | Answer accuracy | Faithfulness | Format compliance | Q5/Q6 refusal robustness |
|---|---:|---:|---:|---:|---:|
| A - No RAG | 33.3% | 33.3% | 0.0% | 100.0% | 0.0% |
| B - Basic RAG | 66.7% | 50.0% | 0.0% | 100.0% | 0.0% |
| C - Context RAG | 66.7% | 83.3% | 66.7% | 83.3% | 100.0% |

Retrieval accuracy measures whether the expected source documents appeared in the supplied context. Faithfulness requires a source citation or the exact required refusal. Refusal robustness is calculated only from Q5 and Q6.
