"""Dictionary-backed CREATE_INCIDENT / GET_INCIDENT worker; manual offset commit."""

import argparse
import asyncio

from aiokafka import TopicPartition

from .hw08_common import DEAD_LETTER, REQUESTS, RESPONSES, consumer, decode, emit, producer
from .hw08_incidents import IncidentService


async def run_worker(group="s2562_incident_worker", instance="worker", idempotent=True, start_latest=False):
    service = IncidentService(idempotent=idempotent)
    reader, sender = consumer(REQUESTS, group, auto_offset_reset="latest" if start_latest else "earliest"), producer()
    await sender.start()
    await reader.start()
    async with asyncio.timeout(30):
        while not reader.assignment():
            await asyncio.sleep(0.1)
        for tp in reader.assignment():
            position = await reader.position(tp)
            if await reader.committed(tp) is None:
                await reader.commit({tp: position})
    emit(instance, "ready", message="Consumer is ready and listening...", topic=REQUESTS)
    try:
        async for record in reader:
            try:
                request = decode(record.value)
            except (ValueError, TypeError, UnicodeError) as exc:
                await sender.send_and_wait(
                    DEAD_LETTER,
                    {
                        "success": False,
                        "error": str(exc),
                        "source_topic": record.topic,
                        "offset": record.offset,
                        "raw": (record.value or b"").decode(errors="replace"),
                    },
                )
            else:
                emit(
                    instance,
                    "request_received",
                    topic=record.topic,
                    partition=record.partition,
                    offset=record.offset,
                    message=request,
                )
                response = service.process(request)
                emit(instance, "request_processed", message=response, incident_count=len(service.incidents))
                # Only the assigned reply topic is allowed: the exercise uses exactly two RPC topics.
                await sender.send_and_wait(RESPONSES, response, key=str(request.get("correlation_id")).encode())
                emit(instance, "response_sent", topic=RESPONSES, message=response)
            await reader.commit({TopicPartition(record.topic, record.partition): record.offset + 1})
            emit(instance, "offset_committed", partition=record.partition, next_offset=record.offset + 1)
    finally:
        await reader.stop()
        await sender.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", default="s2562_incident_worker")
    parser.add_argument("--instance", default="worker")
    parser.add_argument("--disable-idempotency", action="store_true", help="Before-fix experiment only")
    parser.add_argument("--start-latest", action="store_true")
    args = parser.parse_args()
    asyncio.run(run_worker(args.group, args.instance, not args.disable_idempotency, args.start_latest))
