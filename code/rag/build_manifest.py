"""Build the required HW3 corpus manifest."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIRECTORY = ROOT / "data" / "hw03" / "corpus"
OUTPUT_PATH = (
    ROOT
    / "reports"
    / "hw03"
    / "CORPUS_MANIFEST.json"
)

MINIMUM_BYTES = 200 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(
            lambda: file.read(1024 * 1024),
            b""
        ):
            digest.update(block)

    return digest.hexdigest()


def main() -> None:
    files = sorted(
        path
        for path in CORPUS_DIRECTORY.iterdir()
        if path.is_file()
    )

    records = [
        {
            "filename": path.name,
            "byte_size": path.stat().st_size,
            "sha256": sha256_file(path)
        }
        for path in files
    ]

    total_bytes = sum(
        record["byte_size"]
        for record in records
    )

    manifest = {
        "domain_id": 2,
        "domain": "Municipal transit incidents",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "minimum_required_bytes": MINIMUM_BYTES,
        "total_bytes": total_bytes,
        "meets_size_requirement": (
            total_bytes >= MINIMUM_BYTES
        ),
        "files": records
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_PATH.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8"
    )

    print(json.dumps(manifest, indent=2))

    if not manifest["meets_size_requirement"]:
        raise SystemExit(
            "Corpus does not meet the 200 KB requirement."
        )


if __name__ == "__main__":
    main()