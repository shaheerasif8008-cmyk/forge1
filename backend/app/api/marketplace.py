from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..db.session import get_session
from ..db.models import MarketplaceTemplate, Employee, Tenant
from ..core.employee_builder.employee_builder import EmployeeBuilder


router = APIRouter(prefix="/marketplace", tags=["marketplace"])


class TemplateOut(BaseModel):
    key: str
    name: str
    vertical: str | None
    description: str
    required_tools: list[str]
    version: str


@router.get("/templates", response_model=list[TemplateOut])
def list_templates(
    vertical: str | None = Query(default=None),
    search: str | None = Query(default=None),
    db: Session = Depends(get_session),  # noqa: B008
    user=Depends(get_current_user),  # noqa: B008
) -> list[TemplateOut]:
    # Ensure table exists in minimal test envs
    try:
        MarketplaceTemplate.__table__.create(bind=db.get_bind(), checkfirst=True)
    except Exception:
        pass
    q = db.query(MarketplaceTemplate).filter(MarketplaceTemplate.enabled.is_(True))
    if vertical:
        q = q.filter(MarketplaceTemplate.vertical == vertical)
    rows = q.all()
    if not rows:
        # Seed minimal templates if empty (dev/tests convenience)
        try:
            seeds = [
                ("lead_qualifier", "Lead Qualifier", "sales", "Qualify inbound leads", ["api_caller", "csv_reader"], {}),
                ("research_analyst", "Research Analyst", "research", "Research topics and summarize", ["web_scraper", "csv_writer"], {}),
            ]
            for key0, name0, vert0, desc0, tools0, default0 in seeds:
                if db.query(MarketplaceTemplate).filter(MarketplaceTemplate.key == key0).first() is None:
                    db.add(
                        MarketplaceTemplate(
                            key=key0,
                            name=name0,
                            vertical=vert0,
                            description=desc0,
                            required_tools=tools0,
                            default_config=default0,
                            version="1.0",
                            enabled=True,
                        )
                    )
            db.commit()
            rows = db.query(MarketplaceTemplate).filter(MarketplaceTemplate.enabled.is_(True)).all()
        except Exception:
            db.rollback()
    out: list[TemplateOut] = []
    for r in rows:
        if search:
            s = search.lower()
            if s not in (r.name or "").lower() and s not in (r.description or "").lower():
                continue
        out.append(
            TemplateOut(
                key=r.key,
                name=r.name,
                vertical=r.vertical,
                description=r.description,
                required_tools=list(r.required_tools or []),
                version=r.version,
            )
        )
    return out


class DeployOut(BaseModel):
    employee_id: str
    name: str


@router.post("/templates/{key}/deploy", response_model=DeployOut, status_code=status.HTTP_201_CREATED)
def deploy_template(
    key: str,
    db: Session = Depends(get_session),  # noqa: B008
    user=Depends(get_current_user),  # noqa: B008
) -> DeployOut:
    tmpl = db.query(MarketplaceTemplate).filter(MarketplaceTemplate.key == key, MarketplaceTemplate.enabled.is_(True)).first()
    if tmpl is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    # Ensure tenant exists
    tenant_id = str(user.get("tenant_id"))
    if db.get(Tenant, tenant_id) is None:
        db.add(Tenant(id=tenant_id, name="Tenant"))
        db.commit()

    # Suggest a name and make unique
    base_name = tmpl.name
    name = base_name
    suffix = 1
    import hashlib
    eid = hashlib.sha1(f"{tenant_id}::{name}".encode()).hexdigest()[:16]
    while db.get(Employee, eid) is not None:
        suffix += 1
        name = f"{base_name} {suffix}"
        eid = hashlib.sha1(f"{tenant_id}::{name}".encode()).hexdigest()[:16]

    # Build config from template
    required_tools: list[str] = list(tmpl.required_tools or [])
    tools = [{"name": t, "config": {}} for t in required_tools]
    builder = EmployeeBuilder(role_name=name, description=tmpl.description, tools=tools, template_name="base")
    config = builder.build_config()

    row = Employee(id=eid, tenant_id=tenant_id, owner_user_id=None, name=name, config=config)
    try:
        db.add(row)
        db.commit()
    except Exception as e:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=500, detail="Deploy failed") from e
    return DeployOut(employee_id=row.id, name=row.name)


