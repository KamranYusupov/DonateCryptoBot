"""alter_triumph_bill

Revision ID: 47f78d9866d5
Revises: f6632455f65b
Create Date: 2026-06-16 18:51:38.395984

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '47f78d9866d5'
down_revision: Union[str, None] = 'f6632455f65b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Сначала превращаем все старые NULL в 0
    op.execute("UPDATE telegram_users SET triumph_bill = 0 WHERE triumph_bill IS NULL;")

    op.alter_column(
        'telegram_users',
        'triumph_bill',
        existing_type=sa.Numeric(18, 6),
        nullable=False,
        server_default=sa.text("0.0")
    )


def downgrade() -> None:
    pass
