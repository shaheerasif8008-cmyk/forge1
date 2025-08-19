from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

from sqlalchemy.orm import Session

from ...db.models import TraceSpan
from ...db.session import SessionLocal
from . import incr_open_spans, decr_open_spans
import asyncio as _asyncio


def new_trace_id() -> str:
	return uuid.uuid4().hex


def new_span_id() -> str:
	return uuid.uuid4().hex


@dataclass
class SpanContext:
	trace_id: str
	span_id: str
	parent_span_id: str | None
	tenant_id: str | None
	employee_id: str | None


@contextmanager
def span(
	*,
	name: str,
	span_type: str,
	trace_id: str | None = None,
	parent_span_id: str | None = None,
	tenant_id: str | None = None,
	employee_id: str | None = None,
	input: dict[str, Any] | None = None,
) -> Iterator[SpanContext]:
	"""Create and persist a tracing span.

	Writes TraceSpan rows best-effort; survives DB errors silently in prod paths.
	"""
	trace = trace_id or new_trace_id()
	span_id = new_span_id()
	started = time.time()
	ctx = SpanContext(trace_id=trace, span_id=span_id, parent_span_id=parent_span_id, tenant_id=tenant_id, employee_id=employee_id)
	# persist start
	try:
		with SessionLocal() as db:
			# Table managed by Alembic
			db.add(
				TraceSpan(
					trace_id=trace,
					span_id=span_id,
					parent_span_id=parent_span_id,
					tenant_id=tenant_id,
					employee_id=employee_id,
					span_type=span_type,
					name=name,
					status="running",
					input=input or {},
				)
			)
			db.commit()
		incr_open_spans(tenant_id or "-")
		# Emit tracing event (best-effort)
		try:
			async def _emit_start() -> None:
				from ...interconnect import get_interconnect
				ic = await get_interconnect()
				await ic.publish(
					stream="events.tracing",
					type="span.started",
					source="tracing",
					tenant_id=tenant_id,
					employee_id=employee_id,
					data={"trace_id": trace, "span_id": span_id, "parent_span_id": parent_span_id, "name": name, "span_type": span_type},
				)
			_asyncio.get_event_loop().create_task(_emit_start())
		except Exception:
			pass
	except Exception:
		pass
	try:
		yield ctx
	finally:
		dur_ms = int((time.time() - started) * 1000)
		try:
			with SessionLocal() as db:
				row = db.query(TraceSpan).filter(TraceSpan.span_id == span_id).first()
				if row is not None:
					row.duration_ms = dur_ms
					row.finished_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
					row.status = row.status or "ok"
					db.add(row)
					db.commit()
			decr_open_spans(tenant_id or "-")
			# Emit finish event
			try:
				async def _emit_finish() -> None:
					from ...interconnect import get_interconnect
					ic = await get_interconnect()
					await ic.publish(
						stream="events.tracing",
						type="span.finished",
						source="tracing",
						tenant_id=tenant_id,
						employee_id=employee_id,
						data={"trace_id": trace, "span_id": span_id, "duration_ms": dur_ms},
					)
				_asyncio.get_event_loop().create_task(_emit_finish())
			except Exception:
				pass
		except Exception:
			pass


def mark_error(ctx: SpanContext, error: str, *, output: dict[str, Any] | None = None, metadata: dict[str, Any] | None = None) -> None:
	try:
		with SessionLocal() as db:
			row = db.query(TraceSpan).filter(TraceSpan.span_id == ctx.span_id).first()
			if row is None:
				return
			row.status = "error"
			row.error = error
			if output is not None:
				row.output = output
			if metadata is not None:
				row.metadata = metadata
			db.add(row)
			db.commit()
	except Exception:
		pass


def mark_ok(ctx: SpanContext, *, output: dict[str, Any] | None = None, metadata: dict[str, Any] | None = None) -> None:
	try:
		with SessionLocal() as db:
			row = db.query(TraceSpan).filter(TraceSpan.span_id == ctx.span_id).first()
			if row is None:
				return
			row.status = "ok"
			if output is not None:
				row.output = output
			if metadata is not None:
				row.metadata = metadata
			db.add(row)
			db.commit()
	except Exception:
		pass


