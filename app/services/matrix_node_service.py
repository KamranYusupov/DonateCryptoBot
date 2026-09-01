import os
from datetime import datetime, timedelta
from typing import Optional, Sequence, List, Tuple
from uuid import UUID

import loguru

from app.models.matrix import MatrixEngineType, Matrix, MatrixNode, MatrixMarketingType
from app.models.telegram_user import DonateStatus, GlobalMarketingDonateStatus
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
            marketing_type: MatrixMarketingType,
            matrix_status: Optional[DonateStatus] = None,
            **kwargs
    ):
        return await self._repository_matrix_node.get(
            *args,
            marketing_type=marketing_type,
            matrix_status=matrix_status,
            **kwargs,
        )

    async def create_matrix_with_root_node(
            self,
            owner_id: UUID,
            marketing_type: MatrixMarketingType,
            matrix_status: Optional[DonateStatus] = None,
    ) -> MatrixNode:
        matrix_entity = MatrixEntity(
            owner_id=owner_id,
            status=matrix_status,
            engine_type=MatrixEngineType.NODES,
            marketing_type=marketing_type
        )
        matrix = await self._repository_matrix.create(
            obj_in=matrix_entity.model_dump()
        )

        matrix_node_schema = MatrixNodeSchema(
            matrix_id=matrix.id,
            owner_id=owner_id,
            level=0,
            position=1,
            marketing_type=marketing_type,
        )
        matrix_node = await self._repository_matrix_node.create(
            obj_in=matrix_node_schema.model_dump()
        )
        matrix.root_node_id = matrix_node.id

        return matrix_node

    async def _find_target_node(
            self,
            sponsor_user_id: int,
            marketing_type: MatrixMarketingType,
            matrix_status: Optional[DonateStatus] = None,
        max_iterations: int = 200,
    ) -> Optional[tuple[MatrixNode, int]]:
        for _ in range(max_iterations):
            if not sponsor_user_id:
                return None

            sponsor = (
                await self._repository_telegram_user
                .get_sponsor_data_by_user_id(user_id=sponsor_user_id)
            )

            if not sponsor:
                return None

            target_node = await self._repository_matrix_node.get(
                owner_id=sponsor.id,
                marketing_type=marketing_type,
                matrix_status=matrix_status,
                for_update=True,
            )
            if target_node:
                return target_node, sponsor.sponsor_user_id

            sponsor_user_id = sponsor.sponsor_user_id

        return None

    async def _find_available_node(
            self,
            sponsor_id: UUID,
            marketing_type: MatrixMarketingType,
            matrix_status: Optional[DonateStatus] = None,
            max_search_level: Optional[int] = None
    ) -> Optional[MatrixNode]:
        sponsor = await self._repository_telegram_user.get(id=sponsor_id)
        sponsor_node = await self._repository_matrix_node.get(
            owner_id=sponsor.id,
            marketing_type=marketing_type,
            matrix_status=matrix_status,
            for_update=True
        )
        if sponsor_node and sponsor_node.children_count < 2:
            return sponsor_node

        target_node = sponsor_node
        sponsor_user_id = sponsor.sponsor_user_id

        if not target_node:
            target_node_result = await self._find_target_node(
                sponsor_user_id=sponsor_user_id,
                marketing_type=marketing_type,
                matrix_status=matrix_status,
            )

            if not target_node_result:
                return None

            target_node, sponsor_user_id = target_node_result

            if target_node.children_count < 2:
                return target_node

        available_node = await self._repository_matrix_node.get_available_node(
            matrix_id=target_node.matrix_id,
            level=target_node.level,
            position=target_node.position,
            max_search_level=max_search_level,
        )

        return available_node

    async def activate_matrix_node(
            self,
            current_user_id: UUID,
            sponsor_id: UUID,
            marketing_type: MatrixMarketingType,
            max_upline_depth: int,
            matrix_status: Optional[DonateStatus] = None,
            max_search_level: Optional[int] = None
    ) -> Tuple[MatrixNode, List[MatrixNode]]:
        inserted_node, is_created = await self._get_or_create_node(
            current_user_id=current_user_id,
            sponsor_id=sponsor_id,
            marketing_type=marketing_type,
            matrix_status=matrix_status,
            max_search_level=max_search_level,
        )
        upline_positions = self.get_upline_node_positions(
            position=inserted_node.position,
            max_upline_depth=max_upline_depth,
        )
        if is_created:
            await self._repository_matrix_node.increment_downline_count_by_positions(
                matrix_id=inserted_node.matrix_id,
                positions=upline_positions,
            )
        active_upline_nodes = await self._repository_matrix_node.get_nodes_by_positions(
            MatrixNode.last_activation >= (
                    datetime.now() - timedelta(days=365)
            ), # FIXME
            matrix_id=inserted_node.matrix_id,
            positions=upline_positions,
            marketing_type=marketing_type,
            matrix_status=matrix_status,
        )

        return inserted_node, active_upline_nodes

    async def _get_or_create_node(
            self,
            current_user_id: UUID,
            sponsor_id: UUID,
            marketing_type: MatrixMarketingType,
            matrix_status: Optional[DonateStatus] = None,
            max_search_level: Optional[int] = None
    ) -> tuple[MatrixNode, bool]:
        current_user_node = await self._repository_matrix_node.get(
            owner_id=current_user_id,
            matrix_status=matrix_status,
            marketing_type=marketing_type,
        )
        if current_user_node:
            current_user_node.last_activation = datetime.now()
            return current_user_node, False

        new_node = await self._insert_new_node(
            current_user_id=current_user_id,
            sponsor_id=sponsor_id,
            marketing_type=marketing_type,
            matrix_status=matrix_status,
            max_search_level=max_search_level,
        )
        return new_node, True

    async def _insert_new_node(
            self,
            current_user_id: UUID,
            sponsor_id: UUID,
            marketing_type: MatrixMarketingType,
            matrix_status: Optional[DonateStatus] = None,
            max_search_level: Optional[int] = None
    ) -> MatrixNode:
        available_node = await self._find_available_node(
            sponsor_id=sponsor_id,
            marketing_type=marketing_type,
            matrix_status=matrix_status,
            max_search_level=max_search_level,
        )
        result = await self._repository_matrix_node.reserve_child_slot(
            matrix_node_id=available_node.id
        )
        if result is None:
            raise ValueError("Could not reserve child slot.")

        position, updated_children_count = result
        new_position = (position * 2) + updated_children_count - 1

        matrix_node_schema = MatrixNodeSchema(
            matrix_id=available_node.matrix_id,
            owner_id=current_user_id,
            position=new_position,
            level=available_node.level + 1,
            marketing_type=marketing_type,
        )
        return await self._repository_matrix_node.create(
            obj_in=matrix_node_schema.model_dump()
        )

    @staticmethod
    def get_upline_node_positions(
            position: int,
            max_upline_depth: int,
    ):
        upline_nodes = []
        level_count = 0
        while position > 1 and level_count < max_upline_depth:
            position = position // 2
            upline_nodes.append(position)
            level_count += 1

        return upline_nodes

    async def get_downline_nodes(
            self,
            matrix_id: UUID,
            position: int,
            level: int,
            max_level: int,
    ) -> list[MatrixNode]:
        return await self._repository_matrix_node.get_downline_nodes(
            matrix_id, position, level, max_level,
        )

    async def get_downline_counts_per_level(
            self,
            matrix_id: UUID,
            position: int,
            level: int,
            max_level: int = 12
    ) -> dict[int, int]:
        return await self._repository_matrix_node.get_downline_counts_per_level(
            matrix_id=matrix_id,
            position=position,
            level=level,
            max_level=max_level,
        )
