# HW3 Retrieval Metrics

## Configuration

- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- Embedding dimension: 384
- Device: CPU
- Top-k: 5
- SEED: 2562
- Corpus documents: 3
- Precommitted questions: 5
- Total retrieval rows: 75

## Retrieval Quality and Latency

| Technique | Accuracy@1 | Recall@5 | Precision@5 | MRR | Mean top-1 store score | Mean top-1 cosine | Mean chunk length | Latency mean (ms) | Latency p50 (ms) | Latency p95 (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Token | 100.0% | 100.0% | 100.0% | 1.000 | 0.692 | 0.671 | 1087.2 | 16.766 | 17.783 | 18.011 |
| Semantic | 100.0% | 100.0% | 84.0% | 1.000 | 0.602 | 0.564 | 4214.4 | 17.495 | 17.435 | 19.121 |
| Sentence window | 100.0% | 100.0% | 100.0% | 1.000 | 0.746 | 0.702 | 236.3 | 33.682 | 35.449 | 38.264 |

Accuracy@1 measures whether the first result came from the expected source. Recall@5 measures whether the expected source appeared anywhere in the top five. Precision@5 is the proportion of all retrieved rows that came from the expected source.

## Confident False Positive

The highest-scoring result from an incorrect source was:

- Technique: `Semantic`
- Question: `q2`
- Retrieved source: `vta_security_and_system_safety.pdf`
- Expected source: `vta_climate_actions.pdf`
- Store score: 0.559343
- Explicit cosine similarity: 0.507576
- Preview: Crime and antisocial behavior are potential problems in any public environment. System Safety refers to the prevention of accidents to the riding public, employ...

This is a confident false positive because its retrieval score was comparatively high even though the result came from a source other than the precommitted expected source.

## Chunk Statistics

The detailed machine-readable chunk statistics are stored in `reports/hw03/raw/chunk_statistics.json`.

## Interpretation

Shorter sentence-window chunks generally produced more focused passages, while token chunks retained more surrounding context. Semantic chunks were much larger and produced fewer total chunks, which could include unrelated material alongside relevant text.

Retrieval scores measure similarity rather than truth. A high score can therefore occur for an incorrect source, which is why objective source matching and manual review are both necessary.

Chunk statistics were loaded successfully from the graded experiment output.