"""HW9 miss path uses the existing HW8 inbox -> tasks -> drafts -> final pipeline."""

import asyncio
from uuid import uuid4

from .hw08_common import FINAL, INBOX, consumer, decode, producer
from .hw09_common import event


class KafkaAnswerPipeline:
    async def answer(self, question, context):
        cid = str(uuid4())
        reader = consumer(FINAL, f"s2562_hw09_observer_{cid}", auto_offset_reset="latest")
        sender = producer()
        await sender.start()
        try:
            await reader.start()
            try:
                async with asyncio.timeout(180):
                    while not reader.assignment():
                        await asyncio.sleep(0.05)
                    for tp in reader.assignment():
                        await reader.seek_to_end(tp)
                    message = {
                        "correlation_id": cid,
                        "question": question,
                        "related_entity": str((context.get("record") or {}).get("id", "unknown")),
                        "hw09_context": context,
                        "hw09_local_model": True,
                    }
                    await sender.send_and_wait(INBOX, message, key=message["related_entity"].encode())
                    event("pipeline_miss_sent", correlation_id=cid, question=question)
                    async for record in reader:
                        result = decode(record.value)
                        if result.get("correlation_id") == cid:
                            if result.get("status") != "approved":
                                raise ValueError("Pipeline result not approved")
                            event("pipeline_final", correlation_id=cid, answer=result["answer"])
                            return {"answer": result["answer"], "correlation_id": cid}
            finally:
                await reader.stop()
        finally:
            await sender.stop()
