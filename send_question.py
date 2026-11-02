"""Send to inbox and read final JSON, preserving correlation_id through each process."""

import argparse
import asyncio
import json
from uuid import uuid4

from backend.hw08_common import FINAL, INBOX, RAW, consumer, decode, emit, producer


async def send_question(question="How should transit staff handle a Route 2 signal delay?"):
    cid = str(uuid4())
    reader, sender = consumer(FINAL, f"s2562_final_observer_{uuid4()}"), producer()
    await sender.start()
    await reader.start()
    try:
        request = {"correlation_id": cid, "question": question, "related_entity": "route-2"}
        await sender.send_and_wait(INBOX, request, key=b"route-2")
        emit("question", "sent", topic=INBOX, message=request)
        async with asyncio.timeout(45):
            async for record in reader:
                result = decode(record.value)
                if result.get("correlation_id") == cid:
                    assert result.get("status") == "approved" and result.get("answer")
                    emit("question", "final_received", topic=FINAL, message=result)
                    RAW.mkdir(parents=True, exist_ok=True)
                    (RAW / "pipeline_journey.json").write_text(
                        json.dumps({"request": request, "final": result}, indent=2), encoding="utf-8"
                    )
                    return result
    finally:
        await reader.stop()
        await sender.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("question", nargs="?", default="How should transit staff handle a Route 2 signal delay?")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(send_question(args.question)), indent=2))
