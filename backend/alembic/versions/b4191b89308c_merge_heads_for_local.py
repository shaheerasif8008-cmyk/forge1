"""merge heads for local

Revision ID: b4191b89308c
Revises: 14_tracing_observability, add_mem_event_fact
Create Date: 2025-08-17 17:26:55.701213

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4191b89308c'
down_revision: Union[str, None] = ('14_tracing_observability', 'add_mem_event_fact')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
