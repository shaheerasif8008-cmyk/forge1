from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

# Import entities so Base.metadata is populated for create_all
try:  # pragma: no cover - import side-effect
    from .entities import (
        ChaosExperiment,
        Finding,
        LoadJob,
        TestRun,
        TestScenario,
        TestSuite,
    )
except Exception:
    # During certain tooling or partial imports, entities may not be available
    pass


