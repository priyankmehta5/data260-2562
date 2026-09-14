import argparse
import json
from pathlib import Path

from schema_experiment import run_once
from src.model_client import OllamaModelClient


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "reports" / "hw02" / "raw"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--model", default="qwen3:1.7b")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--turn-ceiling", type=int, default=10)
    args = parser.parse_args()

    input_data = json.loads(
        Path(args.input).read_text(encoding="utf-8")
    )

    client = OllamaModelClient(
        model=args.model,
        temperature=args.temperature
    )

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    output_path = RAW_DIR / "adversarial_runs.json"
    summary_path = RAW_DIR / "adversarial_summary.json"

    results = []

    if output_path.exists():
        results = json.loads(
            output_path.read_text(encoding="utf-8")
        )

    print(f"Resuming from {len(results)} completed runs.")

    for run_number in range(len(results) + 1, args.runs + 1):
        result = run_once(
            run_number,
            input_data,
            client,
            args.turn_ceiling
        )

        results.append(result)

        output_path.write_text(
            json.dumps(results, indent=2),
            encoding="utf-8"
        )

        print(
            f"Run {run_number}/{args.runs}: "
            f"{result['classification']}, "
            f"{result['turn_count']} turns, "
            f"{result['latency_ms']} ms"
        )

    ceiling_hits = sum(
        result["classification"] == "abandoned_or_ceiling"
        for result in results
    )

    summary = {
        "total_runs": len(results),
        "ceiling_hits": ceiling_hits,
        "ceiling_hit_rate_percent": round(
            ceiling_hits / len(results) * 100,
            1
        ),
        "completed_without_ceiling": (
            len(results) - ceiling_hits
        ),
        "target_ceiling_hits": 4,
        "target_met": ceiling_hits >= 4
    }

    summary_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8"
    )

    print("\n--- Adversarial Test Summary ---")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()