"""Display selected REAL saved HW8 evidence for screenshots; never changes files or reruns work."""

import argparse
import json

from backend.hw08_common import RAW, ROOT


def read(name):
    return json.loads((RAW / name).read_text(encoding="utf-8"))


def show(label, value):
    if isinstance(value, (dict, list)):
        print(label + ": " + json.dumps(value, ensure_ascii=True))
    else:
        print(f"{label}: {value}")


def events():
    result = []
    for path in RAW.glob("events_*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                result.append(json.loads(line))
            except ValueError:
                continue
    return sorted(result, key=lambda item: item["timestamp"])


def flow():
    demo = read("rpc_demo.json")
    rows = events()
    for kind in ("create", "get"):
        cid = demo[f"{kind}_request"]["correlation_id"]
        print("\n" + demo[f"{kind}_request"]["operation"] + " correlation_id=" + cid)
        needed = {
            ("api", "request_sent"),
            ("worker", "request_received"),
            ("worker", "request_processed"),
            ("worker", "response_sent"),
            ("api", "response_received"),
            ("api", "client_response"),
        }
        found = set()
        for row in rows:
            message = row.get("message", {})
            key = (row["component"], row["event"])
            if (
                isinstance(message, dict)
                and message.get("correlation_id") == cid
                and key in needed
                and key not in found
            ):
                topic = " topic=" + row["topic"] if row.get("topic") else ""
                success = " success=" + str(message["success"]).lower() if "success" in message else ""
                print(f"{row['timestamp']} {row['component']}.{row['event']}{topic} cid={cid}{success}")
                found.add(key)
        if found != needed:
            raise ValueError(f"Missing flow events for {cid}: {needed - found}")


def pipeline():
    data = read("pipeline_journey.json")
    cid = data["request"]["correlation_id"]
    show("question", data["request"]["question"])
    show("correlation_id", cid)
    for row in events():
        message = row.get("message", {})
        if row["event"] == "sent" and isinstance(message, dict) and message.get("correlation_id") == cid:
            print(f"{row['timestamp']} {row['component']} -> {row.get('topic')}; correlation_id={cid}")
    show("final JSON", {key: data["final"][key] for key in ("correlation_id", "status", "answer")})


def duplicate():
    data = read("duplicate_delivery.json")
    for mode, row in data.items():
        print("\n" + mode.upper())
        show("correlation_id", row["first"]["correlation_id"])
        show("first UUID", row["first"]["incident_id"])
        show("replay UUID", row["replay"]["incident_id"])
        show("incident_count", row["incident_count"])
        show("same_uuid", row["same_uuid"])


def death():
    data = read("consumer_death.json")
    all_events = events()
    for mode, row in data.items():
        print("\n" + mode.upper())
        for key in (
            "correlation_id",
            "source_offset",
            "committed_next_offset_at_kill",
            "unsafe_early_commit",
            "lost_before_fix",
            "following_marker_completed",
            "redelivered_and_completed",
        ):
            if key in row:
                show(key, row[key])
        token = row["group"].split("_")[-1]
        for event in all_events:
            if event["component"] == "experiments" and token in event.get("instance", ""):
                print(f"{event['timestamp']} {event['event']} instance={event['instance']} pid={event['pid']}")
        if "commit" in row:
            show("completed at", row["completed"]["timestamp"])
            show(
                "offset committed afterward",
                {"timestamp": row["commit"]["timestamp"], "next_offset": row["commit"]["next_offset"]},
            )


def poison():
    data = read("poison_message.json")
    show("BEFORE event", data["before"]["blocked"])
    for row in data["after"]["retry_events"]:
        show("AFTER retry", {key: row[key] for key in ("timestamp", "attempt", "error", "correlation_id", "offset")})
    message = data["after"]["dead_letter"]["message"]
    cid = message["correlation_id"]
    matches = [
        row for row in events() if row["event"] == "dead_letter" and row.get("message", {}).get("correlation_id") == cid
    ]
    if not matches:
        raise ValueError("No matching dead-letter publish log exists")
    show(
        "dead-letter publish",
        {
            "timestamp": matches[0]["timestamp"],
            "topic": matches[0]["topic"],
            **{
                key: message[key]
                for key in ("correlation_id", "success", "error", "attempts", "source_topic", "offset")
            },
        },
    )
    later = data["after"]["later_message"]
    show("later valid message", {key: later[key] for key in ("timestamp", "event", "correlation_id", "source_offset")})


def ordering(mode):
    data = read(f"ordering_{mode}.json")
    for key in ("verify_seed", "group", "two_writer_instances", "key", "partitions", "observed_sequence", "in_order"):
        show(key, data[key])
    show("record_count", len(data["records"]))
    print("sequence  completed_at_index  partition  writer")
    for row in data["records"]:
        print(f"{row['sequence']:8}  {row['observed_order']:18}  {row['source_partition']:9}  {row['writer']}")


def verification():
    data = json.loads((ROOT / "reports/hw08/verification.json").read_text(encoding="utf-8"))
    for key in ("homework", "sid4", "commit_hash", "seed", "verify_seed", "mode", "timestamp"):
        show(key, data[key])
    show("configuration", data["configuration"])
    for check in data["checks"]:
        print(("PASS " if check["passed"] else "FAIL ") + check["name"])
    show("overall_pass", data["overall_pass"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "section",
        choices=[
            "rpc",
            "flow",
            "pipeline",
            "duplicate",
            "death",
            "poison",
            "ordering-unkeyed",
            "ordering-keyed",
            "verify",
            "errors",
        ],
    )
    args = parser.parse_args()
    print(f"Priyank Mehta - HW8 {args.section} - selected saved real-run evidence")
    print("Source: reports/hw08/raw/ and reports/hw08/verification.json; no experiments rerun.\n")
    if args.section == "rpc":
        data = read("rpc_demo.json")
        for key, row in data.items():
            show(key, row)
    elif args.section == "errors":
        data = json.loads((ROOT / "reports/hw08/verification.json").read_text(encoding="utf-8"))
        for row in data["checks"]:
            if "response" in row:
                show(row["name"], row["response"])
    elif args.section.startswith("ordering-"):
        ordering(args.section.split("-", 1)[1])
    else:
        {
            "flow": flow,
            "pipeline": pipeline,
            "duplicate": duplicate,
            "death": death,
            "poison": poison,
            "verify": verification,
        }[args.section]()


if __name__ == "__main__":
    main()
