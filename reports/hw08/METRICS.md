# HW8 measured results

Only completed real runs are reported as Kafka evidence.

| Failure scenario | Before fix | After fix |
|---|---|---|
| Duplicate delivery | 2 incidents from one replayed correlation | 1 incident; same UUID replayed |
| Consumer killed mid-work | Early commit skipped interrupted work; following marker completed | Same offset redelivered, output sent, then offset+1 committed |
| Poison message | Uncommitted bad message blocked its partition | Three attempts, dead letter, following valid message completed |
| Two partitions/two consumers | Partitions [0, 1]; globally ordered: False | One entity key; partitions [1]; ordered: True |

Unkeyed completion sequence: `[1, 0, 3, 2, 5, 4, 7, 6, 9, 8, 11, 10, 12, 13, 14, 15, 16, 17, 18, 19]`.

Keyed completion sequence: `[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]`.

Both runs contain exactly 20 related messages generated with VERIFY_SEED=262562. UUIDs and timing are real run data, not seeded identities or invented timings.

## Kafka compared with the HW2 in-process graph

Benefits: agents can scale independently through consumer groups; one failed agent can restart while other processes remain available and Kafka retains its input.

Responsibilities: implement idempotency and acknowledge offsets only after successful processing; choose entity keys for partition ordering and handle poison records with bounded retries and a dead-letter topic.

## Model and storage

The HW8 pipeline uses deterministic transit-domain agents; no LLM output or token metrics are claimed. Part 1 entities live only in a plain dictionary in one worker and are lost on worker restart, as specified. Pipeline deduplication uses a separate local SQLite runtime cache. Kafka itself provides at-least-once delivery; this is not a claim of global exactly-once processing.
