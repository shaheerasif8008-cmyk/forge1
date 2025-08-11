from __future__ import annotations

from typing import Any

from ..base_tool import BaseTool


class DataAnalyzer(BaseTool):
    """Basic pandas-powered data analysis (describe/head)."""

    name = "data_analyzer"
    description = "Perform basic data analysis using pandas (describe, head)."

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        data = kwargs.get("data")
        csv_path = kwargs.get("csv_path")
        head = int(kwargs.get("head", 5))
        # Ensure pandas is available
        try:
            import pandas as pd  # type: ignore
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(
                "pandas is required for data_analyzer. Install with `pip install pandas`."
            ) from e

        if data is not None:
            df = pd.DataFrame(data)
        elif csv_path is not None:
            df = pd.read_csv(csv_path)
        else:
            raise ValueError("Provide `data` or `csv_path` for analysis")

        summary = df.describe(include="all").fillna(0).to_dict()
        head_rows = df.head(head).fillna("").to_dict(orient="records")
        return {
            "summary": summary,
            "head": head_rows,
            "rows": int(df.shape[0]),
            "cols": int(df.shape[1]),
        }


TOOLS = {DataAnalyzer.name: DataAnalyzer()}
