# data260-2562
DATA-260 coursework repository for SID4 2562

This repository contains shared application code and homework artifacts for
DATA-260.

## Student Configuration

- SID4: 2562
- PORT_BASE: 8762
- PREFIX: s2562
- SEED: 2562
- VERIFY_SEED: 262562
- DOMAIN_ID: 2
- Assigned domain: Municipal transit incidents

## Repository Structure

- `code/`: Shared application code
- `src/`: Shared model-adapter modules
- `reports/hw01/`: Homework 1 report, results, logs, and evidence


## Model Client and Conversation Context

### Why do previous messages need to be sent again?

The local model does not automatically remember earlier requests. Each model call is independent, so the client sends the system instructions and previous user and assistant messages with every request. This conversation history gives the model the context needed to understand follow-up questions.

### How is a system message different from a user message?

A system message defines the model's overall behavior and instructions. In this application, the system message contains the rules from `AGENT.md`, including the requirement to respond only with bullet points. A user message contains the current question or code that the user wants reviewed. The system message has a higher instructional priority than an ordinary user message.

### Why do input tokens grow during a conversation?

Input tokens grow because each new request includes the accumulated conversation history. As more user prompts and assistant responses are added, the amount of text sent back to the model increases. This causes later turns to have more input tokens than earlier turns.

### What eventually limits conversation growth?

Conversation growth is limited by the model's context window. The context window is the maximum number of tokens the model can process in one request. When the conversation becomes too large, older messages must be removed, summarized, or shortened so the request remains within the model's context limit.
