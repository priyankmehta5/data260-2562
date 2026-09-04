from typing import Any

from langchain_ollama import ChatOllama


class OllamaModelClient:
    def __init__(
        self,
        model: str = "qwen3:1.7b",
        temperature: float = 0.0,
        base_url: str = "http://localhost:11434",
        num_ctx: int = 4096,
    ):
        self.model = ChatOllama(
            model=model,
            temperature=temperature,
            base_url=base_url,
            num_ctx=num_ctx,
            format="json",
        )

    def complete(
        self,
        messages: list[tuple[str, str]],
        tools: list[Any] | None = None,
    ):
        model = self.model.bind_tools(tools) if tools else self.model
        return model.invoke(messages)