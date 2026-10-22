# Consolidated Memory

Last consolidated: 2026-10-20T00:00:00Z

- The project uses FastAPI, Pydantic, Python, and MongoDB for HW6.
- The domain is municipal transit incidents.
- The application port is 8762; the older 8000 setting was superseded.
- The local model is qwen3:1.7b; the older qwen2 setting was superseded.
- Redux Toolkit remains the frontend state layer.
- MongoDB stores messages, summaries, and episodes.
- Memory commands include /memory, /compact, /dream, and /help.
- Short-term memory is configurable and summaries are created periodically.
- Episodes contain facts, importance scores, and embeddings.
- Session identifiers may be null for lifetime summaries.
- Pydantic validates API inputs.
- Tests use deterministic fixtures.
- Reports store raw JSON and CSV evidence.
- Credentials and generated dependencies must never be committed.
- MongoDB data must remain inspectable.
- The report includes labeled screenshots and concise analysis.
- Verification records pass or fail.
- The final repository tag is hw6.
- Contradiction resolution is documented rather than silently discarded.
