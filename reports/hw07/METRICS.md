# HW7 Metrics

Configuration: SID4=2562, PORT_BASE=8762, PREFIX=s2562, SEED=2562, VERIFY_SEED=262562, DOMAIN_ID=2, model=qwen3:1.7b.

The raw machine-readable results are stored under `reports/hw07/raw/`.

| Metric | Result |
|---|---:|
| Verification tasks | 3 |
| Reliability attempts | 20 |
| Before-repair well-formed rate | 0% |
| After-repair well-formed rate | 100% |
| Bike-share scenarios | 2 |
| Minimum rows per scenario | 600 |
| Prompt-injection attacks | 3 |
| Safety-gate pass commands | 5 |
| Safety-gate blocked commands | 5 |

The three fixed verification tasks require search/detail, aggregate/detail, and search/detail/detail chains. The Reflexion path retries a failed deterministic verification at most twice and records only concise failure evidence and revised strategy. Tool-boundary enforcement blocks non-SELECT SQL even if a prompt attempts to override the policy text.

Part 4 pricing caveat: the official Lyft Bikes page lists a $29/month pass with a $1 unlock fee for each single ride. With 500 or more individual ride rows, pay-per-use cannot mathematically beat the monthly pass; the UI reports this comparison transparently rather than fabricating a pay-winning result.
