"""Generate exact source ranges and ordered capture instructions after implementation."""

import ast

from backend.hw09_common import REPORT, ROOT


def locations(file, names):
    found = []

    def visit(node, parent=""):
        qualified = parent
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            qualified = f"{parent}.{node.name}" if parent else node.name
            if qualified in names or node.name in names:
                found.append(f"{qualified}: {node.lineno}-{node.end_lineno}")
        for child in ast.iter_child_nodes(node):
            visit(child, qualified)

    visit(ast.parse((ROOT / file).read_text(encoding="utf-8")))
    return "; ".join(found)


def build():
    lines = [
        "# HW9 screenshot capture order",
        "",
        "Complete the live experiments and verification before taking result screenshots. "
        "The PDF asks for code and output for every part, but does not prescribe a fixed screenshot count. "
        "This guide plans 29 captures, including code evidence, plus two optional captures.",
        "",
        "Use Win+Shift+S and paste directly into your rough Word document. Keep the caption below each image. "
        "Every terminal capture must show Priyank Mehta. The capture helper prints the name automatically. "
        "Code screenshots must show the file breadcrumb, line numbers, and readable text. "
        "Split a long function into adjacent images rather than shrinking it until unreadable.",
        "",
        'Open PowerShell and run `cd "D:\\Grad Prep\\SJSU\\GitHub\\data260-2562"`. '
        "Commands below show saved real results; they do not rerun experiments or alter measurements.",
        "",
    ]
    captures = [
        (
            "Infrastructure",
            None,
            None,
            None,
            "Open Docker Desktop > Containers. Expand s2562-hw09-cache and s2562-hw08. "
            'In PowerShell run `Write-Output "Priyank Mehta - HW9 services"`, '
            "`docker compose -f docker-compose.hw09.yml ps`, and "
            "`docker compose -f docker-compose.hw08.yml ps`, and "
            "`Invoke-RestMethod http://127.0.0.1:8762/api/hw09/health | ConvertTo-Json`. "
            "Capture Redis, Kafka, the three agent services, and the enabled HW9 API. "
            "The API runs on the host at port 8762; the older Compose API is stopped to free that port.",
            "HW9 service deployment",
        ),
        (
            "Part 1 counter code",
            "backend/hw09_database.py",
            ["increment_incident_views"],
            None,
            "",
            "Part 1 - Atomic Redis access counter and every-tenth MySQL synchronization",
        ),
        (
            "Part 1 counter results",
            None,
            None,
            "counter",
            "",
            "Part 1 - 25 accesses, Redis totals, and MySQL checkpoints",
        ),
        (
            "Part 2 vector index and lookup code",
            "backend/hw09_cache.py",
            ["SemanticCache.__init__", "SemanticCache.lookup"],
            None,
            "",
            "Part 2 - Redis FLOAT32 cosine vector index and similarity lookup",
        ),
        (
            "Part 2 cache ingress code",
            "backend/hw09_cache.py",
            ["query"],
            None,
            "",
            "Part 2 - Cache hit bypass and Kafka pipeline miss path",
        ),
        (
            "Part 2 local-model integration code",
            "backend/hw09_model.py",
            ["generate"],
            None,
            "Also open backend/hw08_agents.py at the hw09_local_model branch. Capture it alongside the adapter if readable.",
            "Part 2 - Local Ollama adapter invoked inside the existing HW8 Writer",
        ),
        ("Part 2 query results", None, None, "cache", "", "Part 2 - Exact duplicates, paraphrases, and new questions"),
        (
            "Part 2 measured performance",
            None,
            None,
            "performance",
            "",
            "Part 2 - Measured cache hit rate and cached versus noncached latency",
        ),
        (
            "Part 3.1 fixed labeled cases",
            "cache_cases.yaml",
            [],
            None,
            "Open cache_cases.yaml. Capture one example from each category; use Find for exact, paraphrase, "
            "similar_different, and unrelated. Include should_hit and label_reason. "
            "Use adjacent panes if four examples do not fit one view.",
            "Part 3.1 - Frozen labels across four ten-case categories",
        ),
        (
            "Part 3.1 commit proof",
            None,
            None,
            None,
            "Open GitHub Desktop > History > the Freeze HW9 labeled cache cases commit. "
            "Select cache_cases.yaml and capture the commit identifier and labeled file. "
            "Take this immediately after the pre-sweep commit; retain it for the report.",
            "Part 3.1 - Labeled cases committed before the threshold sweep",
        ),
        (
            "Part 3.2 sweep code",
            "code/hw09_experiments.py",
            ["committed_cases", "sweep"],
            None,
            "For sweep(), capture the threshold loop and per-case hit/false-hit metrics, not the entire function.",
            "Part 3.2 - Committed-label guard and five-threshold experiment",
        ),
        (
            "Part 3.2 threshold table",
            None,
            None,
            "thresholds",
            "",
            "Part 3.2 - Hit rate, false-hit rate, latency, and cost at five thresholds",
        ),
        (
            "Part 3.3 full false hit",
            None,
            None,
            "falsehit",
            "Show incoming query, cached_query, similarity, returned answer, correct answer, and explanation. "
            "Capture in two adjacent images if needed.",
            "Part 3.3 - A false semantic hit and the correct answer",
        ),
        (
            "Part 3.4 cost calculation code",
            "code/hw09_experiments.py",
            ["sweep"],
            None,
            "Capture false-hit counting, total_cost, and the min-cost choice near the end of sweep().",
            "Part 3.4 - Explicit miss and support costs with threshold selection",
        ),
        (
            "Part 3.4 threshold choice",
            None,
            None,
            "cost",
            "",
            "Part 3.4 - Selected threshold and justified cost assumptions",
        ),
        (
            "Part 3.5 version invalidation code",
            "backend/hw09_cache.py",
            ["lookup"],
            None,
            "Place backend/hw09_database.py update_fixture beside lookup(). Include version comparison and version increment.",
            "Part 3.5 - Stored data-version validation after a relational update",
        ),
        (
            "Part 3.5 stale and corrected results",
            None,
            None,
            "stale",
            "",
            "Part 3.5 - Old cached answer, stale hit, invalidation miss, and fresh hit",
        ),
        (
            "Part 4 datasets",
            "reports/hw09/data/reference_data.json",
            [],
            None,
            "In VS Code, open the reference file and training_data.json, validation_data.json, test_data.json "
            "from the same directory. Use two or four editor panes. Show reference facts and that input files contain only id/question.",
            "Part 4 - Ground truth and separate question-only dataset splits",
        ),
        (
            "Part 4.1 answering and evaluator code",
            "backend/hw09_agents.py",
            ["AnsweringAgent", "evaluate"],
            None,
            "",
            "Part 4.1 - Answer generation and reference-grounded PASS or REVISE evaluation",
        ),
        (
            "Part 4.1 revision and stopping code",
            "backend/hw09_agents.py",
            ["run_two_agents"],
            None,
            "",
            "Part 4.1 - Evaluator feedback and the maximum of two answer attempts",
        ),
        (
            "Part 4.1 complete revision sequence",
            None,
            None,
            "revision",
            "Capture question, intentionally incomplete initial answer, evaluator feedback, second answer, "
            "final result, and attempt_count. Use two images if necessary.",
            "Part 4.1 - Controlled failure repaired using evaluator feedback",
        ),
        (
            "Part 4.2 lesson storage and loading code",
            "backend/hw09_agents.py",
            ["LessonMemory", "candidate_lesson"],
            None,
            "",
            "Part 4.2 - Reusable lesson fields, persistence, matching, and use count",
        ),
        (
            "Part 4.2 lesson reuse",
            None,
            None,
            "lessons",
            "",
            "Part 4.2 - Stored lesson loaded for a later related question",
        ),
        (
            "Part 4.3 validation gate code",
            "backend/hw09_agents.py",
            ["validate_lesson"],
            None,
            "Also show code/hw09_part4.py selecting the lesson before reading final test questions.",
            "Part 4.3 - Validation gate protects correct and unrelated answers",
        ),
        (
            "Part 4.3 validation results",
            None,
            None,
            "validation",
            "",
            "Part 4.3 - Before/after validation and the keep-or-reject decision",
        ),
        (
            "Part 4.4 independent variant code",
            "code/hw09_part4.py",
            ["run"],
            None,
            "Capture the four-variant loop, independent memory files, identical test questions, and summary calculation.",
            "Part 4.4 - Four independently evaluated system variants",
        ),
        (
            "Part 4.4 final comparison",
            None,
            None,
            "variants",
            "",
            "Part 4.4 - Held-out correctness, attempts, and measured latency",
        ),
        (
            "Verification code",
            "code/verify_hw09.py",
            ["verify"],
            None,
            "Capture checks for 40 cases, 200 records, stale invalidation, four variants, and the two-attempt bound.",
            "HW9 objective verification checks",
        ),
        (
            "Verification results",
            None,
            None,
            "verify",
            "Capture only after mode is live-evidence and overall_pass is true. Offline mode is not final submission proof.",
            "HW9 final verification metadata and passing checks",
        ),
    ]
    for number, (title, file, names, section, extra, caption) in enumerate(captures, 1):
        lines += [f"## Screenshot {number} - {title}", ""]
        if file:
            lines += [f"In VS Code choose File > Open File and open `{ROOT / file}`.", ""]
            if names:
                lines += [f"Use Ctrl+G for these exact ranges: {locations(file, names)}.", ""]
        if section:
            lines += [f"Run `.\\.venv\\Scripts\\python.exe -m code.hw09_capture {section}`.", ""]
        if extra:
            lines += [extra, ""]
        lines += [f"Caption: **{caption}**", ""]
    lines += [
        "## Optional A - Actual MySQL checkpoint row",
        "",
        "Open MySQL Workbench, open your existing connection, and run "
        "`SELECT id, incident_code, view_count, cache_version FROM s2562_rel.incidents "
        "WHERE incident_code LIKE 'HW9-ROUTE-%';`. Capture the grid after the counter demonstration. "
        "The last persisted count is a multiple of ten; the terminal shows the more recent Redis count.",
        "",
        "Caption: **Part 1 - MySQL stores the last completed ten-access checkpoint**",
        "",
        "## Optional B - Authenticated cache API",
        "",
        "Open http://127.0.0.1:8762/docs. Use your HW7 login flow and Authorize with an access token. "
        "Expand HW9 Redis and agents > POST /api/hw09/qa > Try it out. Enter "
        '`{"question":"What is the current severity of the Route 2 incident?"}` and execute twice. '
        "Capture the request and response flag, similarity, and latency. Do not include a token in the screenshot.",
        "",
        "Caption: **Part 2 - Authenticated semantic-cache endpoint response**",
        "",
        "## Required report content beyond screenshots",
        "",
        "Keep the GitHub link, six configuration values, hardware, local model, and tested/tagged commit at the top. "
        "Use 14 pt bold main headings, 12 pt bold subheadings, and 11 pt body text.",
        "",
        "Include the measured Part 2 hit rate and both average latencies; the five-row threshold table; "
        "one complete false hit; justified costs and threshold choice; stale-answer/version trade-off; "
        "the four-variant results table; and a short Part 4 explanation of communication, reuse, "
        "stopping, validation, and one limitation. Include the current AI_USE.md text.",
        "",
        "Place each code image immediately above its relevant output image. Captures 19 and 20 precede 21; "
        "22 precedes 23; 24 precedes 25; 26 precedes 27. Preserve original image resolution in the Word file.",
    ]
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "SCREENSHOTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Priyank Mehta - 29 planned captures plus two optional captures; exact source ranges generated")


if __name__ == "__main__":
    build()
