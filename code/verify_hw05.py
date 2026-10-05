"""Objective HW5 verification; writes reports/hw05/verification.json."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "reports" / "hw05" / "raw"


def check(name, passed, **extra):
    return {"name": name, "passed": bool(passed), **extra}


def load(name):
    return json.loads((RAW / name).read_text(encoding="utf-8"))


def main():
    checks = []
    result = subprocess.run(
        [sys.executable, "code/hw05_tools.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = (result.stdout + result.stderr)[-3000:]
    checks.append(check("offline test runner", result.returncode == 0, output=output))
    checks.append(check("offline runner reports 8/8", "8/8" in output))

    raw = load("fault_injection.json")
    rates = Counter(round(float(row["rate"]), 1) for row in raw)
    checks.append(check("150 raw records", len(raw) == 150, count=len(raw)))
    checks.append(check("50 calls at each rate", rates == Counter({0.0: 50, 0.2: 50, 0.5: 50}), rates=dict(rates)))
    checks.append(check("retry demonstrations", {row.get("case") for row in load("retry_demonstrations.json")} >= {
        "first_attempt_success", "retry_success", "exhausted_failure"
    }))

    offline = load("offline_agent_scenarios.json")
    checks.append(check("four offline agent scenarios", len(offline) >= 4, count=len(offline)))
    ollama_path = RAW / "ollama_scenarios.json"
    if ollama_path.exists():
        checks.append(check("four local-model scenarios", len(load("ollama_scenarios.json")) >= 4))
    checks.append(check("agent JSONL exists", (RAW / "agent_runs.jsonl").exists()))
    checks.append(check("reflection is 200-300 words", 200 <= len((ROOT / "reports/hw05/REFLECTION.md").read_text(encoding="utf-8").split()) <= 300))

    domain_tests = load("mcp_domain_tests.json")
    checks.append(check("six offline domain cases", len(domain_tests) >= 6))
    checks.append(check("domain cases include valid and invalid for all tools", {
        (row["tool"], row["case"]) for row in domain_tests
    } >= {(tool, case) for tool in ("search", "detail", "aggregate") for case in ("valid", "invalid")}))

    meals_text = (RAW / "inspector-meals-complete.json").read_text(encoding="utf-8") if (RAW / "inspector-meals-complete.json").exists() else ""
    transit_text = (RAW / "inspector-transit-complete.json").read_text(encoding="utf-8") if (RAW / "inspector-transit-complete.json").exists() else ""
    checks.append(check("TheMealDB Inspector export", all(tool in meals_text for tool in (
        "search_meals_by_name", "meals_by_ingredient", "random_meal", "meal_details"
    ))))
    checks.append(check("transit Inspector export", all(tool in transit_text for tool in (
        "search_incidents", "incident_detail", "incident_aggregate"
    ))))

    for path in ("code/mcp/meals_server.py", "code/mcp/transit_server.py", "code/hw05_tools.py"):
        result = subprocess.run([sys.executable, "-m", "py_compile", path], cwd=ROOT, capture_output=True, text=True)
        checks.append(check(path + " syntax", result.returncode == 0, output=result.stderr))

    frontend_package = (ROOT / "frontend/package.json").read_text(encoding="utf-8")
    frontend_source = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "frontend/src").glob("*") if p.is_file())
    checks.append(check("Redux dependencies", '"@reduxjs/toolkit"' in frontend_package and '"react-redux"' in frontend_package))
    checks.append(check("Redux thunks and credentials", "createAsyncThunk" in frontend_source and "withCredentials" in frontend_source))

    required = ["HOMEWORK=5", "SID4=2562", "PORT_BASE=8762", "PREFIX=s2562", "SEED=2562", "VERIFY_SEED=262562"]
    checks.append(check("configuration values recorded", all(value in (ROOT / "reports/hw05/METRICS.md").read_text(encoding="utf-8") or value in (ROOT / "reports/hw05/AI_USE.md").read_text(encoding="utf-8") for value in required)))

    payload = {
        "homework": "5",
        "sid4": "2562",
        "commit_hash": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "model": "qwen3:1.7b",
        "seed": 2562,
        "verify_seed": 262562,
        "checks": checks,
        "overall_pass": all(item["passed"] for item in checks),
    }
    out = ROOT / "reports/hw05/verification.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if payload["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
