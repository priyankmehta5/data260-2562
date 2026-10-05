"""Run the DATA 260 HW5 verification checks from the repository root."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
VERIFICATION = ROOT / "reports" / "hw05" / "verification.json"
RAW = ROOT / "reports" / "hw05" / "raw"


def live_api_check():
    try:
        with urlopen("http://127.0.0.1:8762/", timeout=3) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status == 200 and "HW5 API is running" in body, body
    except Exception as error:  # The caller receives a useful manual-start message.
        return False, str(error)


def inspector_evidence_check():
    meals = RAW / "inspector-meals-complete.json"
    transit = RAW / "inspector-transit-complete.json"
    required_meals = ("search_meals_by_name", "meals_by_ingredient", "random_meal", "meal_details")
    required_transit = ("search_incidents", "incident_detail", "incident_aggregate")
    meals_text = meals.read_text(encoding="utf-8") if meals.exists() else ""
    transit_text = transit.read_text(encoding="utf-8") if transit.exists() else ""
    passed = all(name in meals_text for name in required_meals) and all(name in transit_text for name in required_transit)
    return passed, {"meals_export": meals.name if meals.exists() else None, "transit_export": transit.name if transit.exists() else None}


def main():
    result = subprocess.run([sys.executable, "code/verify_hw05.py"], cwd=ROOT, text=True)
    if not VERIFICATION.exists():
        return result.returncode or 1

    payload = json.loads(VERIFICATION.read_text(encoding="utf-8"))
    api_passed, api_detail = live_api_check()
    inspector_passed, inspector_detail = inspector_evidence_check()
    payload["checks"].extend([
        {"name": "FastAPI smoke test on port 8762", "passed": api_passed, "detail": api_detail},
        {"name": "MCP Inspector tool-call evidence", "passed": inspector_passed, **inspector_detail},
    ])
    payload["overall_pass"] = all(item.get("passed") for item in payload["checks"])
    VERIFICATION.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if not api_passed:
        print("MANUAL ACTION: start the backend on port 8762, then rerun verify.py.")
    return 0 if payload["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
