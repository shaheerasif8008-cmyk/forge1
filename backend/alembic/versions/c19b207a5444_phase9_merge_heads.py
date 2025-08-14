"""phase9 merge heads

Revision ID: c19b207a5444
Revises: 12_auth_v2_models, 6_add_promotion_audit
Create Date: 2025-08-13 15:14:54.401077

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c19b207a5444'
down_revision: Union[str, None] = ('12_auth_v2_models', '6_add_promotion_audit')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
