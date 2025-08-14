from __future__ import annotations

from typing import Any, Iterable

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ..db.models import LedgerAccount, LedgerJournal, LedgerEntry


def ensure_accounts(db: Session, *, tenant_id: str | None, names_and_types: list[tuple[str, str]]) -> dict[str, int]:
    LedgerAccount.__table__.create(bind=db.get_bind(), checkfirst=True)
    out: dict[str, int] = {}
    for name, typ in names_and_types:
        stmt = pg_insert(LedgerAccount).values(tenant_id=tenant_id, name=name, type=typ)
        stmt = stmt.on_conflict_do_nothing(index_elements=[LedgerAccount.tenant_id, LedgerAccount.name])
        db.execute(stmt)
    db.commit()
    rows = (
        db.query(LedgerAccount)
        .filter(LedgerAccount.tenant_id == tenant_id, LedgerAccount.name.in_([n for n, _ in names_and_types]))
        .all()
    )
    for r in rows:
        out[r.name] = r.id
    return out


def post(db: Session, *, tenant_id: str | None, journal_name: str, external_id: str | None, lines: list[dict[str, Any]]) -> int:
    """Idempotent double-entry post.

    lines: list of {account_name, side, commodity, amount, meta}
    Requires sum(debits) == sum(credits) per commodity.
    """
    LedgerAccount.__table__.create(bind=db.get_bind(), checkfirst=True)
    LedgerJournal.__table__.create(bind=db.get_bind(), checkfirst=True)
    LedgerEntry.__table__.create(bind=db.get_bind(), checkfirst=True)
    # Idempotency: reuse existing journal if external_id matches
    jr = None
    if external_id:
        jr = db.query(LedgerJournal).filter(LedgerJournal.external_id == external_id).one_or_none()
        if jr:
            return jr.id
    jr = LedgerJournal(tenant_id=tenant_id, name=journal_name, external_id=external_id, meta=None)
    db.add(jr)
    db.flush()
    # Validate balance per commodity
    totals: dict[str, int] = {}
    acct_names = [(l["account_name"], "expense") for l in lines]
    acct_map = ensure_accounts(db, tenant_id=tenant_id, names_and_types=acct_names)
    for l in lines:
        commodity = str(l["commodity"]).lower()
        amt = int(l["amount"]) * (1 if str(l["side"]).lower() == "debit" else -1)
        totals[commodity] = totals.get(commodity, 0) + amt
    for commodity, net in totals.items():
        if net != 0:
            raise ValueError(f"Unbalanced journal for {commodity}: {net}")
    # Insert entries
    for l in lines:
        db.add(
            LedgerEntry(
                journal_id=jr.id,
                account_id=acct_map[l["account_name"]],
                commodity=str(l["commodity"]).lower(),
                side=str(l["side"]).lower(),
                amount=int(l["amount"]),
                meta=l.get("meta"),
            )
        )
    db.commit()
    return jr.id


