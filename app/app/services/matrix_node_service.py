from datetime import datetime, timedelta
from typing import Optional, Sequence, List, Tuple
from uuid import UUID

import loguru

from app.core.config import settings
from app.models.matrix import MatrixEngineType, Matrix, MatrixNode
from app.models.telegram_user import DonateStatus
from app.repositories.matrix import RepositoryMatrix, RepositoryMatrixNode
from app.repositories.telegram_user import RepositoryTelegramUser
from app.schemas.matrix import MatrixEntity, MatrixNodeSchema
from app.services.base.crud_service import CrudServiceMixin


class MatrixNodeService(CrudServiceMixin[RepositoryMatrixNode]):
    def __init__(
            self,
            repository_matrix: RepositoryMatrix,
            repository_matrix_node: RepositoryMatrixNode,
            repository_telegram_user: RepositoryTelegramUser,
    ) -> None:
        super().__init__(repository=repository_matrix_node)
        self._repository_matrix = repository_matrix
        self._repository_matrix_node = repository_matrix_node
        self._repository_telegram_user = repository_telegram_user

    async def get_node(
            self,
            *args,
            status: Optional[DonateStatus] = None,
            **kwargs
    ):
        return self._repository_matrix_node.get(
            *args,
            status=status,
            **kwargs,
        )

    def create_matrix_with_root_node(
            self,
            owner_id: UUID,
            status: DonateStatus,
    ) -> MatrixNode:
        matrix_entity = MatrixEntity(
            owner_id=owner_id,
            status=status,
            engine_type=MatrixEngineType.NODES
        )
        matrix = self._repository_matrix.create(
            obj_in=matrix_entity.model_dump()
        )

        matrix_node_schema = MatrixNodeSchema(
            matrix_id=matrix.id,
            owner_id=owner_id,
            level=0,
            position=1,
        )
        matrix_node = self._repository_matrix_node.create(
            obj_in=matrix_node_schema.model_dump()
        )
        matrix.root_node_id = matrix_node.id

        return matrix_node

    def _find_available_node(
            self,
            sponsor_id: UUID,
            status: DonateStatus,
    ) -> MatrixNode:
        sponsor = self._repository_telegram_user.get(id=sponsor_id)
        sponsor_node = self._repository_matrix_node.get(
            owner_id=sponsor.id,
            status=status,
            for_update=True,
        )
        if sponsor_node and sponsor_node.children_count < 2:
            return sponsor_node

        target_node = sponsor_node
        available_node = None

        while not available_node:
            if not target_node:
                sponsor = self._repository_telegram_user.get(user_id=sponsor.sponsor_user_id)
                target_node = self._repository_matrix_node.get(
                    owner_id=sponsor.id,
                    status=status,
                )

            available_node = self._repository_matrix_node.get_available_node(
                matrix_id=target_node.matrix_id,
                level=target_node.level,
                position=target_node.position,
                max_level=settings.triumph_matrix_max_level,
            )

            if available_node:
                break

            if sponsor.is_admin:
                available_node = self.create_matrix_with_root_node(
                    owner_id=sponsor.id,
                    status=status,
                )
                break
            else:
                target_node = None

        return available_node

    async def activate_matrix_node(
            self,
            current_user_id: UUID,
            sponsor_id: UUID,
            status: DonateStatus,
    ) -> Tuple[MatrixNode, List[MatrixNode]]:
        inserted_node, is_created = await self._get_or_create_node(
            current_user_id=current_user_id,
            sponsor_id=sponsor_id,
            status=status,
        )
        upline_positions = self.get_upline_node_positions(
            position=inserted_node.position,
        )
        self._repository_matrix_node.increment_downline_count_by_positions(
            matrix_id=inserted_node.matrix_id,
            positions=upline_positions,
        )
        active_upline_nodes = self._repository_matrix_node.get_nodes_by_positions(
            MatrixNode.last_activation >= (
                    datetime.now() - timedelta(days=365)
            ),
            matrix_id=inserted_node.matrix_id,
            positions=upline_positions,
        )

        return inserted_node, active_upline_nodes

    async def _get_or_create_node(
            self,
            current_user_id: UUID,
            sponsor_id: UUID,
            status: DonateStatus,
    ) -> tuple[MatrixNode, bool]:
        current_user_node = self._repository_matrix_node.get(
            owner_id=current_user_id,
            status=status,
            for_update=True,
        )
        if current_user_node:
            current_user_node.last_activation = datetime.now()
            return current_user_node, False

        new_node = await self._insert_new_node(
            current_user_id,
            sponsor_id,
            status,
        )
        return new_node, True

    async def _insert_new_node(
            self,
            current_user_id: UUID,
            sponsor_id: UUID,
            status: DonateStatus
    ) -> MatrixNode:
        available_node = self._find_available_node(sponsor_id, status)
        new_position = (available_node.position * 2) + available_node.children_count
        available_node.children_count += 1

        matrix_node_schema = MatrixNodeSchema(
            matrix_id=available_node.matrix_id,
            owner_id=current_user_id,
            position=new_position,
            level=available_node.level + 1,
        )
        return self._repository_matrix_node.create(
            obj_in=matrix_node_schema.model_dump()
        )

    @staticmethod
    def get_upline_node_positions(position: int):
        upline_nodes = []
        level_count = 0
        while position > 1 and level_count <= settings.triumph_matrix_max_level:
            position = position // 2
            upline_nodes.append(position)
            level_count += 1

        return upline_nodes

    async def get_active_nodes_by_positions(
            self,
            matrix_id: UUID,
            positions: Sequence[int],
    ):
        return self._repository_matrix_node.get_nodes_by_positions(
            MatrixNode.last_activation >= (
                    datetime.now() - timedelta(days=365)
            ),
            matrix_id=matrix_id,
            positions=positions,
        )

    async def get_downline_nodes(
            self,
            matrix_id: UUID,
            position: int,
            level: int,
            max_level: int = settings.matrix_max_level
    ) -> list[MatrixNode]:
        return self._repository_matrix_node.get_downline_nodes(
            matrix_id, position, level, max_level,
        )
