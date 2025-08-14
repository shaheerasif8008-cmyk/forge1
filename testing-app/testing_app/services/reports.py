from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from testing_app.core.config import BASE_ARTIFACTS_DIR
from testing_app.core.signing import sign_bytes


def _html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def build_html_report(run: dict[str, Any]) -> str:
    # Deterministic HTML with embedded JSON payload
    payload = json.dumps(run, separators=(",", ":"))
    signature = sign_bytes(payload.encode("utf-8"))
    html = (
        "<!doctype html><html><head><meta charset='utf-8'><title>Testing Report</title>"
        "<style>body{font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial}h1{font-size:20px}"
        "table{border-collapse:collapse;width:100%}td,th{border:1px solid #ddd;padding:6px;font-size:12px}" 
        "code{background:#f5f5f5;padding:2px 4px;border-radius:3px}</style></head><body>"
        f"<h1>Run #{_html_escape(str(run.get('id','')))}</h1>"
        f"<p>Status: <b>{_html_escape(str(run.get('status','')))}</b></p>"
        f"<p>Suite ID: {_html_escape(str(run.get('suite_id','')))} | Target: {_html_escape(str(run.get('target_api_url','')))}</p>"
        "<h2>Stats</h2>"
        f"<pre><code>{_html_escape(json.dumps(run.get('stats', {}), indent=2))}</code></pre>"
        "<h2>Findings</h2><table><thead><tr><th>Severity</th><th>Area</th><th>Message</th></tr></thead><tbody>"
    )
    for f in run.get("findings", []) or []:
        html += (
            "<tr>"
            f"<td>{_html_escape(f.get('severity',''))}</td>"
            f"<td>{_html_escape(f.get('area',''))}</td>"
            f"<td>{_html_escape(f.get('message',''))}</td>"
            "</tr>"
        )
    html += (
        "</tbody></table>"
        f"<h2>Artifacts</h2><pre><code>{_html_escape(json.dumps(run.get('artifacts', []), indent=2))}</code></pre>"
        f"<h2>Signature</h2><p>algo=HMAC-SHA256 signature=<code>{signature}</code></p>"
        f"<details><summary>Payload</summary><pre><code>{_html_escape(payload)}</code></pre></details>"
        "</body></html>"
    )
    return html


def write_html_report(run_id: int, run: dict[str, Any]) -> str:
    content = build_html_report(run)
    out_dir = BASE_ARTIFACTS_DIR / f"run_{run_id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "report.html"
    out_path.write_text(content, encoding="utf-8")
    return str(out_path)


def try_write_pdf_report(run_id: int) -> str | None:
    html_path = BASE_ARTIFACTS_DIR / f"run_{run_id}" / "report.html"
    if not html_path.exists():
        return None
    wkhtml = shutil.which("wkhtmltopdf")
    if wkhtml is None:
        return None
    pdf_path = html_path.with_suffix(".pdf")
    try:
        subprocess.run([wkhtml, str(html_path), str(pdf_path)], check=True)
        return str(pdf_path)
    except Exception:
        return None


