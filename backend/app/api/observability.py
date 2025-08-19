from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
import asyncio as _asyncio
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.session import get_session
from ..db.models import TraceSpan, RunFailure, TaskExecution, BenchmarkResult, ConsensusLog
from ..core.telemetry.metrics_service import DailyUsageMetric
from ..api.auth import get_current_user


router = APIRouter(prefix="/observability", tags=["observability"])


class SpanOut(BaseModel):
	trace_id: str
	span_id: str
	parent_span_id: str | None
	span_type: str
	name: str
	status: str
	started_at: str | None
	finished_at: str | None
	duration_ms: int | None
	input: dict[str, Any] | None = None
	output: dict[str, Any] | None = None
	metadata: dict[str, Any] | None = None


@router.get("/traces/{trace_id}", response_model=list[SpanOut])
def get_trace(trace_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_session)) -> list[SpanOut]:  # noqa: B008
	# Table managed by Alembic
	pass
	rows = (
		db.query(TraceSpan)
		.filter(TraceSpan.trace_id == trace_id)
		.order_by(TraceSpan.started_at.asc())
		.all()
	)
	out: list[SpanOut] = []
	for r in rows:
		out.append(
			SpanOut(
				trace_id=r.trace_id,
				span_id=r.span_id,
				parent_span_id=r.parent_span_id,
				span_type=r.span_type,
				name=r.name,
				status=r.status,
				started_at=r.started_at.isoformat() if r.started_at else None,
				finished_at=r.finished_at.isoformat() if r.finished_at else None,
				duration_ms=r.duration_ms,
				input=r.input,
				output=r.output,
				metadata=r.metadata,
			)
		)
	return out


@router.get("/traces", response_model=list[SpanOut])
def list_recent_traces(
	current_user=Depends(get_current_user),
	db: Session = Depends(get_session),  # noqa: B008
	limit: int = Query(default=50, ge=1, le=200),
) -> list[SpanOut]:
	# Table managed by Alembic
	pass
	rows = (
		db.query(TraceSpan)
		.filter(TraceSpan.tenant_id == current_user.get("tenant_id"))
		.order_by(TraceSpan.id.desc())
		.limit(limit)
		.all()
	)
	return [
		SpanOut(
			trace_id=r.trace_id,
			span_id=r.span_id,
			parent_span_id=r.parent_span_id,
			span_type=r.span_type,
			name=r.name,
			status=r.status,
			started_at=r.started_at.isoformat() if r.started_at else None,
			finished_at=r.finished_at.isoformat() if r.finished_at else None,
			duration_ms=r.duration_ms,
			input=r.input,
			output=r.output,
			metadata=r.metadata,
		)
		for r in rows
	]


@router.get("/benchmarks")
def list_benchmarks(industry: str | None = None, limit: int = 100, current_user=Depends(get_current_user), db: Session = Depends(get_session)) -> list[dict[str, Any]]:  # noqa: B008
    q = db.query(BenchmarkResult)
    if industry:
        q = q.filter(BenchmarkResult.industry == industry)
    rows = q.order_by(BenchmarkResult.id.desc()).limit(max(1, min(500, int(limit)))).all()
    return [{"industry": r.industry, "task_type": r.task_type, "model_name": r.model_name, "baseline": r.baseline_model, "score": r.score, "latency_ms": r.latency_ms, "ts": (r.created_at.isoformat() if r.created_at else None)} for r in rows]


@router.get("/consensus_logs")
def list_consensus_logs(limit: int = 100, current_user=Depends(get_current_user), db: Session = Depends(get_session)) -> list[dict[str, Any]]:  # noqa: B008
    rows = (
        db.query(ConsensusLog)
        .filter(ConsensusLog.tenant_id == current_user.get("tenant_id"))
        .order_by(ConsensusLog.id.desc())
        .limit(max(1, min(500, int(limit))))
        .all()
    )
    return [{"task_type": r.task_type, "agreed": r.agreed, "selected_model": r.selected_model, "consensus_k": r.consensus_k, "models": r.models, "ts": (r.created_at.isoformat() if r.created_at else None)} for r in rows]


@router.get("/spend/monthly")
def spend_monthly(current_user=Depends(get_current_user), db: Session = Depends(get_session)) -> dict[str, Any]:  # noqa: B008
    # Aggregate from daily usage and approximate cost using provider map where possible
    rows = (
        db.query(DailyUsageMetric)
        .filter(DailyUsageMetric.tenant_id == current_user["tenant_id"])
        .all()
    )
    total_tokens = sum(int(r.total_tokens or 0) for r in rows)
    # Use OpenAI default as approximation; frontend can break down further if needed
    from ..core.llm.model_router import _cost_cents_for_tokens
    approx_cents = _cost_cents_for_tokens("openai", int(total_tokens))
    return {"total_tokens": total_tokens, "approx_cost_cents": approx_cents}


class ReplayRequest(BaseModel):
	trace_id: str
	span_id: str | None = None


@router.post("/replay")
def time_travel_replay(payload: ReplayRequest, current_user=Depends(get_current_user), db: Session = Depends(get_session)) -> dict[str, Any]:  # noqa: B008
	# Store a RunFailure queued entry to be consumed by a worker that replays deterministically
	root = (
		db.query(TraceSpan)
		.filter(TraceSpan.trace_id == payload.trace_id)
		.order_by(TraceSpan.id.asc())
		.first()
	)
	if root is None:
		raise HTTPException(status_code=404, detail="trace not found")
	# best-effort snapshot
	db.add(
		RunFailure(
			tenant_id=root.tenant_id,
			employee_id=root.employee_id,
			reason="replay",
			payload={"trace_id": payload.trace_id, "span_id": payload.span_id},
			status="queued",
		)
	)
	db.commit()
	return {"status": "queued"}


class RootCause(BaseModel):
	trace_id: str
	span_id: str
	reason: str
	path: list[str]


@router.get("/root_cause/{trace_id}", response_model=RootCause)
def root_cause(trace_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_session)) -> RootCause:  # noqa: B008
	# Table managed by Alembic
	pass
	spans = db.query(TraceSpan).filter(TraceSpan.trace_id == trace_id).all()
	# naive: find first error span, walk parents up to root
	by_id = {s.span_id: s for s in spans}
	bad = next((s for s in spans if (s.status or "").lower() == "error"), None)
	if bad is None:
		return RootCause(trace_id=trace_id, span_id="", reason="no_error", path=[])
	path: list[str] = []
	curr = bad
	while curr is not None:
		path.append(curr.name)
		curr = by_id.get(curr.parent_span_id or "")
	path.reverse()
	return RootCause(trace_id=trace_id, span_id=bad.span_id, reason=str(bad.error or "error"), path=path)


@router.get("/stream")
async def stream_tracing(current_user=Depends(get_current_user)) -> StreamingResponse:  # noqa: B008
    async def gen():
        from ..interconnect import get_interconnect
        ic = await get_interconnect()
        cli = await ic.client()
        last_id = b"$"
        stream = "events.tracing"
        while True:
            try:
                resp = await cli.xread({stream: last_id}, block=500, count=10)
                for (_sname, items) in resp or []:
                    for (_id, fields) in items:
                        last_id = _id
                        payload = fields.get(b"data") or b"{}"
                        yield b"data: " + payload + b"\n\n"
            except Exception:
                await _asyncio.sleep(0.5)
    return StreamingResponse(gen(), media_type="text/event-stream")

