# Homework 2 AI Use

## 1. What did I use an AI assistant for, and what did I do myself?

I used an AI assistant to help identify possible debugging approaches and improve the organization of the report. I wrote and reviewed the project code files, executed every command, tested the responsive interface and API, ran the LangGraph and schema experiments, inspected the outputs, corrected errors, and collected the screenshots and raw results myself.

## 2. What AI-produced output was wrong or unsuitable, or what did I independently verify?

The initial setup guidance used the assignment-recommended `qwen3:8b` model. Although the model could be downloaded through Ollama, it was unsuitable for my laptop. Running it caused Windows to restart with a `VIDEO_MEMORY_MANAGEMENT_INTERNAL` stop error. I also tested the smaller `qwen3:4b` model, but it caused the same system error.

## 3. How did I detect the problem or verify the result?

I detected the problem when Windows crashed and restarted while the local model was running. The same stop error occurred with both `qwen3:8b` and `qwen3:4b`, which indicated that the problem was related to the model resource requirements and my laptop's graphics-memory configuration rather than the application input.

I then tested `qwen3:1.7b` with Ollama configured for CPU-only execution. I used `ollama ps` to verify the active processor allocation, and the output reported that the model was using 100% CPU.

## 4. What did I change, and why does it work now?

I replaced the larger models with the tool-capable `qwen3:1.7b` model and configured Ollama to avoid GPU execution. I also used the same model consistently in the reusable model client, LangGraph workflow, schema-validation experiment, ceiling comparison, adversarial experiment, and verification procedure.

The smaller model requires fewer hardware resources, and CPU-only execution avoids the graphics-memory condition that caused Windows to restart. After making this change, I completed all required workflow tests and 75 experimental runs without another system crash.
