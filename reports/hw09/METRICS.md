# HW9 measured results

Configuration: SID4=2562; PORT_BASE=8762; PREFIX=s2562; SEED=2562; VERIFY_SEED=262562; DOMAIN_ID=2. Model: qwen3:1.7b. Embeddings: sentence-transformers/all-MiniLM-L6-v2.

## Part 1

The 25-access run used incident 5007. Redis advanced from 25 to 50; MySQL ended at 50. Each multiple of ten produced a synchronization event. The returned Redis count includes accesses since the last database checkpoint.

## Part 2

Queries: 12; hit rate: 50.00%.
Cached mean latency: 83.43211666639642 ms. Non-cached mean latency: 16395.32861666703 ms.

## Parts 3.2 and 3.4

False-hit rate = false hits / all 40 cases; the conditional rate among hits is also in raw data.

| Threshold | Hit rate | False-hit rate | Mean latency (ms) | Total cost |
|---|---|---|---|---|
| 0.75 | 75.00% | 25.00% | 2880.37 | 1.0200 |
| 0.80 | 75.00% | 25.00% | 1370.56 | 1.0200 |
| 0.85 | 75.00% | 25.00% | 1351.94 | 1.0200 |
| 0.90 | 75.00% | 25.00% | 1352.35 | 1.0200 |
| 0.95 | 45.00% | 10.00% | 2870.37 | 0.4440 |

Costs are explicit assumptions, not paid API bills: 0.002 per miss and 0.10 per false hit. A wrong transit answer can require review/rework, budgeted at 50x a local miss.
The miss cost is a flat compute/queue-capacity budget for one local generation. The false-hit cost is a support/review budget. These values express an assumed preference for avoiding wrong answers; they are not inferred from latency or real invoices.
Chosen threshold: 0.95; minimum assumed cost on this workload.
Each threshold starts with the same ten warmed anchors. Miss answers are not added during the sweep. Real latency includes the embedding, version read, Redis lookup, and Kafka/model work on misses.

## Part 3.3 - Full false hit

Cached question: What is the current severity of the Route 2 incident?
Incoming question: What was the severity of the Route 2 incident yesterday?
Cosine similarity: 0.941560; threshold: 0.75.
Returned cached answer: {"answer": "The current severity of the Route 2 incident is 3.", "facts": {"route": 2, "severity": 3, "status": "open", "agency": "VTA", "delay_minutes": 12}, "abstained": false}
Correct response: The reference does not supply historical facts; abstain.
The queries share entity and attribute wording; the embedding underweights the temporal change from current to yesterday.
A shared incident/version marker does not establish that current and historical questions have the same meaning. A high similarity score is not proof of answer equivalence.

## Part 3.5 - Stale answer and invalidation

Record: s2562_rel.incidents id=5007. Question: What is the current severity of the Route 2 incident?
Old answer: {"answer": "The current severity of the Route 2 incident is 3.", "facts": {"route": 2, "severity": 3, "status": "open", "agency": "VTA", "delay_minutes": 12}, "abstained": false}
After updating the relational record and advancing its version, the disabled-check control returned a stale hit: {"answer": "The current severity of the Route 2 incident is 3.", "facts": {"route": 2, "severity": 3, "status": "open", "agency": "VTA", "delay_minutes": 12}, "abstained": false}
Re-enabling the version check rejected that cached entry and ran the Kafka/model path: {"answer": "The current severity of the Route 2 incident is 5.", "facts": {"route": 2, "severity": 5, "delay_minutes": 30, "status": "open", "agency": "VTA"}, "abstained": false}
Versions at the stale hit: cached=incident-5007-v2, database=incident-5007-v3. The next request hit the refreshed entry.
A metadata database read per request and obsolete vectors consume work/storage; updates must advance cache_version. Snapshot is valid as of the version read.
The demonstration restored the original fixture values afterward, while keeping its version monotonic.

## Part 4.4

| Variant | Correct | Incorrect | Average attempts | Average latency (ms) |
|---|---|---|---|---|
| Baseline | 4 | 0 | 1.00 | 1760.45 |
| Evaluator Repair | 4 | 0 | 1.00 | 1719.77 |
| Lesson Memory | 4 | 0 | 1.00 | 1712.95 |
| Validated Improvement | 4 | 0 | 1.00 | 1758.24 |

Baseline uses one answer; Evaluator Repair permits two attempts; Lesson Memory adds the training-derived lesson; Validated Improvement uses only lessons accepted on validation. Each variant reloads independent state and evaluates the identical held-out inputs.
The controlled incomplete initial answers occur only in the disclosed training demonstration. Final test answers are actual local-model outputs without injected defects.
The evaluator compares structured facts and requested values in the text against the reference; it is not a general natural-language entailment checker. Small synthetic datasets limit generalization.
On the held-out set, report any equal accuracy as equal accuracy; a successful controlled repair demonstrates the workflow but does not by itself establish a general accuracy improvement.

## Storage and correctness trade-offs

Redis INCR is atomic. MySQL stores every tenth count; losing Redis before a checkpoint can lose up to nine recent views. Concurrent checkpoint writes never reduce the persisted count.
A version read is performed before serving a semantic hit. Changes through the application increment cache_version. Direct SQL changes must also advance it. Old versions remain stored but are ineligible; this uses extra storage and a metadata read per request.
Agent communication uses an answer object, deterministic PASS/REVISE feedback, and at most two attempts. Lessons are selected using training and validation only; held-out test outputs never create lessons.
