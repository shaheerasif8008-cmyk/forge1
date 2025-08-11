from __future__ import annotations

import pytest

from app.core.employee_builder.employee_builder import EmployeeBuilder


def test_employee_builder_builds_valid_config(tmp_path):
    # Use default base template from repo, but also simulate a custom template override
    # by writing a temporary YAML and pointing builder to it by name.
    # For simplicity, we rely on included base.yaml and standard defaults.

    tools = [
        "api_caller",
        {"name": "web_scraper", "config": {"max_depth": 2}},
    ]

    builder = EmployeeBuilder(
        role_name="Research Assistant",
        description="Helps with literature review and summaries",
        tools=tools,
        template_name="base",
    )

    cfg = builder.build_config()

    assert cfg["role"]["name"] == "Research Assistant"
    assert "rag" in cfg and isinstance(cfg["rag"], dict)
    assert "memory" in cfg and isinstance(cfg["memory"], dict)
    # required_tools from template should be merged (base has none, but test for presence of provided tools)
    tool_names = {t["name"] for t in cfg["tools"]}
    assert {"api_caller", "web_scraper"}.issubset(tool_names)
    assert cfg["memory"]["long_term"]["dimensions"] == 1536


def test_employee_builder_validation_errors():
    with pytest.raises(ValueError):
        EmployeeBuilder(role_name="", description="desc", tools=["x"]).validate()

    with pytest.raises(ValueError):
        EmployeeBuilder(role_name="Role", description="", tools=["x"]).validate()

    with pytest.raises(ValueError):
        EmployeeBuilder(role_name="Role", description="desc", tools=[]).validate()
