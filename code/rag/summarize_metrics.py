import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

RESULTS_FILE = (
    ROOT / "reports" / "hw03" / "raw"
    / "retrieval_results.csv"
)

CHUNK_FILE = (
    ROOT / "reports" / "hw03" / "raw"
    / "chunk_statistics.json"
)

METRICS_JSON = (
    ROOT / "reports" / "hw03" / "raw"
    / "retrieval_metrics.json"
)

METRICS_MD = ROOT / "reports" / "hw03" / "METRICS.md"


def percentile(values, percent):
    values = sorted(values)

    if not values:
        return 0.0

    position = (len(values) - 1) * percent
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower

    return (
        values[lower] * (1 - fraction)
        + values[upper] * fraction
    )


def read_results():
    with RESULTS_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))

    for row in rows:
        row["rank"] = int(row["rank"])
        row["store_score"] = float(row["store_score"])
        row["cosine_similarity"] = float(
            row["cosine_similarity"]
        )
        row["chunk_length"] = int(row["chunk_length"])
        row["retrieval_latency_ms"] = float(
            row["retrieval_latency_ms"]
        )
        row["expected_source_match"] = (
            row["expected_source_match"].strip().lower()
            == "true"
        )

    return rows


def load_chunk_statistics():
    if not CHUNK_FILE.exists():
        return {}

    with CHUNK_FILE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def calculate_metrics(rows):
    grouped = defaultdict(list)

    for row in rows:
        grouped[row["technique"]].append(row)

    metrics = []
    false_positives = []

    for technique, technique_rows in grouped.items():
        questions = defaultdict(list)

        for row in technique_rows:
            questions[row["question_id"]].append(row)

        top_one_hits = 0
        top_five_hits = 0
        matching_rows = 0
        reciprocal_ranks = []
        query_latencies = []
        top_one_store_scores = []
        top_one_cosines = []

        for question_id, question_rows in questions.items():
            question_rows.sort(key=lambda item: item["rank"])

            top_row = question_rows[0]
            matching = [
                row
                for row in question_rows
                if row["expected_source_match"]
            ]

            if top_row["expected_source_match"]:
                top_one_hits += 1

            for row in question_rows:
                if not row["expected_source_match"]:
                    false_positives.append(
                        {
                            "technique": technique,
                            "question_id": question_id,
                            "rank": row["rank"],
                            "retrieved_source": (
                                row["source_file"]
                            ),
                            "expected_source": (
                                row["expected_source"]
                            ),
                            "store_score": (
                                row["store_score"]
                            ),
                            "cosine_similarity": (
                                row["cosine_similarity"]
                            ),
                            "preview": row["preview"],
                        }
                    )

            if matching:
                top_five_hits += 1
                first_match_rank = min(
                    row["rank"]
                    for row in matching
                )
                reciprocal_ranks.append(
                    1.0 / first_match_rank
                )
            else:
                reciprocal_ranks.append(0.0)

            matching_rows += len(matching)
            query_latencies.append(
                top_row["retrieval_latency_ms"]
            )
            top_one_store_scores.append(
                top_row["store_score"]
            )
            top_one_cosines.append(
                top_row["cosine_similarity"]
            )

        question_count = len(questions)
        result_count = len(technique_rows)

        metrics.append(
            {
                "technique": technique,
                "questions": question_count,
                "retrieval_rows": result_count,
                "source_accuracy_at_1": (
                    top_one_hits / question_count
                ),
                "source_recall_at_5": (
                    top_five_hits / question_count
                ),
                "source_precision_at_5": (
                    matching_rows / result_count
                ),
                "mean_reciprocal_rank": (
                    statistics.mean(reciprocal_ranks)
                ),
                "mean_top1_store_score": (
                    statistics.mean(
                        top_one_store_scores
                    )
                ),
                "mean_top1_cosine": (
                    statistics.mean(top_one_cosines)
                ),
                "mean_chunk_length": (
                    statistics.mean(
                        row["chunk_length"]
                        for row in technique_rows
                    )
                ),
                "latency_mean_ms": (
                    statistics.mean(query_latencies)
                ),
                "latency_p50_ms": percentile(
                    query_latencies,
                    0.50
                ),
                "latency_p95_ms": percentile(
                    query_latencies,
                    0.95
                ),
            }
        )

    false_positives.sort(
        key=lambda item: item["store_score"],
        reverse=True
    )

    return metrics, false_positives


def percent(value):
    return f"{value * 100:.1f}%"


