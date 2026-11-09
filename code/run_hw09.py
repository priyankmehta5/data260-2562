"""Logged automation phases. Never commits or pushes; never sweeps uncommitted labels."""

import argparse
import subprocess
import sys

from backend.hw09_common import REPORT, ROOT, now


def command(args):
    REPORT.mkdir(parents=True, exist_ok=True)
    with (REPORT / "RUN_LOG.txt").open("a", encoding="utf-8") as log:
        heading = f"\n[{now()}] Priyank Mehta COMMAND: {subprocess.list2cmdline(args)}"
        print(heading, flush=True)
        log.write(heading + "\n")
        process = subprocess.Popen(
            args,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        for line in process.stdout:
            print(line.rstrip(), flush=True)
            log.write(line)
            log.flush()
        code = process.wait()
        log.write(f"[{now()}] EXIT {code}\n")
    if code:
        raise RuntimeError(f"Command failed with exit code {code}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["prepare", "baseline", "agents", "sweep", "verify"])
    parser.add_argument("--offline", action="store_true", help="Only applicable to verification")
    args = parser.parse_args()
    calls = {
        "prepare": ["-m", "code.hw09_prepare"],
        "baseline": ["-m", "code.hw09_experiments", "baseline"],
        "agents": ["-m", "code.hw09_part4"],
        "sweep": ["-m", "code.hw09_experiments", "sweep"],
        "verify": ["verify_hw09.py"],
    }
    command([sys.executable, *calls[args.phase], *(["--offline"] if args.offline and args.phase == "verify" else [])])
    if args.phase in ["baseline", "agents", "sweep"]:
        command([sys.executable, "-m", "code.hw09_metrics"])


if __name__ == "__main__":
    main()
