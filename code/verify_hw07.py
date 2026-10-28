"""Objective HW7 smoke tests and raw-evidence checks."""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports" / "hw07"
RAW = REPORTS / "raw"


def check(name, passed, **extra):
    return {"name": name, "passed": bool(passed), **extra}


def live_auth_smoke():
    base = "http://127.0.0.1:8762"

    def request(path, method="GET", body=None, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request_obj = urllib.request.Request(
            base + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request_obj, timeout=5) as response:
                return response.status, json.loads(response.read().decode())
        except urllib.error.HTTPError as error:
            return error.code, None

    no_token, _ = request("/auth/me")
    invalid_login, _ = request("/auth/login", "POST", {"username": "student@example.com", "password": "invalid"})
    valid_login, payload = request(
        "/auth/login", "POST", {"username": "student@example.com", "password": "Transit2562!"}
    )
    me_status, me_payload = request("/auth/me", token=payload.get("access_token") if payload else None)
    passed = (
        no_token == 401
        and invalid_login == 401
        and valid_login == 200
        and me_status == 200
        and bool(me_payload and me_payload.get("role"))
    )
    return passed, {
        "no_token": no_token,
        "invalid_login": invalid_login,
        "valid_login": valid_login,
        "me": me_status,
        "role": me_payload.get("role") if me_payload else None,
    }


def main():
    REPORTS.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    tests = subprocess.run([sys.executable, "code/hw07_tools.py"], cwd=ROOT, capture_output=True, text=True)
    checks = [
        check("HW7 offline evidence generator", tests.returncode == 0, output=(tests.stdout + tests.stderr)[-2500:])
    ]
    required = [
        "verification_tasks.json",
        "error_recovery.json",
        "reliability_attempts.json",
        "reliability_summary.json",
        "reflexion_comparison.json",
        "reflections.json",
        "bike_share_scenarios.json",
        "prompt_injection_results.json",
        "file_tool_tests.json",
        "agent_tool_logs.jsonl",
        "tool_schemas.json",
    ]
    checks.append(check("required raw evidence files", all((RAW / name).exists() for name in required)))
    checks.append(
        check(
            "three verification tasks",
            len(json.loads((RAW / "verification_tasks.json").read_text(encoding="utf-8"))) == 3,
        )
    )
    checks.append(
        check(
            "20 reliability attempts",
            len(json.loads((RAW / "reliability_attempts.json").read_text(encoding="utf-8"))) == 20,
        )
    )
    checks.append(
        check(
            "two bike-share scenarios with 500 rows",
            all(
                item["rows"] >= 500
                for item in json.loads((RAW / "bike_share_scenarios.json").read_text(encoding="utf-8"))
            ),
        )
    )
    checks.append(
        check(
            "three prompt-injection attacks",
            len(json.loads((RAW / "prompt_injection_results.json").read_text(encoding="utf-8"))) == 3,
        )
    )
    file_tests = json.loads((RAW / "file_tool_tests.json").read_text(encoding="utf-8"))
    checks.append(
        check(
            "file-tool integration and 5/5 safety gate",
            file_tests["integration"]["read_contains_DEBUG"]
            and file_tests["pass_count"] == 5
            and file_tests["blocked_count"] == 5,
        )
    )
    checks.append(
        check(
            "JWT implementation present",
            all(
                (ROOT / name).exists()
                for name in ("backend/hw07_auth.py", "backend/routes_hw07.py", "backend/migrate_hw07.py")
            ),
        )
    )
    checks.append(check("ReAct UI present", (ROOT / "frontend/src/HW7BikeShare.jsx").exists()))
    checks.append(
        check(
            "lint configuration present",
            (ROOT / ".pre-commit-config.yaml").exists() and (ROOT / "pyproject.toml").exists(),
        )
    )
    checks.append(check("written threat model present", (REPORTS / "THREAT_MODEL.md").exists()))
    tool_source = (ROOT / "code/hw07_tools.py").read_text(encoding="utf-8")
    ui_source = (ROOT / "frontend/src/HW7BikeShare.jsx").read_text(encoding="utf-8")
    checks.append(
        check(
            "HW1 adapter and tool-role support present",
            "create_hw1_model_adapter" in tool_source and '"role": "tool"' in tool_source,
        )
    )
    checks.append(
        check(
            "ReAct UI evidence fields present",
            all(marker in ui_source for marker in ("weekly", "justification", "pricingHash", "captureDate")),
        )
    )
    attack_rows = json.loads((RAW / "prompt_injection_results.json").read_text(encoding="utf-8"))
    checks.append(
        check(
            "prompt-injection traces present",
            all("before_trace" in row and "after_tool_trace" in row for row in attack_rows),
        )
    )
    live_passed, live_output = live_auth_smoke()
    checks.append(check("live JWT authentication smoke test", live_passed, output=live_output))
    payload = {
        "homework": "7",
        "sid4": "2562",
        "commit_hash": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "model": "qwen3:1.7b",
        "seed": 2562,
        "verify_seed": 262562,
        "checks": checks,
        "overall_pass": all(item["passed"] for item in checks),
    }
    (REPORTS / "verification.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if payload["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
