"""Flexible document ingestion for RAG pipelines.

Supports PDF, CSV, URL, and HTML via LangChain loaders or unstructured.io.
Returns a normalized list of dicts with keys: {"text": str, "metadata": dict}.

Design goals:
- Optional dependencies: dynamically import LangChain or unstructured at runtime
- Graceful fallbacks using stdlib/httpx when possible
- Easy to extend with new formats via a registry
"""

from __future__ import annotations

import csv
import importlib
import json
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import httpx

Document = dict[str, Any]


def _safe_import(module: str, attr: str | None = None) -> Any | None:
    """Best-effort dynamic import for optional deps.

    Returns the module or attribute, or None if unavailable.
    """
    try:
        mod = importlib.import_module(module)
        if attr is None:
            return mod
        return getattr(mod, attr, None)
    except Exception:  # noqa: BLE001
        return None


class DocumentLoader:
    """Format-aware document loader with pluggable handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[[dict[str, Any]], list[Document]]] = {
            "pdf": self._handle_pdf,
            "csv": self._handle_csv,
            "url": self._handle_url,
            "html": self._handle_html,
        }

    def register_handler(
        self, doc_type: str, handler: Callable[[dict[str, Any]], list[Document]]
    ) -> None:
        """Register a new handler for a custom document type."""
        self._handlers[doc_type.lower()] = handler

    # Public API
    def load(self, sources: Iterable[dict[str, Any]]) -> list[Document]:
        """Load a mixed collection of sources.

        Each source dict should contain at minimum:
          - type: one of {pdf, csv, url, html}
          - path or url: depending on the type
          - metadata: optional dict
        """
        docs: list[Document] = []
        for spec in sources:
            doc_type = str(spec.get("type", "")).lower()
            handler = self._handlers.get(doc_type)
            if handler is None:
                raise ValueError(f"Unsupported document type: {doc_type}")
            docs.extend(handler(spec))
        return docs

    def load_pdf(self, path: str, *, metadata: dict[str, Any] | None = None) -> list[Document]:
        return self._handle_pdf({"type": "pdf", "path": path, "metadata": metadata or {}})

    def load_csv(self, path: str, *, metadata: dict[str, Any] | None = None) -> list[Document]:
        return self._handle_csv({"type": "csv", "path": path, "metadata": metadata or {}})

    def load_url(self, url: str, *, metadata: dict[str, Any] | None = None) -> list[Document]:
        return self._handle_url({"type": "url", "url": url, "metadata": metadata or {}})

    def load_html(self, path: str, *, metadata: dict[str, Any] | None = None) -> list[Document]:
        return self._handle_html({"type": "html", "path": path, "metadata": metadata or {}})

    # Handlers
    def _handle_pdf(self, spec: dict[str, Any]) -> list[Document]:
        path = str(spec.get("path", "")).strip()
        meta = dict(spec.get("metadata", {}))
        if not path:
            return []

        # Try LangChain PyPDFLoader
        pypdf = _safe_import("langchain_community.document_loaders", "PyPDFLoader")
        if pypdf is not None:
            loader = pypdf(path)
            pages = loader.load()
            out: list[Document] = []
            for i, d in enumerate(pages):
                out.append(
                    {
                        "text": str(getattr(d, "page_content", "")),
                        "metadata": {
                            **meta,
                            **(getattr(d, "metadata", {}) or {}),
                            "source": str(path),
                            "page": i,
                            "loader": "langchain_pypdf",
                        },
                    }
                )
            return out

        # Try unstructured
        partition_pdf = _safe_import("unstructured.partition.pdf", "partition_pdf")
        if partition_pdf is not None:
            elements = partition_pdf(filename=path)
            out = [
                {
                    "text": str(getattr(el, "text", "")),
                    "metadata": {**meta, "source": str(path), "loader": "unstructured_pdf"},
                }
                for el in elements
                if str(getattr(el, "text", "")).strip()
            ]
            return out

        # Fallback: no dependency available
        raise RuntimeError(
            "PDF loading requires langchain_community or unstructured to be installed"
        )

    def _handle_csv(self, spec: dict[str, Any]) -> list[Document]:
        path = str(spec.get("path", "")).strip()
        meta = dict(spec.get("metadata", {}))
        if not path:
            return []

        # Try LangChain CSVLoader
        csv_loader = _safe_import("langchain_community.document_loaders", "CSVLoader")
        if csv_loader is not None:
            loader = csv_loader(file_path=path)
            rows = loader.load()
            out: list[Document] = []
            for i, d in enumerate(rows):
                out.append(
                    {
                        "text": str(getattr(d, "page_content", "")),
                        "metadata": {
                            **meta,
                            **(getattr(d, "metadata", {}) or {}),
                            "source": str(path),
                            "row": i,
                            "loader": "langchain_csv",
                        },
                    }
                )
            return out

        # Fallback: stdlib CSV
        out2: list[Document] = []
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                try:
                    text = json.dumps(row, ensure_ascii=False)
                except Exception:  # noqa: BLE001
                    text = ", ".join(f"{k}={v}" for k, v in row.items())
                out2.append(
                    {
                        "text": text,
                        "metadata": {**meta, "source": str(path), "row": i, "loader": "stdlib_csv"},
                    }
                )
        return out2

    def _handle_url(self, spec: dict[str, Any]) -> list[Document]:
        url = str(spec.get("url", "")).strip()
        meta = dict(spec.get("metadata", {}))
        if not url:
            return []

        # Try LangChain UnstructuredURLLoader
        url_loader = _safe_import("langchain_community.document_loaders", "UnstructuredURLLoader")
        if url_loader is not None:
            loader = url_loader(urls=[url])
            docs = loader.load()
            out: list[Document] = []
            for _i, d in enumerate(docs):
                out.append(
                    {
                        "text": str(getattr(d, "page_content", "")),
                        "metadata": {
                            **meta,
                            **(getattr(d, "metadata", {}) or {}),
                            "source": url,
                            "loader": "langchain_url",
                        },
                    }
                )
            return out

        # Fallback: fetch and return raw text
        with httpx.Client(follow_redirects=True, timeout=30.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            text = resp.text
        return [{"text": text, "metadata": {**meta, "source": url, "loader": "httpx"}}]

    def _handle_html(self, spec: dict[str, Any]) -> list[Document]:
        path = str(spec.get("path", "")).strip()
        meta = dict(spec.get("metadata", {}))
        if not path:
            return []

        # Try LangChain UnstructuredHTMLLoader
        html_loader = _safe_import("langchain_community.document_loaders", "UnstructuredHTMLLoader")
        if html_loader is not None:
            loader = html_loader(file_path=path)
            docs = loader.load()
            out: list[Document] = []
            for _i, d in enumerate(docs):
                out.append(
                    {
                        "text": str(getattr(d, "page_content", "")),
                        "metadata": {
                            **meta,
                            **(getattr(d, "metadata", {}) or {}),
                            "source": str(path),
                            "loader": "langchain_html",
                        },
                    }
                )
            return out

        # Try unstructured partition_html
        partition_html = _safe_import("unstructured.partition.html", "partition_html")
        if partition_html is not None:
            elements = partition_html(filename=path)
            out = [
                {
                    "text": str(getattr(el, "text", "")),
                    "metadata": {**meta, "source": str(path), "loader": "unstructured_html"},
                }
                for el in elements
                if str(getattr(el, "text", "")).strip()
            ]
            return out

        # Fallback: read raw file contents
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        return [{"text": text, "metadata": {**meta, "source": str(path), "loader": "raw_html"}}]
