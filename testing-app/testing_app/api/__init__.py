from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .runs import router as runs_router
from .scenarios import router as scenarios_router
from .suites import router as suites_router
from testing_app.db.session import get_db
from testing_app.models.entities import TestSuite, TestScenario
from testing_app.api.deps import require_service_key


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(scenarios_router)
api_router.include_router(suites_router)
api_router.include_router(runs_router)


@api_router.post("/seed")
def seed_baseline(db: Session = Depends(get_db), _auth=Depends(require_service_key)) -> dict[str, int]:  # noqa: B008,ARG002
	# Aligned scenarios for staging
	sc_live = TestScenario(
		kind="integration",
		name="health_live",
		description="Health live",
		inputs={"method": "GET", "path": "/api/v1/health/live"},
		asserts={"status": 200, "json_contains": {"status": "live"}},
		tags=["smoke"],  # type: ignore[list-item]
	)
	sc_ready = TestScenario(
		kind="integration",
		name="health_ready",
		description="Health ready",
		inputs={"method": "GET", "path": "/api/v1/health/ready"},
		asserts={"status": 200, "json_has_keys": ["status", "trace_id"], "json_contains": {"status": "ready"}},
		tags=["smoke"],  # type: ignore[list-item]
	)
	sc_emp_soft = TestScenario(
		kind="integration",
		name="employee_create_soft",
		description="Create minimal employee (soft).",
		inputs={
			"method": "POST",
			"path": "/api/v1/employees",
			"payload": {"name": "fc_test_employee", "role_name": "research_assistant", "description": "test", "tools": []},
			"headers": {"Content-Type": "application/json"},
		},
		asserts={"status": [201, 200, "SKIP_IF_404"]},
		tags=["employees", "soft"],  # type: ignore[list-item]
	)
	db.add_all([sc_live, sc_ready, sc_emp_soft])
	db.commit()
	db.refresh(sc_live); db.refresh(sc_ready); db.refresh(sc_emp_soft)

	# Functional-Core
	s1 = TestSuite(
		name="Functional-Core",
		target_env="staging",
		scenario_ids=[sc_live.id, sc_ready.id, sc_emp_soft.id],
		load_profile=None,
		chaos_profile=None,
		security_profile=None,
	)
	# Keep other suites as-is
	db.add_all([s1])
	db.commit()
	db.refresh(s1)
	return {"suite_id": s1.id}


