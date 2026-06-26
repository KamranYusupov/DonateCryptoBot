import uuid
from typing import Optional, Sequence, List

import loguru
from sqlalchemy import select, func, update

from app.models.telegram_user import DonateStatus
from .base import RepositoryBase
from app.repositories.base.mixins import BulkCreateMixin
from app.models.matrix import Matrix, MatrixNode
from app.core.config import settings


class RepositoryMatrix(RepositoryBase[Matrix]):
    """Репозиторий матрицы"""


    def get_list(self, *args, order_by_create_at: bool = False, **kwargs):
        statement = select(Matrix).filter(*args).filter_by(**kwargs)

        if order_by_create_at:
            statement = statement.order_by(Matrix.created_at)

        return self._session.execute(statement).scalars().all()

    def get_parent_matrix(
            self,
            matrix_id: Matrix.id,
            status: DonateStatus,
            return_all: bool = False,
            for_update: bool = False,
    ) -> Matrix | list[Matrix]:
        statement = (
            select(Matrix)
            .where(
                (Matrix.status == status)
                & (Matrix.matrices.has_key(str(matrix_id)))
            )
            .order_by(Matrix.created_at)
        )
        if for_update:
            statement = statement.with_for_update()
        if return_all:
            result = self._session.execute(statement).scalars().all()
        else:
            result = self._session.execute(statement).scalars().first()

        return result

    def get_user_matrices(
            self,
            owner_id: uuid.UUID,
            status: DonateStatus | None = None,
            for_update: bool = False,
    ) -> list[Matrix]:
        statement_filter_by_kwargs = {"owner_id": owner_id}

        if status:
            statement_filter_by_kwargs["status"] = status

        statement = (
            select(Matrix)
            .filter_by(**statement_filter_by_kwargs)
            .order_by(Matrix.created_at)
        )
        if for_update:
            statement = statement.with_for_update()

        return self._session.execute(statement).scalars().all()

    def get_matrices_by_ids_list(
            self,
            matrices_ids: list[str | uuid.UUID],
            mapping: bool = False,
            for_update: bool = False,
    ) -> list[Matrix]:
        statement = select(Matrix).filter(Matrix.id.in_(matrices_ids))
        if for_update:
            statement = statement.with_for_update()
        matrices = self._session.execute(statement).scalars().all()


        if not mapping:
            return matrices

        matrices_map = {str(m.id): m for m in matrices}
        return [matrices_map[str(i)] for i in matrices_ids]

    def get_owner_ids_by_matrices_ids_list(
            self,
            matrices_ids: list[uuid.UUID]
    ) -> list[uuid.UUID]:
        if not matrices_ids:
            return []

        statement = select(Matrix.id, Matrix.owner_id).where(
            Matrix.id.in_(matrices_ids)
        )

        rows = self._session.execute(statement).all()
        mapping = {str(row.id): row.owner_id for row in rows}

        return [mapping[str(i)] for i in matrices_ids]

    def get_unique_statuses_by_owner_id(self, owner_id: uuid.UUID) -> Sequence[DonateStatus]:
        statement = (
            select(Matrix.status)
            .filter_by(owner_id=owner_id)
            .distinct()
        )

        result = self._session.execute(statement)
        return result.scalars().all()


class RepositoryMatrixNode(RepositoryBase[MatrixNode]):

    def increment_downline_count_by_positions(
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
            result = self._session.execute(statement)
            return result.rowcount

        statement = statement.returning(MatrixNode)
        result = self._session.execute(statement)
        return result.scalars().all()

    def get(
            self,
            *args,
            status: Optional[DonateStatus] = None,
            for_update: bool = False,
            skip_locked: bool = False,
            **kwargs
    ):
        if not status:
            statement = select(MatrixNode).where(*args).filter_by(**kwargs)
            if for_update:
                statement = statement.with_for_update(skip_locked=skip_locked)
            result = self._session.execute(statement.limit(1))
            return result.scalars().first()

        statement = (
            select(MatrixNode)
            .where(*args)
            .filter_by(**kwargs)
            .join(Matrix, onclause=MatrixNode.matrix)
            .where(Matrix.status == status)
            .limit(1)
        )
        if for_update:
            statement = statement.with_for_update(skip_locked=skip_locked)
        result = self._session.execute(statement)
        return result.scalars().first()


    def get_available_node(
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

        result = self._session.execute(statement)
        return result.scalars().first()

    def get_downline_nodes(
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

        return self._session.execute(statement).scalars().all()

    def get_nodes_by_positions(
            self,
            *args,
            positions: Sequence[int],
            **kwargs
    ) -> List[MatrixNode]:
        statement = (
            select(MatrixNode)
            .where(
                *args,
                MatrixNode.position.in_(positions),
            )
            .filter_by(**kwargs)

        )

        result = self._session.execute(statement)
        return result.scalars().all()



