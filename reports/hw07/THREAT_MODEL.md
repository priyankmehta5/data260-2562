# HW7 Threat Model

The public-data exercise treats retrieved pricing text and uploaded CSV content as untrusted input.

| Attacker goal | Enabling condition | Defense |
| --- | --- | --- |
| Override the recommendation | Hostile retrieved text is treated as an instruction | Keep retrieved text in a labeled evidence field; compute the decision from validated numeric inputs |
| Execute a write through the CSV tool | SQL text reaches the database adapter without a tool boundary | `csv_sql` accepts one `SELECT` statement and rejects write, schema, attachment, and pragma keywords |
| Exfiltrate uploaded CSV rows | The model is allowed to quote the entire uploaded file | Return only requested aggregates or bounded result rows; do not include raw file contents in the final answer |

Prompt-only instructions are insufficient because a model can still follow hostile retrieved text or generate unsafe SQL. The tool boundary enforces the SELECT-only contract independently of the model, while the result schema limits what is returned. The before/after examples are recorded in `raw/prompt_injection_results.json`.
