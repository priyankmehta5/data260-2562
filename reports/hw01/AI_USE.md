# AI Use Disclosure

## 1. What did I use an AI assistant for, and what did I do myself?

I used an AI assistant to clarify selected assignment requirements, review implementation approaches, and troubleshoot Docker, AWS, Ollama, and Windows errors. I also consulted implementation examples, which I reviewed and adapted for my assigned municipal transit domain.

I created and managed the repository, configured the development environment, integrated the application files, developed the programs, executed the commands, tested each component, deployed the application, collected the experimental results, verified the outputs, and prepared the submission evidence.

## 2. What AI-produced output was wrong or unsuitable?

The assignment initially required the `qwen3:8b` model, but running it caused Windows to restart with the `VIDEO_MEMORY_MANAGEMENT_INTERNAL` stop code. An AI assistant suggested testing the smaller `qwen3:4b` model as a more conservative alternative.

The second model also caused Windows to restart with the same video-memory-management stop code. Therefore, both models were unsuitable for stable execution on my laptop.

## 3. How did I detect or verify the problem?

I detected the problem when Windows restarted during both model tests. I checked Windows Event Viewer and found a system error report showing bug check `0x0000010e`. This corresponded to the `VIDEO_MEMORY_MANAGEMENT_INTERNAL` error displayed during the crashes.

Because the same failure occurred with both `qwen3:8b` and `qwen3:4b`, I determined that simply selecting a somewhat smaller model did not resolve the hardware-related execution problem. I also verified that the crashes occurred while running local Ollama inference rather than during the other Python or Docker tasks.

## 4. What did I change, and why does it work now?

I changed Ollama to CPU-only execution and selected `qwen3:1.7b` as the third model. After starting Ollama with the CPU library setting, I ran `ollama ps` and confirmed that the model showed `100% CPU`.

The third model completed inference without restarting Windows. I then used it successfully for the Planner and Reviewer workflow, all 40 nondeterminism tests, and the five-turn model-client conversation. This solution works because the smaller model requires fewer resources and CPU-only execution avoids the unstable GPU video-memory path that caused the earlier crashes.
