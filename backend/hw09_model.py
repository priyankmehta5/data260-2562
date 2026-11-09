"""Local Ollama adapter shared by Kafka misses and the answering agent."""

import json
import os
import time

import httpx

from .hw09_common import MODEL, SEED, event


class OllamaAdapter:
    def generate(self, question, context, instructions="", feedback=""):
        started = time.perf_counter()
        prompt = (
            "Answer municipal transit questions using only the supplied reference facts. "
            "Return JSON with answer (short text), facts (object containing only requested supported facts), "
            "and abstained (boolean). For unsupported questions, abstain and use empty facts. "
            "Use facts keys route, severity, delay_minutes, status, agency when requested. "
            "Do not invent facts. /no_think\n"
            f"INSTRUCTIONS: {instructions}\nREFERENCE: {json.dumps(context)}\n"
            f"FEEDBACK: {feedback}\nQUESTION: {question}"
        )
        with httpx.Client(timeout=150) as client:
            response = client.post(
                os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434") + "/api/generate",
                json={
                    "model": MODEL,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False,
                    "think": False,
                    "keep_alive": "10m",
                    "options": {"temperature": 0, "seed": SEED, "num_predict": 240},
                },
            )
            response.raise_for_status()
            body = response.json()
        answer = json.loads(body["response"])
        if not isinstance(answer.get("answer"), str) or not isinstance(answer.get("facts"), dict):
            raise ValueError("Local model did not return the required answer/facts object")
        event(
            "local_model",
            model=MODEL,
            question=question,
            output=answer,
            latency_ms=(time.perf_counter() - started) * 1000,
            prompt_tokens=body.get("prompt_eval_count"),
            output_tokens=body.get("eval_count"),
        )
        return answer
