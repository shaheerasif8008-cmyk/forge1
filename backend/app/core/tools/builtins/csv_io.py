from __future__ import annotations

from typing import Any
import csv
from io import StringIO

from ..base_tool import BaseTool


class CsvReader(BaseTool):
    name = "csv_reader"
    description = "Read CSV content and return rows as arrays or dicts"

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        content = kwargs.get("content")
        path = kwargs.get("path")
        as_dict = bool(kwargs.get("as_dict", True))
        delimiter = str(kwargs.get("delimiter", ","))
        data: str
        if content is not None and isinstance(content, str):
            data = content
        elif path is not None and isinstance(path, str):
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
        else:
            raise ValueError("csv_reader requires 'content' or 'path'")
        f = StringIO(data)
        if as_dict:
            reader = csv.DictReader(f, delimiter=delimiter)
            rows = [dict(r) for r in reader]
        else:
            reader = csv.reader(f, delimiter=delimiter)
            rows = [list(r) for r in reader]
        return {"rows": rows}


class CsvWriter(BaseTool):
    name = "csv_writer"
    description = "Write rows to CSV and return string (or save to path)"

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        rows = kwargs.get("rows")
        if not isinstance(rows, list):
            raise ValueError("csv_writer requires 'rows' list")
        delimiter = str(kwargs.get("delimiter", ","))
        path = kwargs.get("path")
        out = StringIO()
        if rows and isinstance(rows[0], dict):
            fieldnames = list(rows[0].keys())
            writer = csv.DictWriter(out, fieldnames=fieldnames, delimiter=delimiter)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
        else:
            writer = csv.writer(out, delimiter=delimiter)
            for r in rows:
                writer.writerow(r)
        data = out.getvalue()
        if path and isinstance(path, str):
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(data)
        return {"content": data}


TOOLS = {CsvReader.name: CsvReader(), CsvWriter.name: CsvWriter()}


