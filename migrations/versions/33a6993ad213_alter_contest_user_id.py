"""alter contest user_id

Revision ID: 33a6993ad213
Revises: 9ea89eb1fa26
Create Date: 2026-05-28 13:47:05.546077

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '33a6993ad213'
down_revision: Union[str, None] = '9ea89eb1fa26'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(op.f('ix_sponsors_contest_points_sponsor_user_id'), table_name='sponsors_contest_points')
    op.drop_constraint(op.f('fk_sponsors_contest_points_sponsor_user_id_telegram_users'), 'sponsors_contest_points',
                       type_='foreignkey')

    op.alter_column(
        'sponsors_contest_points',
        'sponsor_user_id',
        new_column_name='user_id'
    )

    op.create_index(op.f('ix_sponsors_contest_points_user_id'), 'sponsors_contest_points', ['user_id'], unique=False)
    op.create_foreign_key(
        op.f('fk_sponsors_contest_points_user_id_telegram_users'),
        'sponsors_contest_points',
        'telegram_users',
        ['user_id'],
        ['user_id']
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_sponsors_contest_points_user_id'),
                  table_name='sponsors_contest_points')
    op.drop_constraint(op.f('fk_sponsors_contest_points_user_id_telegram_users'), 'sponsors_contest_points',
                       type_='foreignkey')

    op.alter_column(
        'sponsors_contest_points',
        'user_id',
        new_column_name='sponsor_user_id'
    )

    op.create_index(op.f('ix_sponsors_contest_points_sponsor_user_id'), 'sponsors_contest_points', ['sponsor_user_id'],
                    unique=False)
    op.create_foreign_key(
        op.f('fk_sponsors_contest_points_sponsor_user_id_telegram_users'),
        'sponsors_contest_points',
        'telegram_users',
        ['sponsor_user_id'],
        ['user_id']
    )