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
