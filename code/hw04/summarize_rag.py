import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "reports" / "hw04" / "raw"
METRICS_FILE = ROOT / "reports" / "hw04" / "METRICS.md"
INPUT_FILE = RAW_DIR / "rag_evaluation.csv"
OUTPUT_FILE = RAW_DIR / "rag_summary.json"


def as_bool(value):
    return str(value).strip().lower() == "true"


with INPUT_FILE.open(encoding="utf-8") as file:
    rows = list(csv.DictReader(file))

groups = defaultdict(list)

for row in rows:
    groups[row["configuration"]].append(row)

names = {
    "A": "No RAG",
    "B": "Basic RAG",
    "C": "Context RAG"
}

summary = []

for configuration in ["A", "B", "C"]:
    items = groups[configuration]
    refusal_items = [
        row for row in items
        if row["question_id"] in {"Q5", "Q6"}
    ]

    result = {
        "configuration": configuration,
        "name": names[configuration],
        "questions": len(items),
        "retrieval_accuracy_percent": round(
            100 * sum(
                as_bool(row["correct_retrieval"])
                for row in items
            ) / len(items),
            1
        ),
        "answer_accuracy_percent": round(
            100 * sum(
                as_bool(row["correct_answer"])
                for row in items
            ) / len(items),
            1
        ),
        "faithfulness_percent": round(
            100 * sum(
                as_bool(row["grounded"])
                for row in items
            ) / len(items),
            1
        ),
        "format_compliance_percent": round(
            100 * sum(
                as_bool(row["format_compliance"])
                for row in items
            ) / len(items),
            1
        ),
        "refusal_robustness_percent": round(
            100 * sum(
                as_bool(row["refused_when_needed"])
                for row in refusal_items
            ) / len(refusal_items),
            1
        )
    }

    summary.append(result)

OUTPUT_FILE.write_text(
    json.dumps(summary, indent=2),
    encoding="utf-8"
)

lines = [
    "",
    "## HW4 RAG Evaluation",
    "",
    "| Configuration | Retrieval accuracy | Answer accuracy | Faithfulness | Format compliance | Q5/Q6 refusal robustness |",
    "|---|---:|---:|---:|---:|---:|"
]

for row in summary:
    lines.append(
        f"| {row['configuration']} - {row['name']} "
        f"| {row['retrieval_accuracy_percent']}% "
        f"| {row['answer_accuracy_percent']}% "
        f"| {row['faithfulness_percent']}% "
        f"| {row['format_compliance_percent']}% "
        f"| {row['refusal_robustness_percent']}% |"
    )

lines.extend(
    [
        "",
        "Retrieval accuracy measures whether the expected source documents appeared in the supplied context. Faithfulness requires a source citation or the exact required refusal. Refusal robustness is calculated only from Q5 and Q6.",
        ""
    ]
)

metrics = (
    METRICS_FILE.read_text(encoding="utf-8")
    if METRICS_FILE.exists()
    else "# HW4 Metrics\n"
)

marker = "## HW4 RAG Evaluation"

if marker in metrics:
    metrics = metrics.split(marker)[0].rstrip() + "\n"

METRICS_FILE.write_text(
    metrics.rstrip() + "\n" + "\n".join(lines),
    encoding="utf-8"
)

print("HW4 RAG evaluation summary")

for row in summary:
    print(
        f"{row['configuration']} - {row['name']}: "
        f"answer_accuracy={row['answer_accuracy_percent']}%; "
        f"faithfulness={row['faithfulness_percent']}%; "
        f"format={row['format_compliance_percent']}%; "
        f"refusal_robustness="
        f"{row['refusal_robustness_percent']}%"
    )

print(f"\nSaved: {OUTPUT_FILE}")
print(f"Updated: {METRICS_FILE}")