import datetime
import uuid
from typing import Tuple, Any, Optional, Sequence, List

import loguru

from app.models.telegram_user import DonateStatus, GlobalMarketingDonateStatus
from app.repositories.matrix import RepositoryMatrix, RepositoryMatrixNode
from app.models import Matrix
from app.schemas.matrix import MatrixEntity
from app.repositories.telegram_user import RepositoryTelegramUser
from app.services.base.crud_service import CrudServiceMixin
from app.models.matrix import MatrixMarketingType, MatrixEngineType
from app.schemas.marketing import MatrixMarketingScope, create_marketing_scope


class MatrixService(CrudServiceMixin[RepositoryMatrix]):
    def __init__(
            self,
            repository_matrix: RepositoryMatrix,
            repository_matrix_node: RepositoryMatrixNode,
            repository_telegram_user: RepositoryTelegramUser,
    ) -> None:
        super().__init__(repository=repository_matrix)
        self._repository_matrix = repository_matrix
        self._repository_matrix_node = repository_matrix_node
        self._repository_telegram_user = repository_telegram_user

    async def get_list(self, *args, order_by_create_at: bool = False, **kwargs) -> list[Matrix]:
        return await self._repository_matrix.get_list(
            *args,
            order_by_create_at=order_by_create_at,
            **kwargs
        )

    async def get_count(
            self,
            owner_id: uuid.UUID,
            engine_type: MatrixEngineType,
    ) -> int:
        return await self._repository_matrix.get_count(
            owner_id=owner_id,
            engine_type=engine_type,
        )


    async def get_matrix(self, **kwargs) -> Matrix | None:
        return await self._repository_matrix.get(**kwargs)

    async def get_user_matrices(
            self,
            owner_id: uuid.UUID,
            status: DonateStatus | None = None,
    ) -> list[Matrix]:
        return await self._repository_matrix.get_user_matrices(
            owner_id=owner_id,
            status=status,
        )

    async def get_parent_matrix(
            self, matrix_id: Matrix.id, status: DonateStatus, return_all: bool = False
    )-> Matrix:
        return await self._repository_matrix.get_parent_matrix(
            matrix_id=matrix_id, status=status, return_all=return_all
        )

    async def get_matrix_parents(self, matrix: Matrix, count: int) -> list[Matrix]:
        parents = []

        for _ in range(count):
            current_parent_matrix = await self._repository_matrix.get_parent_matrix(
                matrix.id,
                status=matrix.status,
            )
            if not current_parent_matrix:
                break
            parents.append(current_parent_matrix.owner_id)

        return parents

    async def create_matrix(self, matrix: MatrixEntity) -> Matrix:
        return await self._repository_matrix.create(obj_in=matrix.model_dump())

    async def delete(self, obj_id: uuid.UUID):
        await self._repository_matrix.delete(obj_id=obj_id)

    async def get_unique_statuses_by_owner_id(
            self,
            owner_id: uuid.UUID,
    ) -> List[DonateStatus]:
        return await self._repository_matrix.get_unique_statuses_by_owner_id(
            owner_id=owner_id,
        )

    async def get_team_matrix_obj_with_count_by_marketing_scope(
            self,
            owner_id: uuid.UUID,
            marketing_scope: MatrixMarketingScope,
            is_archived: bool = False,
            offset: int | None = None,
            max_downline_nodes_level: int = 4,
    ):
        match marketing_scope.marketing_type:
            case MatrixMarketingType.START:
                matrices_count = await self._repository_matrix.get_count(
                    owner_id=owner_id,
                    engine_type=MatrixEngineType.JSON,
                )
                if offset > matrices_count:
                    triumph_node = await self._repository_matrix_node.get(
                        owner_id=owner_id,
                        marketing_scope=create_marketing_scope(
                            marketing_type=MatrixMarketingType.START,
                            status=DonateStatus.BRILLIANT,
                        ),
                    )
                    return triumph_node, matrices_count

                json_matrix = await self._repository_matrix.get_team_matrix(
                    owner_id=owner_id,
                    offset=offset,
                )
                return json_matrix, matrices_count


            case MatrixMarketingType.GLOBAL:
                matrix_nodes_count = await self._repository_matrix_node.get_count(
                    owner_id=owner_id,
                    marketing_type=marketing_scope.marketing_type,
                )
                matrix_node = await self._repository_matrix_node.get_team_matrix_node(
                    owner_id=owner_id,
                    marketing_type=marketing_scope.marketing_type,
                    offset=offset,
                )
                if not matrix_node:
                    return None, matrix_nodes_count

                return matrix_node, matrix_nodes_count

            case _:
                raise ValueError("Not supported marketing type")


