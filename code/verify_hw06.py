"""Objective HW6 verification and offline evidence generator."""
from __future__ import annotations

import json
import subprocess
import sys
from urllib.request import Request, urlopen
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports" / "hw06"
RAW = REPORTS / "raw"


def check(name, passed, **extra):
    return {"name": name, "passed": bool(passed), **extra}


def live_mongo_check():
    try:
        from pymongo import MongoClient

        client = MongoClient("mongodb://127.0.0.1:27017", serverSelectionTimeoutMS=1500)
        result = client.admin.command("ping")
        client.close()
        return result.get("ok") == 1, result
    except Exception as error:
        return False, str(error)


def live_api_check():
    try:
        with urlopen("http://127.0.0.1:8762/", timeout=3) as response:
            root_ok = response.status == 200
        request = Request(
            "http://127.0.0.1:8762/api/chat",
            data=json.dumps({
                "user_id": "verify-hw06",
                "session_id": "verify-session",
                "message": "verification message",
            }).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            body = json.loads(response.read().decode())
            chat_ok = response.status == 200 and bool(body.get("reply"))
        return root_ok and chat_ok, body
    except Exception as error:
        return False, str(error)


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    checks = []
    test = subprocess.run([sys.executable, "code/hw06_tests.py"], cwd=ROOT, capture_output=True, text=True)
    checks.append(check("offline HW6 tests", test.returncode == 0, output=(test.stdout + test.stderr)[-4000:]))
    experiment = subprocess.run([sys.executable, "code/hw06_experiments.py"], cwd=ROOT, capture_output=True, text=True)
    checks.append(check("memory-cost experiments", experiment.returncode == 0, output=experiment.stdout[-2000:]))
    required = ["memory_cost_records.json", "memory_cost_records.csv", "memory_cost_summary.json", "memory_cost_estimates.json", "chat_token_usage.jsonl"]
    checks.append(check("raw experiment files", all((RAW / name).exists() for name in required)))
    checks.append(check("five memory probes", len((REPORTS / "memory_probes.yaml").read_text(encoding="utf-8").split("- question:") ) - 1 == 5))
    checks.append(check("consolidated memory under 40 lines", len([line for line in (ROOT / "MEMORY.md").read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")]) < 40))
    checks.append(check("agent instructions cover HW6 categories", all(term in (ROOT / "AGENT.md").read_text(encoding="utf-8") for term in ("Project description", "Technology stack", "Coding conventions", "Testing approach", "Prohibited actions"))))
    checks.append(check("HW6 routes present", all(term in (ROOT / "backend/routes_hw06.py").read_text(encoding="utf-8") for term in ("/documents", "/chat", "/memory", "/aggregate"))))
    checks.append(check("memory commands present", all(term in (ROOT / "backend/hw06_file_memory.py").read_text(encoding="utf-8") for term in ("/memory", "/compact", "/dream", "/help"))))
    checks.append(check("original and consolidated memory fixtures", (REPORTS / "MEMORY.original.md").exists() and (REPORTS / "MEMORY.consolidated.md").exists()))
    checks.append(check("memory comparison present", (REPORTS / "COMPARISON.md").exists()))
    mongo_passed, mongo_detail = live_mongo_check()
    checks.append(check("MongoDB ping on 127.0.0.1:27017", mongo_passed, detail=mongo_detail))
    api_passed, api_detail = live_api_check()
    checks.append(check("FastAPI root and POST /api/chat smoke test", api_passed, detail=api_detail))
    payload = {"homework": "6", "sid4": "2562", "commit_hash": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "model": "qwen3:1.7b", "seed": 2562, "verify_seed": 262562, "checks": checks, "overall_pass": all(item["passed"] for item in checks)}
    (REPORTS / "verification.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if payload["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