def create_markdown(
    metrics,
    false_positives,
    chunk_statistics
):
    lines = [
        "# HW3 Retrieval Metrics",
        "",
        "## Configuration",
        "",
        "- Embedding model: "
        "`sentence-transformers/all-MiniLM-L6-v2`",
        "- Embedding dimension: 384",
        "- Device: CPU",
        "- Top-k: 5",
        "- SEED: 2562",
        "- Corpus documents: 3",
        "- Precommitted questions: 5",
        "- Total retrieval rows: 75",
        "",
        "## Retrieval Quality and Latency",
        "",
        "| Technique | Accuracy@1 | Recall@5 | "
        "Precision@5 | MRR | Mean top-1 store score | "
        "Mean top-1 cosine | Mean chunk length | "
        "Latency mean (ms) | Latency p50 (ms) | "
        "Latency p95 (ms) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"
        "---:|---:|---:|",
    ]

    for item in metrics:
        lines.append(
            f"| {item['technique']} "
            f"| {percent(item['source_accuracy_at_1'])} "
            f"| {percent(item['source_recall_at_5'])} "
            f"| {percent(item['source_precision_at_5'])} "
            f"| {item['mean_reciprocal_rank']:.3f} "
            f"| {item['mean_top1_store_score']:.3f} "
            f"| {item['mean_top1_cosine']:.3f} "
            f"| {item['mean_chunk_length']:.1f} "
            f"| {item['latency_mean_ms']:.3f} "
            f"| {item['latency_p50_ms']:.3f} "
            f"| {item['latency_p95_ms']:.3f} |"
        )

    lines.extend(
        [
            "",
            "Accuracy@1 measures whether the first result came "
            "from the expected source. Recall@5 measures whether "
            "the expected source appeared anywhere in the top "
            "five. Precision@5 is the proportion of all retrieved "
            "rows that came from the expected source.",
            "",
            "## Confident False Positive",
            "",
        ]
    )

    if false_positives:
        item = false_positives[0]

        lines.extend(
            [
                "The highest-scoring result from an incorrect source was:",
                "",
                f"- Technique: `{item['technique']}`",
                f"- Question: `{item['question_id']}`",
                f"- Retrieved source: "
                f"`{item['retrieved_source']}`",
                f"- Expected source: "
                f"`{item['expected_source']}`",
                f"- Store score: "
                f"{item['store_score']:.6f}",
                f"- Explicit cosine similarity: "
                f"{item['cosine_similarity']:.6f}",
                f"- Preview: {item['preview']}",
                "",
                "This is a confident false positive because its "
                "retrieval score was comparatively high even "
                "though the result came from a source other than "
                "the precommitted expected source.",
            ]
        )
    else:
        lines.extend(
            [
                "No incorrect-source result appeared in the "
                "retrieved top-five sets.",
            ]
        )

    lines.extend(
        [
            "",
            "## Chunk Statistics",
            "",
            "The detailed machine-readable chunk statistics are "
            "stored in "
            "`reports/hw03/raw/chunk_statistics.json`.",
            "",
            "## Interpretation",
            "",
            "Shorter sentence-window chunks generally produced "
            "more focused passages, while token chunks retained "
            "more surrounding context. Semantic chunks were much "
            "larger and produced fewer total chunks, which could "
            "include unrelated material alongside relevant text.",
            "",
            "Retrieval scores measure similarity rather than "
            "truth. A high score can therefore occur for an "
            "incorrect source, which is why objective source "
            "matching and manual review are both necessary.",
            "",
        ]
    )

    if chunk_statistics:
        lines.append(
            "Chunk statistics were loaded successfully from the "
            "graded experiment output."
        )

    return "\n".join(lines)


def main():
    rows = read_results()

    if len(rows) != 75:
        raise ValueError(
            f"Expected 75 retrieval rows; found {len(rows)}"
        )

    metrics, false_positives = calculate_metrics(rows)
    chunk_statistics = load_chunk_statistics()

    output = {
        "seed": 2562,
        "embedding_model": (
            "sentence-transformers/all-MiniLM-L6-v2"
        ),
        "embedding_dimension": 384,
        "top_k": 5,
        "retrieval_rows": len(rows),
        "metrics_by_technique": metrics,
        "confident_false_positive": (
            false_positives[0]
            if false_positives
            else None
        ),
    }

    METRICS_JSON.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    METRICS_JSON.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    METRICS_MD.write_text(
        create_markdown(
            metrics,
            false_positives,
            chunk_statistics
        ),
        encoding="utf-8"
    )

    print("HW3 retrieval metrics")
    print()

    for item in metrics:
        print(
            f"{item['technique']}: "
            f"Accuracy@1="
            f"{percent(item['source_accuracy_at_1'])}; "
            f"Recall@5="
            f"{percent(item['source_recall_at_5'])}; "
            f"MRR="
            f"{item['mean_reciprocal_rank']:.3f}; "
            f"p50="
            f"{item['latency_p50_ms']:.3f} ms; "
            f"p95="
            f"{item['latency_p95_ms']:.3f} ms"
        )

    if false_positives:
        item = false_positives[0]
        print()
        print("Confident false positive:")
        print(
            f"{item['technique']} {item['question_id']} "
            f"retrieved {item['retrieved_source']} "
            f"instead of {item['expected_source']} "
            f"with store score "
            f"{item['store_score']:.6f}"
        )
    else:
        print()
        print("No incorrect-source result found in the top-five sets.")

    print()
    print(f"Saved: {METRICS_JSON}")
    print(f"Saved: {METRICS_MD}")


if __name__ == "__main__":
    main()