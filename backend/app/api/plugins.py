from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.session import get_session
from ..db.models import Plugin, PluginVersion, PluginInstall
from .auth import get_current_user
from ..exec.sandbox_manager import run_tool_sandboxed, SandboxTimeout


router = APIRouter(prefix="/plugins", tags=["plugins"])


class ManifestIn(BaseModel):
    key: str
    name: str
    description: str | None = None
    author: str | None = None
    homepage: str | None = None
    version: str
    entry_module: str
    entry_handler: str
    permissions: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


@router.post("/submit", status_code=status.HTTP_201_CREATED)
def submit_plugin(manifest: ManifestIn, current_user=Depends(get_current_user), db: Session = Depends(get_session)) -> dict[str, Any]:  # noqa: B008
    # Upsert plugin
    plug = db.query(Plugin).filter(Plugin.key == manifest.key).first()
    if not plug:
        plug = Plugin(key=manifest.key, name=manifest.name, description=manifest.description, author=manifest.author, homepage=manifest.homepage, latest_version=manifest.version, status="pending")
        db.add(plug)
        db.commit()
        db.refresh(plug)
    else:
        plug.name = manifest.name
        plug.description = manifest.description
        plug.author = manifest.author
        plug.homepage = manifest.homepage
        plug.latest_version = manifest.version
        plug.status = plug.status or "pending"
        db.add(plug)
        db.commit()
    # Insert version
    ver = PluginVersion(plugin_id=plug.id, version=manifest.version, manifest=manifest.model_dump(), entry_module=manifest.entry_module, entry_handler=manifest.entry_handler, permissions=manifest.permissions or {})
    db.add(ver)
    db.commit()
    return {"plugin_id": plug.id, "version_id": ver.id, "status": plug.status}


@router.post("/{plugin_key}/approve")
def approve_plugin(plugin_key: str, current_user=Depends(get_current_user), db: Session = Depends(get_session)) -> dict[str, Any]:  # noqa: B008
    # TODO: Restrict to admins in production
    plug = db.query(Plugin).filter(Plugin.key == plugin_key).first()
    if not plug:
        raise HTTPException(status_code=404, detail="plugin not found")
    plug.status = "approved"
    db.add(plug)
    db.commit()
    return {"status": "approved"}


@router.get("/marketplace")
def list_marketplace(current_user=Depends(get_current_user), db: Session = Depends(get_session)) -> list[dict[str, Any]]:  # noqa: B008
    rows = db.query(Plugin).filter(Plugin.status == "approved").order_by(Plugin.name.asc()).all()
    return [{"key": r.key, "name": r.name, "description": r.description, "latest_version": r.latest_version} for r in rows]


@router.post("/install/{plugin_key}")
def install_plugin(plugin_key: str, current_user=Depends(get_current_user), db: Session = Depends(get_session)) -> dict[str, Any]:  # noqa: B008
    tenant_id = current_user["tenant_id"]
    plug = db.query(Plugin).filter(Plugin.key == plugin_key, Plugin.status == "approved").first()
    if not plug:
        raise HTTPException(status_code=404, detail="plugin not available")
    # Pick version (latest or pinned by request later)
    ver = db.query(PluginVersion).filter(PluginVersion.plugin_id == plug.id).order_by(PluginVersion.id.desc()).first()
    if not ver:
        raise HTTPException(status_code=400, detail="no versions")
    inst = db.query(PluginInstall).filter(PluginInstall.tenant_id == tenant_id, PluginInstall.plugin_id == plug.id).first()
    if not inst:
        inst = PluginInstall(tenant_id=tenant_id, plugin_id=plug.id, version_id=ver.id, auto_update=False, pinned_version=None)
    else:
        inst.version_id = ver.id
    db.add(inst)
    db.commit()
    return {"installed": True, "plugin": plug.key, "version": ver.version}


@router.post("/uninstall/{plugin_key}")
def uninstall_plugin(plugin_key: str, current_user=Depends(get_current_user), db: Session = Depends(get_session)) -> dict[str, Any]:  # noqa: B008
    tenant_id = current_user["tenant_id"]
    plug = db.query(Plugin).filter(Plugin.key == plugin_key).first()
    if not plug:
        raise HTTPException(status_code=404, detail="plugin not found")
    db.query(PluginInstall).filter(PluginInstall.tenant_id == tenant_id, PluginInstall.plugin_id == plug.id).delete()
    db.commit()
    return {"uninstalled": True}


class RunPluginIn(BaseModel):
    plugin_key: str
    version: str | None = None
    payload: dict[str, Any]


@router.post("/run")
def run_plugin(payload: RunPluginIn, current_user=Depends(get_current_user), db: Session = Depends(get_session)) -> dict[str, Any]:  # noqa: B008
    tenant_id = current_user["tenant_id"]
    plug = db.query(Plugin).filter(Plugin.key == payload.plugin_key, Plugin.status == "approved").first()
    if not plug:
        raise HTTPException(status_code=404, detail="plugin not available")
    # Resolve version by pin or latest installed
    ver: PluginVersion | None = None
    if payload.version:
        ver = db.query(PluginVersion).filter(PluginVersion.plugin_id == plug.id, PluginVersion.version == payload.version).first()
    if ver is None:
        inst = db.query(PluginInstall).filter(PluginInstall.tenant_id == tenant_id, PluginInstall.plugin_id == plug.id).first()
        if not inst:
            raise HTTPException(status_code=400, detail="plugin not installed")
        ver = db.query(PluginVersion).get(inst.version_id)
    if ver is None:
        raise HTTPException(status_code=404, detail="version not found")
    try:
        result = run_tool_sandboxed(ver.entry_module, ver.entry_handler, payload.payload, timeout_secs=5)
    except SandboxTimeout:
        raise HTTPException(status_code=504, detail="plugin timeout")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"plugin error: {e}")
    return {"ok": True, "result": result}


