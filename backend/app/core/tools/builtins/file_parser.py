from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from ..base_tool import BaseTool


class FileParser(BaseTool):
    """Parse files (CSV/TXT/PDF) into structured outputs.

    CSV returns rows, TXT returns text, PDF returns extracted text via pypdf.
    """

    name = "file_parser"
    description = (
        "Parse CSV, TXT, basic PDF into text/rows. For PDFs, returns raw text if available."
    )

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        path = str(kwargs.get("path", ""))
        limit_rows = kwargs.get("limit_rows")
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(path)
        suffix = p.suffix.lower()
        if suffix == ".csv":
            rows: list[dict[str, Any]] = []
            with p.open(newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    rows.append(dict(row))
                    if limit_rows is not None and i + 1 >= limit_rows:
                        break
            return {"type": "csv", "rows": rows}
        if suffix in {".txt", ".md", ".log"}:
            text = p.read_text(encoding="utf-8", errors="ignore")
            return {"type": "text", "text": text}
        if suffix == ".pdf":
            # Minimal: try to use pypdf if possible else return bytes length
            try:
                import pypdf

                reader = pypdf.PdfReader(str(p))
                parts: list[str] = []
                for page in reader.pages:  # type: ignore[attr-defined]
                    parts.append(page.extract_text() or "")
                return {"type": "pdf", "text": "\n".join(parts)}
            except Exception as e:  # noqa: BLE001
                raise RuntimeError(
                    "pypdf is required for PDF parsing. Install with `pip install pypdf`."
                ) from e
        # Fallback: just return raw bytes length
        data = p.read_bytes()
        return {"type": "binary", "bytes": len(data)}


TOOLS = {FileParser.name: FileParser()}
