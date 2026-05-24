"""obj_id matrix task

Revision ID: 05472b4ff833
Revises: c3eaa1f6b9cb
Create Date: 2026-05-24 16:57:22.980534

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '05472b4ff833'
down_revision: Union[str, None] = 'c3eaa1f6b9cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('add_to_matrix_tasks', sa.Column('engine_type', sa.Enum('JSON', 'NODES', name='matrixenginetype'),
                                                   server_default=sa.text("'JSON'"), nullable=False))
    op.create_index(op.f('ix_add_to_matrix_tasks_engine_type'), 'add_to_matrix_tasks', ['engine_type'], unique=False)

    op.drop_index(op.f('ix_add_to_matrix_tasks_matrix_id'), table_name='add_to_matrix_tasks')
    op.drop_constraint(op.f('fk_add_to_matrix_tasks_matrix_id_matrices'), 'add_to_matrix_tasks', type_='foreignkey')

    op.alter_column(
        'add_to_matrix_tasks',
        'matrix_id',
        new_column_name='obj_id'
    )
    op.create_index(op.f('ix_add_to_matrix_tasks_obj_id'), 'add_to_matrix_tasks', ['obj_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_add_to_matrix_tasks_obj_id'), table_name='add_to_matrix_tasks')

    op.alter_column(
        'add_to_matrix_tasks',
        'obj_id',
        new_column_name='matrix_id'
    )

    op.create_index(op.f('ix_add_to_matrix_tasks_matrix_id'), 'add_to_matrix_tasks', ['matrix_id'], unique=False)
    op.create_foreign_key(op.f('fk_add_to_matrix_tasks_matrix_id_matrices'), 'add_to_matrix_tasks', 'matrices',
                          ['matrix_id'], ['id'])

    op.drop_index(op.f('ix_add_to_matrix_tasks_engine_type'), table_name='add_to_matrix_tasks')
    op.drop_column('add_to_matrix_tasks', 'engine_type')
