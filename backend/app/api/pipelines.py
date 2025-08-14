from __future__ import annotations

import time
import hashlib
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .auth import get_current_user
from ..db.session import get_session
from ..db.models import Pipeline, PipelineStep, PipelineRun, PipelineStepRun, Employee
from ..core.runtime.deployment_runtime import DeploymentRuntime


router = APIRouter(prefix="/pipelines", tags=["pipelines"])


class PipelineStepIn(BaseModel):
    employee_id: str
    order: int = Field(ge=0)
    input_map: dict[str, Any] = Field(default_factory=dict)
    output_key: str = Field(min_length=1)
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None


class PipelineIn(BaseModel):
    name: str
    description: str | None = None
    steps: list[PipelineStepIn]


class PipelineOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    steps: list[PipelineStepIn]


@router.post("/", response_model=PipelineOut, status_code=status.HTTP_201_CREATED)
def create_pipeline(payload: PipelineIn, db: Session = Depends(get_session), user=Depends(get_current_user)) -> PipelineOut:  # noqa: B008
    if not payload.steps:
        raise HTTPException(status_code=400, detail="Pipeline requires at least one step")
    # Validate employees exist in tenant
    for s in payload.steps:
        e = db.get(Employee, s.employee_id)
        if e is None or e.tenant_id != user["tenant_id"]:
            raise HTTPException(status_code=404, detail=f"Employee not found: {s.employee_id}")
    pid = hashlib.sha1(f"{user['tenant_id']}::{payload.name}".encode()).hexdigest()[:16]
    if db.get(Pipeline, pid) is not None:
        raise HTTPException(status_code=409, detail="Pipeline exists")
    row = Pipeline(id=pid, tenant_id=user["tenant_id"], name=payload.name, description=payload.description or "")
    db.add(row)
    for s in sorted(payload.steps, key=lambda x: x.order):
        sid = hashlib.sha1(f"{pid}::{s.order}::{s.employee_id}".encode()).hexdigest()[:16]
        db.add(PipelineStep(id=sid, pipeline_id=pid, order=int(s.order), employee_id=s.employee_id, input_map=s.input_map or {}, output_key=s.output_key, input_schema=s.input_schema, output_schema=s.output_schema))
    db.commit()
    return PipelineOut(id=row.id, name=row.name, description=row.description, steps=payload.steps)


@router.get("/", response_model=list[PipelineOut])
def list_pipelines(db: Session = Depends(get_session), user=Depends(get_current_user)) -> list[PipelineOut]:  # noqa: B008
    rows = db.query(Pipeline).filter(Pipeline.tenant_id == user["tenant_id"]).all()
    out: list[PipelineOut] = []
    for p in rows:
        steps = db.query(PipelineStep).filter(PipelineStep.pipeline_id == p.id).order_by(PipelineStep.order.asc()).all()
        out.append(PipelineOut(id=p.id, name=p.name, description=p.description, steps=[PipelineStepIn(employee_id=s.employee_id, order=s.order, input_map=s.input_map or {}, output_key=s.output_key, input_schema=s.input_schema, output_schema=s.output_schema) for s in steps]))
    return out


class PipelineRunOut(BaseModel):
    run_id: int
    status: str
    output: dict[str, Any] | None


@router.post("/{pipeline_id}/run", response_model=PipelineRunOut)
async def run_pipeline(pipeline_id: str, payload: dict[str, Any], db: Session = Depends(get_session), user=Depends(get_current_user)) -> PipelineRunOut:  # noqa: B008
    p = db.get(Pipeline, pipeline_id)
    if p is None or p.tenant_id != user["tenant_id"]:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    steps = db.query(PipelineStep).filter(PipelineStep.pipeline_id == p.id).order_by(PipelineStep.order.asc()).all()
    if not steps:
        raise HTTPException(status_code=400, detail="Pipeline has no steps")
    run = PipelineRun(pipeline_id=p.id, tenant_id=user["tenant_id"], status="running", input=payload or {})
    db.add(run)
    db.commit()
    db.refresh(run)
    context: dict[str, Any] = dict(payload or {})
    try:
        for s in steps:
            sr = PipelineStepRun(pipeline_run_id=run.id, step_id=s.id, order=s.order, employee_id=s.employee_id, status="running", input={k: context.get(v) for k, v in (s.input_map or {}).items()})
            db.add(sr)
            db.commit()
            # Execute step via employee runtime
            emp = db.get(Employee, s.employee_id)
            runtime = DeploymentRuntime(employee_config=emp.config)
            # Seed prompt from input map
            task_text = str(sr.input.get("task") or context.get("task") or "")
            start = time.time()
            try:
                results = await runtime.start(task_text, iterations=1, context={"tenant_id": user["tenant_id"], "employee_id": emp.id, **sr.input})
                out = results[-1].model_dump() if results else {}
                sr.output = out
                sr.status = "succeeded" if (results and results[-1].success) else "failed"
                sr.finished_at = time.time()
                db.commit()
                if sr.status != "succeeded":
                    raise RuntimeError(out.get("error") or "step failed")
                # Stash output under step.output_key
                context[s.output_key] = out.get("output") or out
            except Exception as e:  # noqa: BLE001
                sr.status = "failed"
                sr.error = str(e)
                db.commit()
                raise
        run.status = "succeeded"
        run.output = {k: v for k, v in context.items() if k not in (payload or {})}
        run.finished_at = time.time()
        db.commit()
        return PipelineRunOut(run_id=run.id, status=run.status, output=run.output)
    except Exception as e:  # noqa: BLE001
        run.status = "failed"
        run.error = str(e)
        run.finished_at = time.time()
        db.commit()
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e}")


