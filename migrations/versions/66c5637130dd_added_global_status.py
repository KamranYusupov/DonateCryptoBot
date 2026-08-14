"""added global status

Revision ID: 66c5637130dd
Revises: 544486ea6b04
Create Date: 2026-08-14 16:03:34.239240

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '66c5637130dd'
down_revision: Union[str, None] = '544486ea6b04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

global_marketing_status_enum = sa.Enum(
    'NOT_ACTIVE',
    'SEPTEMBER',
    'OCTOBER',
    'NOVEMBER',
    'DECEMBER',
    'JANUARY',
    'FEBRUARY',
    'MARCH',
    'APRIL',
    'MAY',
    'JUNE',
    'JULY',
    'AUGUST',
    name='globalmarketingdonatestatus',
)


def upgrade() -> None:
    global_marketing_status_enum.create(
            op.get_bind(),
            checkfirst=True,
        )

    op.add_column(
        'telegram_users',
        sa.Column(
            'global_marketing_status',
            global_marketing_status_enum,
            nullable=True,
        ),
    )

    op.create_index(
        op.f('ix_telegram_users_global_marketing_status'),
        'telegram_users',
        ['global_marketing_status'],
        unique=False,
    )

    op.create_index(
        op.f('ix_telegram_users_status'),
        'telegram_users',
        ['status'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_telegram_users_status'),
        table_name='telegram_users',
    )

    op.drop_index(
        op.f('ix_telegram_users_global_marketing_status'),
        table_name='telegram_users',
    )

    op.drop_column(
        'telegram_users',
        'global_marketing_status',
    )

    op.execute("""
        DROP TYPE IF EXISTS public.globalmarketingdonatestatus;
    """)