import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from model_client import OllamaModelClient


def get_token_usage(response):
    usage = response.usage_metadata or {}
    metadata = response.response_metadata or {}

    input_tokens = usage.get(
        "input_tokens",
        metadata.get("prompt_eval_count", 0)
    )
    output_tokens = usage.get(
        "output_tokens",
        metadata.get("eval_count", 0)
    )
    total_tokens = usage.get(
        "total_tokens",
        input_tokens + output_tokens
    )

    return input_tokens, output_tokens, total_tokens


def history_length(history):
    return len(json.dumps(history, ensure_ascii=False))


def follows_bullet_format(content):
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    return bool(lines) and all(line.startswith("- ") for line in lines)


def print_stats(turn_count, cumulative_input, cumulative_output, history):
    print("\n--- Conversation Stats ---")
    print(f"Turn count: {turn_count}")
    print(f"Cumulative input tokens: {cumulative_input}")
    print(f"Cumulative output tokens: {cumulative_output}")
    print(f"History length: {history_length(history)} characters")


def main():
    instructions = (ROOT / "AGENT.md").read_text(encoding="utf-8")
    model = OllamaModelClient()

    history = [
        {"role": "system", "content": instructions}
    ]

    turn_count = 0
    cumulative_input = 0
    cumulative_output = 0

    print("Homework 1 Code Review Client")
    print("Commands: /stats, /exit")

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            user_input = "/exit"
            print()

        if not user_input:
            continue

        if user_input == "/stats":
            print_stats(
                turn_count,
                cumulative_input,
                cumulative_output,
                history
            )
            continue

        if user_input == "/exit":
            print("\n--- Final Stats ---")
            print(f"Turn count: {turn_count}")
            print(f"Cumulative input tokens: {cumulative_input}")
            print(f"Cumulative output tokens: {cumulative_output}")
            break

        history.append({"role": "user", "content": user_input})
        response = model.complete(history)
        content = response.content.strip()

        history.append({"role": "assistant", "content": content})

        input_tokens, output_tokens, total_tokens = get_token_usage(response)

        turn_count += 1
        cumulative_input += input_tokens
        cumulative_output += output_tokens

        print(f"\nAssistant:\n{content}")
        print("\n--- Turn Token Usage ---")
        print(f"Input tokens: {input_tokens}")
        print(f"Output tokens: {output_tokens}")
        print(f"Total tokens: {total_tokens}")
        print(
            "Bullet-only format followed:",
            "Yes" if follows_bullet_format(content) else "No"
        )


if __name__ == "__main__":
    main()