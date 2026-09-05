# Homework 1 Results

## Part 2 - Agentic AI

### Environment

| Item              | Value       |
| ----------------- | ----------- |
| Python version    | Python 3.12 |
| Local model       | qwen3:1.7b  |
| Model server      | Ollama      |
| Execution mode    | CPU only    |
| Temperature       | 0.0         |
| Strict validation | Enabled     |

The assignment recommends qwen3:8b. However, qwen3:8b and qwen3:4b both caused Windows bugcheck `0x0000010E`, `VIDEO_MEMORY_MANAGEMENT_INTERNAL`, during GPU inference. I therefore used the smaller tool-capable qwen3:1.7b model with Ollama's CPU-only backend, as permitted by the assignment.

### Input

**Title:** VTA Blue Line Signal Failure

**Content:** A signal failure near Santa Clara station caused major delays and disrupted Blue Line light rail service during the morning commute.

### Command Used

```powershell
python code/agents_demo.py --title "VTA Blue Line Signal Failure" --content "A signal failure near Santa Clara station caused major delays and disrupted Blue Line light rail service during the morning commute." --model qwen3:1.7b --temperature 0.0 --strict
```

### Agent Results

| Stage              | Result    |
| ------------------ | --------- |
| Planner latency    | 55,168 ms |
| Reviewer latency   | 95,589 ms |
| Final tag count    | 3         |
| Summary word count | 20        |
| Valid final JSON   | Yes       |

### Q1. Final Tags

1. `signal failure`
2. `morning commute`
3. `blue line`

### Q2. Final Summary

Signal failure near Santa Clara station caused major delays and disrupted Blue Line light rail service during the morning commute.

### Q3. Did the Reviewer Change Anything?

No. The Reviewer returned the same three tags and summary as the Planner. Although its decision note stated "corrected tags," comparison of the actual Planner and Reviewer results showed no changes.

### Planner Step

The Planner received the incident title and content and proposed three topical tags and a one-sentence summary. Its output was returned as JSON for the Reviewer to examine.

### Reviewer Step

The Reviewer received the original input and the Planner's complete output. It checked the tags for relevance and uniqueness and checked whether the summary remained within the 25-word limit.

### Finalization Step

The Finalizer was implemented as a Python validation step rather than a third model agent. It enforced exactly three tags, normalized the summary, and produced the final publishable JSON.

### Output Validation

The final output contained exactly three distinct tags. All three tags were derived from the transit-incident input. The final summary contained 20 words, which satisfied the maximum length of 25 words.

### Observed Model Limitation

The Planner and Reviewer placed the summary text in the auxiliary `issues` array even though it was not an issue. I detected this by comparing the meaning of the `issues` field with its actual content. The deterministic Finalizer excluded that field from the required final JSON, so the published result contained only the validated tags and summary.

## Part 3: Nondeterminism Experiment

The nondeterminism experiment used the same fixed municipal transit incident input for every run. The local `qwen3:1.7b` model was tested 20 times at temperature 0.7 and 20 times at temperature 0.0. All 40 runs completed successfully.

### Results

| Temperature | Successful Runs | Distinct Tag Sets | p50 Latency | p95 Latency | p99 Latency |
|---|---:|---:|---:|---:|---:|
| 0.7 | 20 | 10 | 115,486 ms | 161,003 ms | 167,861 ms |
| 0.0 | 20 | 3 | 76,804 ms | 122,841 ms | 154,367 ms |

At temperature 0.7, no tag appeared in all 20 runs. The tags that appeared in exactly one run were `blue line delays`, `blue line service disruption`, `commute delay`, `rail service`, `rail service disruption`, `santa clara`, and `vta signal failure`.

At temperature 0.0, `blue line` and `signal failure` appeared in all 20 runs. The tags `morning commute` and `vta blue line` each appeared in exactly one run.

The higher temperature produced 10 distinct tag sets, while temperature 0.0 produced only 3. This shows that lowering the temperature reduced output variation but did not eliminate it completely. Temperature 0.0 was also faster in this experiment, with a median latency of 76,804 ms compared with 115,486 ms at temperature 0.7.

The latency measurements represent the complete Planner and Reviewer workflow for each test run.

## Part 4: Model Client Conversation

The interactive model client completed a five-turn code-review conversation using the local `qwen3:1.7b` model. Instructions were loaded from the root-level `AGENT.md` file and sent to the model as a system message.

All five responses followed the required bullet-only format. The client displayed the input, output, and total token counts after every model response.

### Conversation Statistics

| Measurement              |     After Turn 3 |     After Turn 5 |
| ------------------------ | ---------------: | ---------------: |
| Turn count               |                3 |                5 |
| Cumulative input tokens  |              501 |            1,155 |
| Cumulative output tokens |              131 |              193 |
| History length           | 1,370 characters | 1,920 characters |

Between turns 3 and 5, the cumulative input-token count increased from 501 to 1,155, while the conversation history increased from 1,370 to 1,920 characters. The input-token count increased because each new request included the system instructions and the previous user and assistant messages.

The cumulative output-token count increased from 131 to 193 as two additional responses were generated. The model followed the instructions from `AGENT.md`, and the client reported `Bullet-only format followed: Yes`.

The final session contained five completed turns, 1,155 cumulative input tokens, and 193 cumulative output tokens.
