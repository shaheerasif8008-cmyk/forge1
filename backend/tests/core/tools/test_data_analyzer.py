from __future__ import annotations

from app.core.tools.builtins.data_analyzer import DataAnalyzer


def test_data_analyzer_from_rows():
    tool = DataAnalyzer()
    data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    out = tool.execute(data=data)
    assert out["rows"] == 2
    assert out["cols"] == 2
