"""Concurrent Kafka RPC with caller-generated correlation IDs and bounded timeouts."""

import asyncio
import contextlib
from uuid import uuid4

from .hw08_common import REQUESTS, RESPONSES, consumer, decode, emit, producer


class KafkaRPC:
    def __init__(self, component="api"):
        self.component, self.pending = component, {}

    async def start(self):
        self.producer = producer()
        # A unique response group broadcasts replies to every API instance. Each filters its own pending IDs.
        self.consumer = consumer(RESPONSES, f"s2562_rpc_{uuid4()}", auto_offset_reset="latest")
        await self.producer.start()
        try:
            await self.consumer.start()
            # Ensure partition assignment and latest position BEFORE a request can be sent.
            for _ in range(100):
                await self.consumer.getmany(timeout_ms=100)
                if self.consumer.assignment():
                    break
            else:
                raise TimeoutError("Response consumer received no partition assignment")
            self.task = asyncio.create_task(self.receive())
        except BaseException:
            await self.consumer.stop()
            await self.producer.stop()
            raise
        emit(self.component, "ready", topic=RESPONSES)

    async def stop(self):
        self.task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self.task
        for future in self.pending.values():
            if not future.done():
                future.set_exception(ConnectionError("RPC stopped"))
        await self.consumer.stop()
        await self.producer.stop()

    async def receive(self):
        async for message in self.consumer:
            try:
                data = decode(message.value)
            except (ValueError, TypeError, UnicodeError) as exc:
                emit(self.component, "invalid_response", error=str(exc), topic=message.topic, offset=message.offset)
                continue
            future = self.pending.get(data.get("correlation_id"))
            if future is not None and not future.done():
                emit(
                    self.component,
                    "response_received",
                    topic=message.topic,
                    partition=message.partition,
                    offset=message.offset,
                    message=data,
                )
                future.set_result(data)

    async def request(self, request, timeout=15):
        cid = request.get("correlation_id")
        if not isinstance(cid, str) or not cid.strip():
            return {"correlation_id": cid, "success": False, "error": "correlation_id is required"}
        if cid in self.pending:
            return {"correlation_id": cid, "success": False, "error": "correlation_id is already in flight"}
        future = asyncio.get_running_loop().create_future()
        self.pending[cid] = future
        try:
            emit(self.component, "request_sent", topic=REQUESTS, message=request)
            await asyncio.wait_for(self.producer.send_and_wait(REQUESTS, request, key=cid.encode()), timeout=timeout)
            response = await asyncio.wait_for(future, timeout=timeout)
            emit(self.component, "client_response", message=response)
            return response
        except (TimeoutError, OSError) as exc:
            return {"correlation_id": cid, "success": False, "error": f"Kafka request failed: {type(exc).__name__}"}
        finally:
            self.pending.pop(cid, None)


def make_request(operation, data, correlation_id=None):
    return {
        "correlation_id": str(uuid4()) if correlation_id is None else correlation_id,
        "reply_to": RESPONSES,
        "operation": operation,
        "data": data,
    }
