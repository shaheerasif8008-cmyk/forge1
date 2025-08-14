from __future__ import annotations

"""Redis Streams-based event bus and RPC transport.

Streams used:
- events.core, events.tasks, events.employees, events.ops, events.rag, events.security
  Each has a corresponding DLQ stream: events.<topic>.dlq

RPC queues:
- rpc.requests, rpc.replies

Envelope:
- CloudEvents v1.0 (see cloudevents.CloudEvent)

Consumer groups:
- One per service/role; caller is responsible for passing group name.

Retry with exponential backoff:
- Message has headers attempts and next_at; failed processing re-adds to stream with delay,
  and after max_attempts goes to DLQ.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Awaitable, Callable

import redis.asyncio as redis

from .cloudevents import CloudEvent

logger = logging.getLogger(__name__)


EVENT_STREAMS = [
    "events.core",
    "events.tasks",
    "events.employees",
    "events.ops",
    "events.rag",
    "events.security",
]

RPC_REQUESTS = "rpc.requests"
RPC_REPLIES = "rpc.replies"


def _dlq_name(stream: str) -> str:
    if stream.startswith("events."):
        return f"{stream}.dlq"
    return f"{stream}.dlq"


async def _ensure_streams(client: redis.Redis) -> None:
    try:
        for s in EVENT_STREAMS + [RPC_REQUESTS, RPC_REPLIES]:
            try:
                # Create stream with MAXLEN ~10k to cap memory in dev
                await client.xadd(s, {"_init": "1"}, maxlen=10000, approximate=True)
            except Exception:
                pass
    except Exception as e:  # noqa: BLE001
        logger.warning(f"ensure_streams failed: {e}")


def _serialize_event(event: CloudEvent) -> dict[str, str]:
    # Store as flat fields for Redis Streams
    payload = event.model_dump()
    return {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in payload.items()}


def _deserialize_event(fields: dict[bytes, bytes]) -> CloudEvent:
    m: dict[str, Any] = {}
    for k_b, v_b in fields.items():
        k = k_b.decode()
        v_s = v_b.decode()
        if k in {"data"}:
            try:
                m[k] = json.loads(v_s)
            except Exception:
                m[k] = {}
        elif k in {"tenant_id", "employee_id", "trace_id", "actor", "subject", "type", "source", "time", "datacontenttype", "specversion", "id", "version"}:
            m[k] = v_s
        elif k in {"ttl"}:
            try:
                m[k] = int(v_s)
            except Exception:
                m[k] = None
        else:
            # unknown extension -> best-effort
            try:
                m[k] = json.loads(v_s)
            except Exception:
                m[k] = v_s
    return CloudEvent(**m)


async def publish_event(client: redis.Redis, stream: str, event: CloudEvent) -> str:
    fields = _serialize_event(event)
    msg_id = await client.xadd(stream, fields, maxlen=10000, approximate=True)
    return msg_id  # type: ignore[return-value]


@dataclass
class RetryPolicy:
    max_attempts: int = 5
    base_delay_ms: int = 250
    max_delay_ms: int = 30_000

    def next_delay_ms(self, attempt: int) -> int:
        # exponential backoff with cap and jitter
        import random as _rand

        delay = min(self.max_delay_ms, self.base_delay_ms * (2 ** max(0, attempt - 1)))
        jitter = int(0.2 * delay * _rand.random())
        return delay + jitter


async def consume_stream(
    client: redis.Redis,
    *,
    stream: str,
    group: str,
    consumer: str,
    handler: Callable[[CloudEvent], Awaitable[bool]],
    retry: RetryPolicy | None = None,
    stop_event: asyncio.Event | None = None,
) -> None:
    """Consume a stream using consumer groups with retry and DLQ.

    The handler should return True on success, False to trigger a retry.
    """
    retry = retry or RetryPolicy()

    # Create group if not exists
    try:
        await client.xgroup_create(stream, group, id="0-0", mkstream=True)
    except Exception:
        pass

    while stop_event is None or not stop_event.is_set():
        try:
            resp = await client.xreadgroup(group, consumer, streams={stream: ">"}, count=50, block=1000)
            if not resp:
                continue
            for _stream_name, messages in resp:
                for msg_id, fields in messages:
                    try:
                        event = _deserialize_event(fields)
                        if event.is_expired():
                            # Acknowledge and drop silently
                            await client.xack(stream, group, msg_id)
                            continue
                        ok = await handler(event)
                        if ok:
                            await client.xack(stream, group, msg_id)
                        else:
                            # schedule retry or DLQ
                            attempts_key = f"attempts"
                            attempts = int(fields.get(attempts_key.encode(), b"0").decode() or "0") + 1
                            if attempts >= retry.max_attempts:
                                await client.xack(stream, group, msg_id)
                                await client.xadd(_dlq_name(stream), fields | {b"error": b"handler_failed"})
                            else:
                                delay_ms = retry.next_delay_ms(attempts)
                                # emulate delayed requeue by sleep and re-add
                                await asyncio.sleep(delay_ms / 1000.0)
                                new_fields = dict(fields)
                                new_fields[b"attempts"] = str(attempts).encode()
                                await client.xadd(stream, new_fields, maxlen=10000, approximate=True)
                                await client.xack(stream, group, msg_id)
                    except Exception as e:  # noqa: BLE001
                        logger.exception("consumer handler error", exc_info=e)
                        try:
                            await client.xack(stream, group, msg_id)
                            await client.xadd(_dlq_name(stream), fields | {b"error": b"exception"})
                        except Exception:
                            pass
        except Exception as e:  # noqa: BLE001
            logger.warning(f"consume_stream error: {e}")


class RpcClient:
    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    async def call(
        self,
        *,
        method: str,
        params: dict[str, Any],
        timeout_ms: int = 5000,
        correlation_id: str | None = None,
        reply_to: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        cid = correlation_id or datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
        reply_stream = reply_to or f"{RPC_REPLIES}.{cid}"
        # Publish request
        req: dict[str, Any] = {
            "method": method,
            "params": params,
            "reply_to": reply_stream,
            "correlation_id": cid,
            "metadata": metadata or {},
        }
        await self._client.xadd(RPC_REQUESTS, {k: json.dumps(v) for k, v in req.items()}, maxlen=10000, approximate=True)
        # Wait for response
        deadline = datetime.now(UTC) + timedelta(milliseconds=timeout_ms)
        last_id = "0-0"
        while datetime.now(UTC) < deadline:
            try:
                resp = await self._client.xread({reply_stream: last_id}, block=250, count=1)
                if resp:
                    _s, messages = resp[0]
                    msg_id, fields = messages[0]
                    last_id = msg_id
                    try:
                        data = {k.decode(): json.loads(v.decode()) for k, v in fields.items()}
                    except Exception:
                        data = {k.decode(): v.decode() for k, v in fields.items()}
                    # Clean up ephemeral reply stream
                    try:
                        await self._client.xtrim(reply_stream, 0)
                    except Exception:
                        pass
                    return data
            except Exception:
                await asyncio.sleep(0.1)
        return None


class RpcServer:
    def __init__(self, client: redis.Redis, *, group: str, consumer: str) -> None:
        self._client = client
        self._group = group
        self._consumer = consumer
        self._handlers: dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]] = {}

    def register(self, method: str, handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]) -> None:
        self._handlers[method] = handler

    async def serve(self, stop_event: asyncio.Event | None = None) -> None:
        try:
            await self._client.xgroup_create(RPC_REQUESTS, self._group, id="0-0", mkstream=True)
        except Exception:
            pass
        while stop_event is None or not stop_event.is_set():
            try:
                resp = await self._client.xreadgroup(self._group, self._consumer, streams={RPC_REQUESTS: ">"}, count=10, block=1000)
                if not resp:
                    continue
                for _s, messages in resp:
                    for msg_id, fields in messages:
                        try:
                            payload = {k.decode(): json.loads(v.decode()) for k, v in fields.items()}
                            method = str(payload.get("method", ""))
                            reply_to = str(payload.get("reply_to", RPC_REPLIES))
                            cid = str(payload.get("correlation_id", ""))
                            handler = self._handlers.get(method)
                            result: dict[str, Any]
                            if handler is None:
                                result = {"error": f"unknown_method:{method}"}
                            else:
                                result = await handler(payload)
                            out = {"correlation_id": cid, "result": result}
                            await self._client.xadd(reply_to, {k: json.dumps(v) for k, v in out.items()}, maxlen=1000, approximate=True)
                        except Exception as e:  # noqa: BLE001
                            logger.exception("RPC handler error", exc_info=e)
                        finally:
                            try:
                                await self._client.xack(RPC_REQUESTS, self._group, msg_id)
                            except Exception:
                                pass
            except Exception as e:  # noqa: BLE001
                logger.warning(f"RpcServer loop error: {e}")


