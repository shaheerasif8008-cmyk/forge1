from __future__ import annotations

"""High-level SDK for publishing and subscribing to internal events and RPC.

Provides a simple facade used by the rest of the backend to avoid leaking
Redis or Streams primitives.
"""

import asyncio
import logging
from typing import Any, Awaitable, Callable

import redis.asyncio as redis

from .cloudevents import CloudEvent, make_event
from .redis_streams import (
    EVENT_STREAMS,
    RpcClient,
    RpcServer,
    consume_stream,
    publish_event,
    RetryPolicy,
)

logger = logging.getLogger(__name__)


class Interconnect:
    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._client: redis.Redis | None = None
        self._rpc_server: RpcServer | None = None
        self._serve_task: asyncio.Task | None = None

    async def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(self._redis_url, decode_responses=False)  # type: ignore[no-untyped-call]
            try:
                await self._client.ping()
            except Exception as e:  # noqa: BLE001
                logger.error(f"Interconnect Redis ping failed: {e}")
                raise
        return self._client

    # ----- Events API -----
    async def publish(
        self,
        *,
        stream: str,
        type: str,
        source: str,
        subject: str | None = None,
        data: dict[str, Any] | None = None,
        tenant_id: str | None = None,
        employee_id: str | None = None,
        trace_id: str | None = None,
        actor: str | None = None,
        ttl: int | None = None,
        version: str = "1.0",
    ) -> str:
        ev = make_event(
            source=source,
            type=type,
            subject=subject,
            data=data,
            tenant_id=tenant_id,
            employee_id=employee_id,
            trace_id=trace_id,
            actor=actor,
            ttl=ttl,
            version=version,
        )
        cli = await self.client()
        return await publish_event(cli, stream, ev)

    async def subscribe(
        self,
        *,
        stream: str,
        group: str,
        consumer: str,
        handler: Callable[[CloudEvent], Awaitable[bool]],
        stop_event: asyncio.Event | None = None,
        retry: RetryPolicy | None = None,
    ) -> None:
        cli = await self.client()
        await consume_stream(
            cli,
            stream=stream,
            group=group,
            consumer=consumer,
            handler=handler,
            retry=retry,
            stop_event=stop_event,
        )

    # ----- RPC API -----
    async def rpc_call(
        self,
        *,
        method: str,
        params: dict[str, Any],
        timeout_ms: int = 5000,
        correlation_id: str | None = None,
        reply_to: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        cli = await self.client()
        return await RpcClient(cli).call(
            method=method,
            params=params,
            timeout_ms=timeout_ms,
            correlation_id=correlation_id,
            reply_to=reply_to,
            metadata=metadata,
        )

    async def rpc_register_and_serve(
        self,
        *,
        group: str,
        consumer: str,
        registrations: dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]],
        stop_event: asyncio.Event | None = None,
    ) -> None:
        cli = await self.client()
        self._rpc_server = RpcServer(cli, group=group, consumer=consumer)
        for name, func in registrations.items():
            self._rpc_server.register(name, func)
        await self._rpc_server.serve(stop_event=stop_event)


