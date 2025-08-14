from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from testing_app.core.config import settings
from testing_app.api.deps import require_service_key
from testing_app.db.session import get_db
from testing_app.models.entities import Finding, RunStatus, TestRun, TestSuite, TestScenario
from testing_app.services.artifacts import save_json_artifact
from testing_app.services.reports import try_write_pdf_report, write_html_report
from testing_app.worker.tasks import run_suite_task


router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("")
def create_run(payload: dict[str, Any], db: Session = Depends(get_db), _auth=Depends(require_service_key)) -> dict[str, Any]:  # noqa: B008,ARG002
    suite_id = int(payload.get("suite_id"))
    suite = db.get(TestSuite, suite_id)
    if suite is None:
        raise HTTPException(status_code=404, detail="suite not found")

    target_api_url = payload.get("target_api_url") or settings.target_api_url_default
    run = TestRun(
        suite_id=suite_id,
        status=RunStatus.running,
        target_api_url=target_api_url,
        stats={},
        artifacts=[],
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    scenarios: list[dict[str, Any]] = []
    if suite.scenario_ids:
        ids = [int(x) for x in suite.scenario_ids if isinstance(x, int) or (isinstance(x, str) and str(x).isdigit())]
        rows = db.query(TestScenario).filter(TestScenario.id.in_(ids)).all()
        for sc in rows:
            # Map stored TestScenario to runner step shape
            method = (sc.inputs or {}).get("method") if sc.inputs else None
            path = (sc.inputs or {}).get("path") if sc.inputs else None
            payload = (sc.inputs or {}).get("payload") if sc.inputs else None
            headers = (sc.inputs or {}).get("headers") if sc.inputs else None
            scenarios.append({
                "name": sc.name,
                "method": (str(method) if method else "GET").upper(),
                "path": str(path or "/api/v1/health"),
                "payload": payload,
                "headers": headers or {},
                "asserts": sc.asserts or {},
            })

    suite_doc = {
        "id": suite.id,
        "name": suite.name,
        "scenarios": scenarios,
        "load_profile": suite.load_profile,
        "chaos_profile": suite.chaos_profile,
        "security_profile": suite.security_profile,
    }

    if settings.run_sync:
        # Useful for tests
        result = run_suite_task(run.id, suite_doc)
        return {"run_id": run.id, "result": result}
    else:
        run_suite_task.delay(run.id, suite_doc)  # type: ignore[attr-defined]
        return {"run_id": run.id}


@router.get("")
def list_runs(limit: int = 50, db: Session = Depends(get_db), _auth=Depends(require_service_key)) -> list[dict[str, Any]]:  # noqa: B008,ARG002
    rows = db.query(TestRun).order_by(TestRun.id.desc()).limit(limit).all()
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append({
            "id": r.id,
            "suite_id": r.suite_id,
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        })
    return out


@router.get("/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db), _auth=Depends(require_service_key)) -> dict[str, Any]:  # noqa: B008,ARG002
    run = db.get(TestRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    findings = db.query(Finding).filter(Finding.run_id == run_id).all()
    run_doc = {
        "id": run.id,
        "suite_id": run.suite_id,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "status": run.status.value if hasattr(run.status, "value") else str(run.status),
        "stats": run.stats or {},
        "artifacts": run.artifacts or [],
        "target_api_url": run.target_api_url,
        "findings": [
            {
                "id": f.id,
                "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                "area": f.area,
                "message": f.message,
            }
            for f in findings
        ],
    }
    html_path = write_html_report(run_id, run_doc)
    pdf_path = try_write_pdf_report(run_id)
    # Expose artifact URLs
    signed_report_url = f"/artifacts/run_{run_id}/report.html"
    return {"run": run_doc, "report_html": html_path, "report_pdf": pdf_path, "signed_report_url": signed_report_url, "artifacts": run_doc["artifacts"]}


@router.post("/{run_id}/abort")
def abort_run(run_id: int, db: Session = Depends(get_db), _auth=Depends(require_service_key)) -> dict[str, Any]:  # noqa: B008,ARG002
    run = db.get(TestRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    if run.status == RunStatus.running:
        run.status = RunStatus.aborted
        run.finished_at = datetime.now(UTC)
        db.add(run)
        db.commit()
    return {"status": "ok", "run_id": run_id}


@router.post("/seed")
def seed_baseline(db: Session = Depends(get_db)) -> dict[str, Any]:  # noqa: B008
    # Seed a tiny suite that pings /health
    suite = TestSuite(
        name="baseline",
        target_env="staging",
        scenario_ids=[],
        load_profile={"tool": "k6", "vus": 1, "duration": "1s", "endpoints": ["/health"]},
        chaos_profile={},
        security_profile={},
    )
    db.add(suite)
    db.commit()
    db.refresh(suite)
    return {"suite_id": suite.id}


