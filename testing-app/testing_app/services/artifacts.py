from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from testing_app.core.config import BASE_ARTIFACTS_DIR, settings


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_json_artifact(run_id: int, name: str, data: dict[str, Any]) -> str:
    # Local disk fallback; if TESTING_ARTIFACTS_URL provided, treat as base path or URL prefix
    safe_name = name.replace("/", "_")
    run_dir = BASE_ARTIFACTS_DIR / f"run_{run_id}"
    _ensure_dir(run_dir)
    file_path = run_dir / f"{safe_name}.json"
    file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    base_url = settings.artifacts_url
    if base_url and (base_url.startswith("http://") or base_url.startswith("https://")):
        # Caller must ensure the artifacts dir is exposed; return URL join
        return f"{base_url.rstrip('/')}/run_{run_id}/{safe_name}.json"
    return str(file_path)


def save_text_artifact(run_id: int, name: str, content: str) -> str:
    safe_name = name.replace("/", "_")
    run_dir = BASE_ARTIFACTS_DIR / f"run_{run_id}"
    _ensure_dir(run_dir)
    file_path = run_dir / f"{safe_name}.log"
    file_path.write_text(content, encoding="utf-8")
    base_url = settings.artifacts_url
    if base_url and (base_url.startswith("http://") or base_url.startswith("https://")):
        return f"{base_url.rstrip('/')}/run_{run_id}/{safe_name}.log"
    return str(file_path)


def save_text_artifact_ext(run_id: int, name: str, content: str, ext: str) -> str:
    safe_name = name.replace("/", "_")
    ext_clean = (ext or "").lstrip(".") or "txt"
    run_dir = BASE_ARTIFACTS_DIR / f"run_{run_id}"
    _ensure_dir(run_dir)
    file_path = run_dir / f"{safe_name}.{ext_clean}"
    file_path.write_text(content, encoding="utf-8")
    base_url = settings.artifacts_url
    if base_url and (base_url.startswith("http://") or base_url.startswith("https://")):
        return f"{base_url.rstrip('/')}/run_{run_id}/{safe_name}.{ext_clean}"
    return str(file_path)


