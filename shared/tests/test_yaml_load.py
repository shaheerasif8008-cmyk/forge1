from __future__ import annotations

from shared.testing.runner import load_suite_from_name


def test_load_golden_suite_by_name() -> None:
    suite = load_suite_from_name("golden_basic.yaml")
    assert suite.id == "golden-basic"
    assert suite.name.lower().startswith("golden")
    assert len(suite.cases) >= 3
