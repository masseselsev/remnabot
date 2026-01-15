"""drop_legacy_columns

Revision ID: af3b4ead5cad
Revises: 914d2590c406
Create Date: 2026-01-15 10:45:49.699051

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af3b4ead5cad'
down_revision: Union[str, None] = '914d2590c406'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('tariffs', 'price')
    op.drop_column('tariffs', 'currency')


def downgrade() -> None:
    op.add_column('tariffs', sa.Column('currency', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('tariffs', sa.Column('price', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
