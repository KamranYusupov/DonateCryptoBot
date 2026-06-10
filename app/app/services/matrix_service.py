import datetime
import uuid
from typing import Tuple, Any, Optional

import loguru

from app.models.telegram_user import DonateStatus
from app.repositories.matrix import RepositoryMatrix, RepositoryAddBotToMatrixTaskModel
from app.models import Matrix, AddBotToMatrixTaskModel
from app.schemas.matrix import MatrixEntity, AddBotToMatrixTaskSchema
from app.repositories.telegram_user import RepositoryTelegramUser


class MatrixService:
    def __init__(
            self,
            repository_matrix: RepositoryMatrix,
            repository_telegram_user: RepositoryTelegramUser,
    ) -> None:
        self._repository_matrix = repository_matrix
        self._repository_telegram_user = repository_telegram_user

    async def get_list(self, *args, order_by_create_at: bool = False,**kwargs) -> list[Matrix]:
        return self._repository_matrix.get_list(
            *args,
            order_by_create_at=order_by_create_at,
            **kwargs
        )

    async def get_matrix(self, **kwargs) -> Matrix | None:
        return self._repository_matrix.get(**kwargs)

    async def get_user_matrices(
            self,
            owner_id: uuid.UUID,
            status: DonateStatus | None = None,
    ) -> list[Matrix]:
        return self._repository_matrix.get_user_matrices(
            owner_id=owner_id,
            status=status,
        )

    async def get_parent_matrix(
            self, matrix_id: Matrix.id, status: DonateStatus, return_all: bool = False
    )-> Matrix:
        return self._repository_matrix.get_parent_matrix(
            matrix_id=matrix_id, status=status, return_all=return_all
        )

    async def get_matrix_parents(self, matrix: Matrix, count: int) -> list[Matrix]:
        parents = []

        for _ in range(count):
            current_parent_matrix = self._repository_matrix.get_parent_matrix(
                matrix.id,
                status=matrix.status,
            )
            if not current_parent_matrix:
                break
            parents.append(current_parent_matrix.owner_id)

        return parents

    async def create_matrix(self, matrix: MatrixEntity) -> Matrix:
        return self._repository_matrix.create(obj_in=matrix.model_dump())

    async def delete(self, obj_id: uuid.UUID):
        self._repository_matrix.delete(obj_id=obj_id)

    async def get_unique_statuses_by_owner_id(self, owner_id: uuid.UUID):
        return self._repository_matrix.get_unique_statuses_by_owner_id(
            owner_id=owner_id
        )

