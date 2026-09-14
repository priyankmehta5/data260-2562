# Homework 2 Metrics

## Schema Validation Results

| Classification | Runs |
|---|---:|
| Valid on first attempt | 30 |
| Valid after one retry | 0 |
| Valid after two or more retries | 0 |
| Abandoned at ceiling | 0 |
| Total | 30 |

Completion rate: 100.0%

Mean latency: 6487.7 ms

## Turn Ceiling Comparison

| Turn ceiling | Runs | Completed | Completion rate | Mean latency |
|---:|---:|---:|---:|---:|
| 2 | 20 | 0 | 0.0% | 1353.1 ms |
| 10 | 20 | 20 | 100.0% | 4002.45 ms |

A ceiling of 2 stopped the workflow before the Planner and Reviewer sequence could complete. A ceiling of 10 allowed all 20 runs to complete.

## Adversarial Results

| Measurement | Result |
|---|---:|
| Total runs | 5 |
| Ceiling hits | 5 |
| Ceiling-hit rate | 100.0% |
| Completed without ceiling | 0 |
| Required target | At least 4 ceiling hits |
| Target met | Yes |

## Total Experimental Runs

| Experiment | Runs |
|---|---:|
| Schema validation | 30 |
| Ceiling comparison | 40 |
| Adversarial input | 5 |
| Total | 75 |
