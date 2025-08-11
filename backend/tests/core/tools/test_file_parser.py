from __future__ import annotations

from pathlib import Path

import pytest

from app.core.tools.builtins.file_parser import FileParser


def test_file_parser_csv(tmp_path: Path):
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    tool = FileParser()
    out = tool.execute(path=str(csv_path))
    assert out["type"] == "csv"
    assert len(out["rows"]) == 2


def test_file_parser_txt(tmp_path: Path):
    txt = tmp_path / "note.txt"
    txt.write_text("hello", encoding="utf-8")
    tool = FileParser()
    out = tool.execute(path=str(txt))
    assert out["type"] == "text"
    assert out["text"] == "hello"


def test_file_parser_pdf_requires_pypdf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    pdf = tmp_path / "file.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    tool = FileParser()

    # Force import error inside execute
    # Simulate missing pypdf by patching import system to raise ImportError
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):  # noqa: ANN001
        if name == "pypdf":
            raise ImportError("pypdf missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(RuntimeError):
        tool.execute(path=str(pdf))
