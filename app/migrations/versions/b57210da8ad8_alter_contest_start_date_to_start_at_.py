"""alter_contest_start_date_to_start_at_timestamp

Revision ID: b57210da8ad8
Revises: 8be72375accf
Create Date: 2026-05-31 20:50:16.738210

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b57210da8ad8'
down_revision: Union[str, None] = '8be72375accf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index('ix_sponsors_contests_start_date', table_name='sponsors_contests')
    op.drop_index('ix_registration_contests_start_date', table_name='registration_contests')

    op.alter_column(
        'sponsors_contests',
        'start_date',
        new_column_name='start_at',
        type_=sa.DateTime(timezone=True),
        existing_type=sa.Date(),
        postgresql_using='start_date::timestamp with time zone',
    )
    op.alter_column(
        'registration_contests',
        'start_date',
        new_column_name='start_at',
        type_=sa.DateTime(timezone=True),
        existing_type=sa.Date(),
        postgresql_using='start_date::timestamp with time zone',
    )

    op.create_unique_constraint('uq_sponsors_contests_start_datetime', 'sponsors_contests', ['start_at'])
    op.create_unique_constraint('uq_registration_contests_start_datetime', 'registration_contests', ['start_at'])

    op.create_index('ix_sponsors_contest_start_datetime', 'sponsors_contests', ['start_at'], unique=False)
    op.create_index('ix_registration_contest_start_datetime', 'registration_contests', ['start_at'], unique=False)

def downgrade() -> None:
    # 1. Дропаем новые индексы
    op.drop_index('ix_sponsors_contest_start_datetime', table_name='sponsors_contests')
    op.drop_index('ix_registration_contest_start_datetime', table_name='registration_contests')

    # 2. Дропаем новые уникальные констрейнты
    op.drop_constraint('uq_sponsors_contests_start_datetime', 'sponsors_contests', type_='unique')
    op.drop_constraint('uq_registration_contests_start_datetime', 'registration_contests', type_='unique')

    # 3. Откатываем название и тип колонки обратно в Date
    op.alter_column(
        'sponsors_contests',
        'start_at',
        new_column_name='start_date',
        type_=sa.Date(),
        existing_type=sa.DateTime(timezone=True),
        postgresql_using='start_at::date', # Отсекаем время
    )
    op.alter_column(
        'registration_contests',
        'start_at',
        new_column_name='start_date',
        type_=sa.Date(),
        existing_type=sa.DateTime(timezone=True),
        postgresql_using='start_at::date', # Отсекаем время
    )

    # 4. Возвращаем старые индексы
    op.create_index('ix_sponsors_contests_start_date', 'sponsors_contests', ['start_date'], unique=True)
    op.create_index('ix_registration_contests_start_date', 'registration_contests', ['start_date'], unique=True)