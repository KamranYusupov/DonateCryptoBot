"""matrix_structure_marketing_split

Revision ID: 002a819917a1
Revises: fbdcb212a0ce
Create Date: 2026-08-28 14:15:58.149504

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '002a819917a1'
down_revision: Union[str, None] = '4b3580f5a143'
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


def upgrade():
    op.create_unique_constraint('uq_matrix_id_marketing_type', 'matrices', ['id', 'marketing_type'])

    op.drop_column('matrices', 'global_marketing_status')

    op.add_column(
        'matrix_nodes',
        sa.Column(
            'global_marketing_status',
            global_marketing_status_enum,
            nullable=True,
            server_default=text('null'),
        ),
    )
    op.create_index(op.f('ix_matrix_nodes_global_marketing_status'), 'matrix_nodes', ['global_marketing_status'], unique=False)

    op.add_column('matrix_nodes', sa.Column(
        'marketing_type',
        sa.Enum('START', 'GLOBAL', name='matrixmarketingtype'),
        server_default='START',
        nullable=False
    ))

    op.drop_constraint('fk_matrix_nodes_matrix_id_matrices', 'matrix_nodes', type_='foreignkey')

    op.create_foreign_key(
        'fk_matrix_nodes_composite',
        source_table='matrix_nodes',
        referent_table='matrices',
        local_cols=['matrix_id', 'marketing_type'],
        remote_cols=['id', 'marketing_type'],
        ondelete='CASCADE'
    )

    op.create_check_constraint(
        'ck_matrix_node_global_status_logic',
        'matrix_nodes',
        """
        (marketing_type = 'GLOBAL' AND global_marketing_status IS NOT NULL)
        OR
        (marketing_type = 'START' AND global_marketing_status IS NULL)
        """
    )


def downgrade():
    op.drop_constraint('ck_matrix_node_global_status_logic', 'matrix_nodes', type_='check')

    op.drop_constraint('fk_matrix_nodes_composite', 'matrix_nodes', type_='foreignkey')

    # 3. Восстанавливаем старый простой ForeignKey (только по matrix_id)
    op.create_foreign_key(
        'fk_matrix_nodes_matrix_id_matrices',
        source_table='matrix_nodes',
        referent_table='matrices',
        local_cols=['matrix_id'],
        remote_cols=['id'],
        ondelete='CASCADE'
    )

    op.drop_column('matrix_nodes', 'marketing_type')

    op.drop_index(op.f('ix_matrix_nodes_global_marketing_status'), table_name='matrix_nodes')
    op.drop_column('matrix_nodes', 'global_marketing_status')

    op.add_column(
        'matrices',
        sa.Column(
            'global_marketing_status',
            global_marketing_status_enum,
            nullable=True,
        )
    )


    op.drop_constraint('uq_matrix_id_marketing_type', 'matrices', type_='unique')