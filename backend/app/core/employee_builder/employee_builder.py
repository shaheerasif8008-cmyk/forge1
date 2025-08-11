"""Employee Builder Core.

Provides `EmployeeBuilder` to construct validated, deployment-ready employee configs
from role inputs and JSON/YAML templates.

Config shape returned by `build_config()`:
{
  "role": {"name": str, "description": str},
  "tools": list[{"name": str, "config": dict}],
  "rag": {"enabled": bool, "top_k": int, "provider": str},
  "memory": {
      "short_term": {"provider": str, "ttl": int},
      "long_term": {"provider": str, "dimensions": int}
  }
}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

TEMPLATES_DIR = Path(__file__).parent / "templates"


class EmployeeBuilder:
    """Builds a validated employee configuration from templates and inputs.

    Args:
        role_name: Human-readable role name for the employee.
        description: Concise description of the employee's purpose and scope.
        tools: List of tool specs. Each entry can be a tool name (str) or a dict
               with keys {"name": str, "config": dict}.
        template_name: Base template filename without extension (default: "base").
    """

    def __init__(
        self,
        role_name: str,
        description: str,
        tools: list[str | dict[str, Any]],
        *,
        template_name: str = "base",
    ) -> None:
        self.role_name = role_name.strip()
        self.description = description.strip()
        self._raw_tools = tools
        # If a specific template was not supplied, try to infer from role_name
        inferred = (
            self._infer_template_name(role_name) if template_name == "base" else template_name
        )
        self.template_name = inferred

        self._template: dict[str, Any] = self._load_base_template(template_name)
        self._tools: list[dict[str, Any]] = self._normalize_tools(self._raw_tools)

    # Public API
    def validate(self) -> None:
        """Validate inputs and ensure required config sections exist.

        Raises:
            ValueError: If validation fails.
        """
        if not self.role_name:
            raise ValueError("role_name cannot be empty")
        if not self.description:
            raise ValueError("description cannot be empty")

        if not self._tools:
            raise ValueError("at least one tool must be provided")

        # Ensure required sections exist in template/config
        rag = self._template.get("rag")
        if not isinstance(rag, dict):
            rag = {}
            self._template["rag"] = rag
        rag.setdefault("enabled", True)
        rag.setdefault("top_k", 5)
        rag.setdefault("provider", "hybrid")

        memory = self._template.get("memory")
        if not isinstance(memory, dict):
            memory = {}
            self._template["memory"] = memory
        short_term = memory.get("short_term")
        if not isinstance(short_term, dict):
            short_term = {}
            memory["short_term"] = short_term
        short_term.setdefault("provider", "redis")
        short_term.setdefault("ttl", 3600)

        long_term = memory.get("long_term")
        if not isinstance(long_term, dict):
            long_term = {}
            memory["long_term"] = long_term
        long_term.setdefault("provider", "pgvector")
        long_term.setdefault("dimensions", 1536)

    def build_config(self) -> dict[str, Any]:
        """Build and return a complete employee configuration.

        Returns:
            A validated configuration dictionary ready for deployment.
        """
        self.validate()

        # Merge required tools from template into normalized tools (dedupe by name)
        required = []
        tmpl_tools = self._template.get("required_tools", [])
        if isinstance(tmpl_tools, list):
            for t in tmpl_tools:
                if isinstance(t, str):
                    required.append({"name": t, "config": {}})
                elif isinstance(t, dict) and isinstance(t.get("name"), str):
                    cfg = t.get("config") if isinstance(t.get("config"), dict) else {}
                    required.append({"name": t["name"], "config": cfg})
        merged_tools: dict[str, dict[str, Any]] = {t["name"]: t for t in self._tools}
        for rt in required:
            if rt["name"] not in merged_tools:
                merged_tools[rt["name"]] = rt

        config: dict[str, Any] = {
            "role": {"name": self.role_name, "description": self.description},
            "tools": list(merged_tools.values()),
            "rag": self._template["rag"],
            "memory": self._template["memory"],
        }
        # Allow template to inject additional defaults (e.g., policies)
        for extra_key in ("policies", "constraints", "defaults"):
            if extra_key in self._template and extra_key not in config:
                config[extra_key] = self._template[extra_key]
        return config

    # Internals
    @staticmethod
    def _load_base_template(template_name: str) -> dict[str, Any]:
        """Load a JSON/YAML template by name from the templates directory.

        The function attempts `<name>.yaml`, `<name>.yml`, then `<name>.json`.
        Returns an empty dict if the template directory/file is missing.
        """
        candidates = [
            TEMPLATES_DIR / f"{template_name}.yaml",
            TEMPLATES_DIR / f"{template_name}.yml",
            TEMPLATES_DIR / f"{template_name}.json",
        ]
        for path in candidates:
            if path.exists():
                if path.suffix in {".yaml", ".yml"}:
                    with path.open("r", encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}
                        if not isinstance(data, dict):
                            raise ValueError(f"Template {path} must contain a mapping at top level")
                        return data
                elif path.suffix == ".json":
                    with path.open("r", encoding="utf-8") as f:
                        data = json.load(f) or {}
                        if not isinstance(data, dict):
                            raise ValueError(f"Template {path} must contain an object at top level")
                        return data
        # Default empty template; downstream defaults will fill required fields
        return {}

    @staticmethod
    def _infer_template_name(role_name: str) -> str:
        """Infer a template filename from a role name.

        Example mappings:
          - "Sales Agent" → "sales_agent"
          - "Research Assistant" → "research_assistant"
          - "Customer Support" → "customer_support"
        Falls back to "base".
        """
        key = role_name.strip().casefold().replace(" ", "_")
        mapping = {
            "sales_agent": "sales_agent",
            "research_assistant": "research_assistant",
            "customer_support": "customer_support",
        }
        return mapping.get(key, "base")

    @staticmethod
    def _normalize_tools(tools: list[str | dict[str, Any]]) -> list[dict[str, Any]]:
        """Normalize a mixed tools list to a uniform list of dict specs.

        Each normalized entry has keys: {"name": str, "config": dict}.
        """
        normalized: list[dict[str, Any]] = []
        for t in tools:
            if isinstance(t, str):
                name = t.strip()
                if not name:
                    continue
                normalized.append({"name": name, "config": {}})
            elif isinstance(t, dict):
                name_val = t.get("name")
                if not isinstance(name_val, str) or not name_val.strip():
                    continue
                cfg = t.get("config")
                cfg_dict = cfg if isinstance(cfg, dict) else {}
                normalized.append({"name": name_val.strip(), "config": cfg_dict})
        return normalized
