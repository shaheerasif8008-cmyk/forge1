from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .auth import get_current_user
from ..db.session import get_session
from ..db.models import ToolManifest, TenantToolConfig


router = APIRouter(prefix="/admin/tools", tags=["admin-tools"])


def _require_admin(user=Depends(get_current_user)):
    roles = set(user.get("roles", []) if isinstance(user.get("roles", []), list) else [])
    if "admin" not in roles:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user


class ToolOut(BaseModel):
    name: str
    version: str
    scopes: list[str] | None
    config_schema: dict[str, Any] | None
    docs_url: str | None


@router.get("/registry", response_model=list[ToolOut])
def list_registry(db: Session = Depends(get_session), user=Depends(_require_admin)) -> list[ToolOut]:  # noqa: B008
    try:
        ToolManifest.__table__.create(bind=db.get_bind(), checkfirst=True)
    except Exception:
        pass
    rows = db.query(ToolManifest).all()
    if not rows:
        # Seed minimal manifests for DX if empty
        try:
            seeds = [
                ToolManifest(
                    name="csv_reader",
                    version="1.0",
                    scopes=["files:read"],
                    config_schema={"type": "object", "properties": {"delimiter": {"type": "string", "default": ","}}, "required": []},
                    docs_url="https://docs.local/tools/csv",
                ),
                ToolManifest(
                    name="csv_writer",
                    version="1.0",
                    scopes=["files:write"],
                    config_schema={"type": "object", "properties": {"delimiter": {"type": "string", "default": ","}}, "required": []},
                    docs_url="https://docs.local/tools/csv",
                ),
                ToolManifest(
                    name="slack_notifier",
                    version="1.0",
                    scopes=["slack:send"],
                    config_schema={"type": "object", "properties": {"webhook_url": {"type": "string"}}, "required": ["webhook_url"]},
                    docs_url="https://api.slack.com/messaging/webhooks",
                ),
            ]
            for m in seeds:
                db.add(m)
            db.commit()
            rows = db.query(ToolManifest).all()
        except Exception:
            db.rollback()
    return [ToolOut(name=r.name, version=r.version, scopes=r.scopes, config_schema=r.config_schema, docs_url=r.docs_url) for r in rows]


class TenantToolOut(BaseModel):
    tool_name: str
    enabled: bool
    config: dict[str, Any] | None


@router.get("/tenant", response_model=list[TenantToolOut])
def list_tenant_tools(db: Session = Depends(get_session), user=Depends(_require_admin)) -> list[TenantToolOut]:  # noqa: B008
    rows = db.query(TenantToolConfig).filter(TenantToolConfig.tenant_id == user["tenant_id"]).all()
    return [TenantToolOut(tool_name=r.tool_name, enabled=r.enabled, config=r.config) for r in rows]


class EnableIn(BaseModel):
    enabled: bool = Field(default=True)
    config: dict[str, Any] | None = None


def _validate_config(schema: dict[str, Any] | None, config: dict[str, Any] | None) -> None:
    if not schema:
        return
    cfg = config or {}
    props = (schema or {}).get("properties", {})
    required = (schema or {}).get("required", [])
    # required keys
    for key in required:
        if key not in cfg or cfg.get(key) in (None, ""):
            raise HTTPException(status_code=400, detail=f"Missing required config field: {key}")
    # type checks (basic)
    for k, spec in props.items():
        if k in cfg and cfg[k] is not None:
            t = spec.get("type")
            if t == "string" and not isinstance(cfg[k], str):
                raise HTTPException(status_code=400, detail=f"Field {k} must be a string")
            if t == "boolean" and not isinstance(cfg[k], bool):
                raise HTTPException(status_code=400, detail=f"Field {k} must be a boolean")
            if t == "number" and not isinstance(cfg[k], (int, float)):
                raise HTTPException(status_code=400, detail=f"Field {k} must be a number")


@router.post("/{tool_name}/enable", response_model=TenantToolOut)
def enable_tool(tool_name: str, payload: EnableIn, db: Session = Depends(get_session), user=Depends(_require_admin)) -> TenantToolOut:  # noqa: B008
    manifest = db.query(ToolManifest).filter(ToolManifest.name == tool_name).first()
    if manifest is None:
        raise HTTPException(status_code=404, detail="Tool not found")
    _validate_config(manifest.config_schema, payload.config)
    # Ensure tenant_tools table exists in dev/tests
    try:
        TenantToolConfig.__table__.create(bind=db.get_bind(), checkfirst=True)
    except Exception:
        pass
    row = db.query(TenantToolConfig).filter(TenantToolConfig.tenant_id == user["tenant_id"], TenantToolConfig.tool_name == tool_name).first()
    if row is None:
        row = TenantToolConfig(tenant_id=user["tenant_id"], tool_name=tool_name, enabled=payload.enabled, config=payload.config or {})
        db.add(row)
    else:
        row.enabled = payload.enabled
        row.config = payload.config or {}
    db.commit()
    return TenantToolOut(tool_name=row.tool_name, enabled=row.enabled, config=row.config)


