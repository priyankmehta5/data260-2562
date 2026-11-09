"""Create labeled cases BEFORE sweeping; write-once fixtures prevent accidental relabeling."""

import hashlib
import json

import yaml

from backend.hw09_common import DATA, REPORT, ROOT, event, save


def write_once(path, value, yaml_file=False):
    content = yaml.safe_dump(value, sort_keys=False) if yaml_file else json.dumps(value, indent=2)
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise ValueError(f"Refusing to overwrite frozen dataset: {path.name}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def prepare():
    anchors = []
    specs = [
        (2, "severity"),
        (2, "delay"),
        (3, "severity"),
        (3, "delay"),
        (4, "status"),
        (5, "delay"),
        (4, "agency"),
        (5, "severity"),
        (3, "status"),
        (2, "agency"),
    ]
    for index, (route, field) in enumerate(specs):
        anchors.append(
            {
                "id": f"anchor{index + 1:02}",
                "route": route,
                "field": field,
                "query": f"What is the current {field} of the Route {route} incident?",
            }
        )
    unrelated = [
        "How do I bake sourdough bread?",
        "What is the capital of Japan?",
        "Explain photosynthesis.",
        "How do I tune a guitar?",
        "What is a prime number?",
        "How do volcanoes form?",
        "Explain a chess fork.",
        "How do I grow basil?",
        "What is a lunar eclipse?",
        "How do I knit a scarf?",
    ]
    cases = []
    for index, anchor in enumerate(anchors):
        for category, question, hit in [
            ("exact", anchor["query"], True),
            ("paraphrase", f"Tell me the current {anchor['field']} for the incident on Route {anchor['route']}.", True),
            (
                "similar_different",
                f"What was the {anchor['field']} of the Route {anchor['route']} incident yesterday?",
                False,
            ),
            ("unrelated", unrelated[index], False),
        ]:
            cases.append(
                {
                    "case_id": f"{category}{index + 1:02}",
                    "category": category,
                    "anchor_id": anchor["id"],
                    "query": question,
                    "should_hit": hit,
                    "label_reason": "Same current fact"
                    if hit
                    else "Historical facts are not supplied"
                    if category == "similar_different"
                    else "Outside municipal transit reference scope",
                }
            )
    write_once(ROOT / "cache_cases.yaml", {"schema": 1, "anchors": anchors, "cases": cases}, True)
    records = [
        {"route": route, "severity": severity, "delay_minutes": delay, "status": "open", "agency": "VTA"}
        for route, severity, delay in [(2, 3, 12), (3, 4, 25), (4, 2, 8), (5, 1, 4)]
    ]
    write_once(
        DATA / "reference_data.json",
        {
            "source": "Synthetic municipal transit exercise facts",
            "records": records,
            "historical_data_available": False,
        },
    )
    splits = {
        "training": [
            "What is the severity and agency of the Route 2 incident?",
            "Give the severity and agency for the Route 3 incident.",
        ],
        "validation": [
            "What is the severity and agency of the Route 4 incident?",
            "What is the delay of the Route 2 incident?",
            "How do I bake a cake?",
            "What is the current status of the Route 3 incident?",
        ],
        "test": [
            "State the severity and agency of the Route 5 incident.",
            "What is the delay of the Route 3 incident?",
            "What is the current status of the Route 4 incident?",
            "Who won the World Cup?",
        ],
    }
    for split, questions in splits.items():
        write_once(
            DATA / f"{split}_data.json", [{"id": f"{split}-{i + 1}", "question": q} for i, q in enumerate(questions)]
        )
    frozen = hashlib.sha256((ROOT / "cache_cases.yaml").read_bytes()).hexdigest()
    save(
        "dataset_manifest.json",
        {
            "cache_cases_sha256": frozen,
            "cases": 40,
            "labels": {"exact": 10, "paraphrase": 10, "similar_different": 10, "unrelated": 10},
            "split_sha256": {
                split: hashlib.sha256((DATA / f"{split}_data.json").read_bytes()).hexdigest() for split in splits
            },
        },
    )
    REPORT.mkdir(parents=True, exist_ok=True)
    event("Datasets prepared before threshold results", cache_cases_sha256=frozen, cases=40)


if __name__ == "__main__":
    prepare()
