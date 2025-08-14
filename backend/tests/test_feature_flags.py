from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.flags.feature_flags import FeatureFlag, is_enabled, set_flag
from app.db.session import engine, get_session


def _get_db() -> Session:
    for s in get_session():
        return s
    raise RuntimeError("no session")


def test_feature_flags_default_and_set() -> None:
    # Create only the feature_flags table; avoid creating vector-dependent tables locally
    FeatureFlag.__table__.create(bind=engine, checkfirst=True)
    db = _get_db()
    tenant_id = "t-1"
    flag = "beta_tool"

    # default is False when not present
    assert is_enabled(db, tenant_id, flag, default=False) is False
    assert is_enabled(db, tenant_id, flag, default=True) is True

    # enable
    set_flag(db, tenant_id, flag, True)
    assert is_enabled(db, tenant_id, flag, default=False) is True

    # disable
    set_flag(db, tenant_id, flag, False)
    assert is_enabled(db, tenant_id, flag, default=True) is False



