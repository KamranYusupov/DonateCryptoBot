import uuid
from typing import Optional, Sequence, List

import loguru
from sqlalchemy import (
    select,
    func,
    update,
    cast,
    BigInteger,
    ARRAY,
)
from app.models.telegram_user import DonateStatus
from app.schemas.marketing import MatrixMarketingScope
from .base import RepositoryBase
from app.models.matrix import Matrix, MatrixNode, MatrixMarketingType
from app.core.config import settings

_MARKETING_STATUS_COLUMNS_MAPPING = {
    MatrixMarketingType.START: Matrix.status,
    MatrixMarketingType.GLOBAL: Matrix.global_marketing_status,
}


class RepositoryMatrix(RepositoryBase[Matrix]):
    """Репозиторий матрицы"""

    async def get_list(self, *args, order_by_create_at: bool = False, **kwargs):
        statement = select(Matrix).filter(*args).filter_by(**kwargs)

        if order_by_create_at:
            statement = statement.order_by(Matrix.created_at)

        result = await self._session.execute(statement)
        return result.scalars().all()

    async def get_parent_matrix(
            self,
            matrix_id: uuid.UUID,
            marketing_scope: MatrixMarketingScope,
            return_all: bool = False,
            for_update: bool = False,
    ) -> Matrix | list[Matrix]:
        status_column = _MARKETING_STATUS_COLUMNS_MAPPING[marketing_scope.marketing_type]
        statement = (
            select(Matrix)
            .where(
                (status_column == marketing_scope.status)
                & (Matrix.matrices.has_key(str(matrix_id)))
            )
            .order_by(Matrix.created_at)
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self._session.execute(statement)
        if return_all:
            return result.scalars().all()

        return result.scalars().first()

    async def get_user_matrices(
            self,
            owner_id: uuid.UUID,
            marketing_scope: MatrixMarketingScope | None = None,
            for_update: bool = False,
    ) -> list[Matrix]:
        statement_where_args = (Matrix.owner_id == owner_id, )

        if marketing_scope:
            status_column = _MARKETING_STATUS_COLUMNS_MAPPING[marketing_scope.marketing_type]
            statement_where_args += (status_column == marketing_scope.status)

        statement = (
            select(Matrix)
            .where(*statement_where_args)
            .order_by(Matrix.created_at)
        )
        if for_update:
            statement = statement.with_for_update()

        result = await self._session.execute(statement)
        return result.scalars().all()

    async def get_matrices_by_ids_list(
            self,
            matrices_ids: list[str | uuid.UUID],
            mapping: bool = False,
            for_update: bool = False,
    ) -> list[Matrix]:
        statement = select(Matrix).filter(Matrix.id.in_(matrices_ids))
        if for_update:
            statement = statement.with_for_update()
        result = await self._session.execute(statement)
        matrices = result.scalars().all()

        if not mapping:
            return matrices

        matrices_map = {str(m.id): m for m in matrices}
        return [matrices_map[str(i)] for i in matrices_ids]

    async def get_owner_ids_by_matrices_ids_list(
            self,
            matrices_ids: list[uuid.UUID]
    ) -> list[uuid.UUID]:
        if not matrices_ids:
            return []

        statement = select(Matrix.id, Matrix.owner_id).where(
            Matrix.id.in_(matrices_ids)
        )

        result = await self._session.execute(statement)
        rows = result.all()
        mapping = {str(row.id): row.owner_id for row in rows}

        return [mapping[str(i)] for i in matrices_ids]

    async def get_unique_statuses_by_owner_id(self, owner_id: uuid.UUID) -> Sequence[DonateStatus]:
        statement = (
            select(Matrix.status)
            .filter_by(owner_id=owner_id)
            .distinct()
        )

        result = await self._session.execute(statement)
        return result.scalars().all()

    async def get_order_map(self, matrix_ids: list[str]) -> dict[str, int]:
        statement = (
            select(Matrix.id)
            .filter(Matrix.id.in_(matrix_ids))
            .order_by(Matrix.created_at)
        )
        result = await self._session.execute(statement)

        return {
            str(matrix_id): index
            for index, matrix_id in enumerate(result.scalars().all())
        }


class RepositoryMatrixNode(RepositoryBase[MatrixNode]):
    def _base_node_select(
            self,
            *args,
            marketing_scope: Optional[MatrixMarketingScope] = None,
            for_update: bool = False,
            skip_locked: bool = False,
            **kwargs
    ):
        statement = select(MatrixNode).where(*args).filter_by(**kwargs)

        if for_update:
            statement = (
                statement
                .with_for_update(skip_locked=skip_locked)
            )

        if marketing_scope is not None:
            status_column = \
                _MARKETING_STATUS_COLUMNS_MAPPING[marketing_scope.marketing_type]

            statement = (
                statement
                .join(Matrix, onclause=MatrixNode.matrix)
                .where(status_column == marketing_scope.status)
            )


        return statement

    async def increment_downline_count_by_positions(
            self,
            matrix_id: uuid.UUID,
            positions: Sequence[int],
            returning: bool = False
    ) -> List[MatrixNode] | int:
        statement = (
            update(MatrixNode)
            .where(
                MatrixNode.matrix_id == matrix_id,
                MatrixNode.position.in_(positions)
            )
            .values(downline_count=MatrixNode.downline_count + 1)
        )

        if not returning:
            result = await self._session.execute(statement)
            return result.rowcount

        statement = statement.returning(MatrixNode)
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def get(
            self,
            *args,
            marketing_scope: Optional[MatrixMarketingScope] = None,
            for_update: bool = False,
            skip_locked: bool = False,
            **kwargs
    ) -> Optional[MatrixNode]:

        statement = self._base_node_select(
            *args,
            marketing_scope=marketing_scope,
            for_update=for_update,
            skip_locked=skip_locked,
            **kwargs
        ).limit(1)
        result = await self._session.execute(statement)
        return result.scalars().first()

    async def get_available_node(
            self,
            matrix_id: uuid.UUID,
            position: int,
            level: int,
            max_level: int,
    ):
        absolute_max_level = level + max_level
        power_calc = func.power(2, MatrixNode.level - level)

        statement = (
            select(MatrixNode)
            .where(
                MatrixNode.matrix_id == matrix_id,

                MatrixNode.level > level,
                MatrixNode.level <= absolute_max_level,

                MatrixNode.children_count < 2,
                MatrixNode.position >= position * power_calc,
                MatrixNode.position < (position + 1) * power_calc,
            )
            .order_by(
                MatrixNode.level,
                MatrixNode.position,
            )
            .with_for_update(skip_locked=True)
            .limit(1)
        )

        result = await self._session.execute(statement)
        return result.scalars().first()

    async def get_downline_nodes(
            self,
            matrix_id: uuid.UUID,
            position: int,
            level: int,
            max_level: int = settings.matrix_max_level
    ) -> list[MatrixNode]:
        power_calc = func.power(2, MatrixNode.level - level)

        statement = (
            select(MatrixNode)
            .where(
                MatrixNode.matrix_id == matrix_id,
                MatrixNode.level > level,
                MatrixNode.level <= level + max_level,
                MatrixNode.position >= position * power_calc,
                MatrixNode.position < (position + 1) * power_calc,
            )
            .order_by(MatrixNode.level, MatrixNode.position)
        )

        result = await self._session.execute(statement)
        return result.scalars().all()

    async def get_nodes_by_positions(
            self,
            *args,
            positions: Sequence[int],
            marketing_scope: Optional[MatrixMarketingScope] = None,
            **kwargs
    ) -> List[MatrixNode]:
        statement = self._base_node_select(
            *args,
            MatrixNode.position.in_(positions),
            marketing_scope=marketing_scope,
            **kwargs
        )

        statement = (
            statement
            .order_by(
                func.array_position(
                    cast(positions, ARRAY(BigInteger)),
                    MatrixNode.position,
                )
            )
        )

        result = await self._session.execute(statement)
        return result.scalars().all()

    async def reserve_child_slot(
            self,
            matrix_node_id: uuid.UUID,
    ) -> tuple[int, int] | None:
        statement = (
            update(MatrixNode)
            .where(
                MatrixNode.id == matrix_node_id,
            )
            .values(children_count=MatrixNode.children_count + 1)
            .returning(MatrixNode.position, MatrixNode.children_count)
        )
        result = await self._session.execute(statement)
        return result.one()
