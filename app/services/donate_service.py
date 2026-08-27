import time
import uuid
from copy import copy
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Tuple, Any, Sequence, Optional

import loguru
from dependency_injector.wiring import inject

from app.repositories.telegram_user import RepositoryTelegramUser
from app.repositories.matrix import RepositoryMatrix
from app.repositories.donate import RepositoryDonate
from app.models.telegram_user import TelegramUser, DonateStatus, GlobalMarketingDonateStatus
from app.models.matrix import Matrix, MatrixNode, MatrixMarketingType
from app.schemas.matrix import MatrixEntity
from app.core.config import settings
from app.utils.matrix import (
    collect_matrix_ids,
    find_free_place_in_matrix,
    insert_into_matrices,
)
from app.schemas.transaction import (
    SponsorTransactionContextSchema,
    SystemTransactionContextSchema,
    MatrixTransactionContextSchema,
    DonateTransactionContextSchema,
    TransactionReceiverSchema,
)
from app.schemas.marketing import MatrixMarketingScope, GlobalMarketingScope
from app.models.matrix import MatrixEngineType


class DonateService:
    def __init__(
            self,
            repository_telegram_user: RepositoryTelegramUser,
            repository_matrix: RepositoryMatrix,
            repository_donate: RepositoryDonate,
    ) -> None:
        self._repository_telegram_user = repository_telegram_user
        self._repository_matrix = repository_matrix
        self._repository_donate = repository_donate


    @staticmethod
    def get_sponsor_depth(
            transaction_quantity: Decimal,
            donate_quantity: Decimal,
            marketing_scope: MatrixMarketingScope,
            sponsors_donate_percents: Optional[Tuple[Decimal, Decimal, Decimal]] = None,
    ) -> int | None:
        if sponsors_donate_percents is None:
            sponsors_donate_percents = (
                marketing_scope.config.donates_config.first_sponsor_donate_percent,
                marketing_scope.config.donates_config.second_sponsor_donate_percent,
                marketing_scope.config.donates_config.third_sponsor_donate_percent,
            )

        transaction_percent = int(transaction_quantity * 100 / donate_quantity)

        if transaction_percent in sponsors_donate_percents:
            return sponsors_donate_percents.index(transaction_percent) +  1

        return None

    async def get_matrix_parents(
            self,
            matrix: Matrix,
            count: int,
    ) -> list[Matrix]:
        parents = []
        current_matrix = matrix

        for _ in range(count):
            current_matrix = await self._repository_matrix.get_parent_matrix(
                current_matrix.id,
                status=current_matrix.status,
                for_update=True,
            )
            if not current_matrix:
                break
            parents.append(current_matrix)

        return parents


    @staticmethod
    def update_transactions_data_with_sponsors(
            current_user: TelegramUser,
            first_sponsor: TelegramUser,
            second_sponsor: Optional[TelegramUser],
            third_sponsor: Optional[TelegramUser],
            status: DonateStatus | GlobalMarketingDonateStatus,
            marketing_scope: MatrixMarketingScope,
            sponsors_donate_percents: Optional[Tuple[Decimal, Decimal, Decimal]] = None,
    ) -> list[SponsorTransactionContextSchema]:
        if sponsors_donate_percents is None:
            sponsors_donate_percents = (
                marketing_scope.config.donates_config.first_sponsor_donate_percent,
                marketing_scope.config.donates_config.second_sponsor_donate_percent,
                marketing_scope.config.donates_config.third_sponsor_donate_percent,
            )

        transactions_data = []

        sponsors = (first_sponsor, second_sponsor, third_sponsor)
        sponsor_percents_map = list(zip(sponsors, sponsors_donate_percents))
        for sponsor_depth, (sponsor, percent) in enumerate(sponsor_percents_map, start=1):
            if sponsor is None:
                continue

            sponsor_status = getattr(sponsor, marketing_scope.status_orm_attr)
            if sponsor_status is not None:
                receiver_schema = TransactionReceiverSchema.model_validate(sponsor)
                transaction = SponsorTransactionContextSchema(
                    receiver=receiver_schema,
                    sender_str=current_user.full_username,
                    sponsor_depth=sponsor_depth,
                    status=status,
                    quantity=status.amount * percent / 100,
                )
                transactions_data.append(transaction)

        return transactions_data

    async def update_transactions_data_with_system_transaction(
            self,
            transactions_data: list[DonateTransactionContextSchema],
            donate_sum: Decimal,
    ) -> list[DonateTransactionContextSchema]:
        transactions_quantities = [
            transaction.quantity
            for transaction in transactions_data
        ]
        transactions_sum = sum(transactions_quantities)
        donate_reminder = donate_sum - transactions_sum

        if donate_reminder:
            admin_user = await self._repository_telegram_user.get(is_admin=True)
            receiver_schema = TransactionReceiverSchema.model_validate(admin_user)
            transaction = SystemTransactionContextSchema(
                receiver=receiver_schema,
                quantity=donate_reminder,
            )
            transactions_data.append(transaction)

        return transactions_data

    async def update_transactions_data_with_nodes(
            self,
            nodes: list[MatrixNode],
            donate_sum: Decimal,
            status: DonateStatus | GlobalMarketingDonateStatus,
            matrix_max_length: int,
            triumph: bool = False,
            transaction_percent: Decimal = \
                settings.start_marketing.triumph_matrix_transaction_percent,
    ) -> list[DonateTransactionContextSchema]:
        transaction_quantity = donate_sum * transaction_percent / 100

        owner_ids_node_map = {node.owner_id: node for node in nodes}
        receivers = await self._repository_telegram_user.get_active_users_by_ids(
            ids=list(owner_ids_node_map.keys()),
        )

        transactions_data = [
            MatrixTransactionContextSchema(
                receiver=TransactionReceiverSchema.model_validate(receiver),
                quantity=transaction_quantity,
                matrix_length=owner_ids_node_map[receiver.id].downline_count,
                matrix_max_length=matrix_max_length,
                status=status,
                triumph=triumph,
            )
            for receiver in receivers
        ]

        return transactions_data

    async def _update_transactions_data_with_json_matrix_receivers(
            self,
            matrix: Matrix,
            status: DonateStatus,
            transactions_data: list[DonateTransactionContextSchema],
            free_place_path: list[uuid.UUID | str],
            parents: list[Matrix],
            matrix_max_length: int,
            transaction_percent: Decimal = \
                settings.start_marketing.donates_config.matrix_donate_transaction_percent,
    ) -> list[DonateTransactionContextSchema]:
        transaction_quantity = status.amount * transaction_percent / 100

        path_matrices = list(
            await self._repository_matrix.get_matrices_by_ids_list(
                free_place_path,
                for_update=True,
            )
        )
        path_matrices.extend(parents)
        path_matrices.append(matrix)

        path_matrices_ids_map = {}
        donate_receivers_ids = []
        for path_matrix in path_matrices:
            donate_receivers_ids.append(path_matrix.owner_id)
            path_matrices_ids_map[path_matrix.owner_id] = path_matrix

        donate_receivers = await self._repository_telegram_user.get_active_users_by_ids(
            ids=donate_receivers_ids,
            is_bot=False,
        )

        transactions_data.extend([
            MatrixTransactionContextSchema(
                receiver=TransactionReceiverSchema.model_validate(receiver),
                quantity=transaction_quantity,
                matrix_length=len(path_matrices_ids_map[receiver.id].telegram_users) + 1,
                status=status,
                matrix_max_length=matrix_max_length,
            )
            for receiver in donate_receivers
        ])
        return transactions_data

    async def add_to_matrix(
            self,
            matrix_to_add: Matrix,
            current_user: TelegramUser,
            free_place_level: int,
            free_place_path: list[str],
            parents: list[Matrix],
    ) -> Matrix:
        current_time = datetime.now()
        created_matrix_entity = MatrixEntity(
            owner_id=current_user.id,
            status=matrix_to_add.status,
        )
        created_matrix = await self._repository_matrix.create(obj_in=created_matrix_entity.model_dump())
        created_matrix.created_at = current_time

        matrix_to_add_path_matrices = await self._repository_matrix.get_matrices_by_ids_list(
            free_place_path,
            mapping=True,
            for_update=True,
        )

        matrix_to_add.telegram_users.append(current_user.user_id)
        insert_into_matrices(
            matrix_to_add.matrices,
            free_place_path,
            free_place_level,
            str(created_matrix.id),
        )

        child_matrix_free_level = free_place_level
        child_matrix_path = copy(free_place_path)

        for path_matrix in matrix_to_add_path_matrices:

            child_matrix_free_level -= 1
            child_matrix_path.remove(str(path_matrix.id))

            path_matrix.telegram_users.append(current_user.user_id)
            insert_into_matrices(
                path_matrix.matrices,
                child_matrix_path,
                child_matrix_free_level,
                str(created_matrix.id),
            )

        parent_matrix_free_level = free_place_level
        parent_matrix_path = [str(matrix_to_add.id)] + free_place_path

        for parent_matrix in parents:
            parent_matrix_free_level += 1

            parent_matrix.telegram_users.append(current_user.user_id)
            insert_into_matrices(
                parent_matrix.matrices,
                parent_matrix_path,
                parent_matrix_free_level,
                str(created_matrix.id),
            )

            parent_matrix_path = [str(parent_matrix.id)] + parent_matrix_path

        return created_matrix

    async def handle_matrix_activation(
            self,
            current_user: TelegramUser,
            sponsor: TelegramUser,
            transactions_data: list,
            marketing_scope: MatrixMarketingScope,
            max_matrix_length: int,
            level_length: int = settings.level_length,
            found_matrix: Matrix | None = None
    ) -> Tuple[Matrix, Optional[Matrix]] | None:
        if found_matrix:
            await self._handle_insertion_to_free_matrix(
                found_matrix,
                current_user,
                marketing_scope.status,
                transactions_data,
                level_length,
            )
            return found_matrix, None

        sponsor_matrices = await self._repository_matrix.get_user_matrices(
            owner_id=sponsor.id,
            marketing_scope=marketing_scope,
            for_update=True,
        )

        for matrix in sponsor_matrices:

            if len(matrix.telegram_users) < settings.matrix_max_length:
                created_matrix = await self._handle_insertion_to_free_matrix(
                    matrix,
                    current_user,
                    marketing_scope.status,
                    transactions_data,
                    level_length,
                    max_matrix_length,
                )
                return matrix, created_matrix
        else:
            if sponsor.is_admin:
                matrix_entity = MatrixEntity.from_marketing_scope(
                    owner_id=sponsor.id,
                    engine_type=MatrixEngineType.JSON,
                    marketing_scope=marketing_scope,
                )
                matrix = await self._repository_matrix.create(obj_in=matrix_entity)
                matrix.matrices, matrix.telegram_users = {},  []
                created_matrix = await self._handle_insertion_to_free_matrix(
                    matrix,
                    current_user,
                    marketing_scope.status,
                    transactions_data,
                    level_length,
                    max_matrix_length,
                )
                return matrix, created_matrix

            return await self._find_free_matrix(
                user_to_add=current_user,
                marketing_scope=marketing_scope,
                transactions_data=transactions_data,
                level_length=settings.level_length,
            )


    async def _handle_insertion_to_free_matrix(
            self,
            free_matrix: Matrix,
            current_user: TelegramUser,
            status: DonateStatus,
            transactions_data: list,
            matrix_max_length: int,
            level_length: int = settings.level_length,
    ):
        matrix_ids = collect_matrix_ids(free_matrix.matrices)
        order_map = await self._repository_matrix.get_order_map(list(matrix_ids))

        free_place_path = find_free_place_in_matrix(
            free_matrix.matrices,
            order_map,
            level_length,
        )
        free_place_level = len(free_place_path) + 1
        parents = await self.get_matrix_parents(
            matrix=free_matrix,
            count=settings.matrix_max_level - free_place_level
        )

        await self._update_transactions_data_with_json_matrix_receivers(
            free_matrix,
            status,
            transactions_data,
            free_place_path,
            parents,
            matrix_max_length,
        )
        return await self.add_to_matrix(
            free_matrix,
            current_user,
            free_place_level,
            free_place_path,
            parents,
        )

    async def _find_free_matrix(
            self,
            user_to_add: TelegramUser,
            donate_sum: Decimal,
            marketing_scope: MatrixMarketingScope,
            transactions_data: list,
            level_length: int,
            max_iterations: int = 10000,
    ) -> Tuple[Matrix, Optional[Matrix]] | None:
        current_user = user_to_add
        iter_count = 0

        while iter_count <= max_iterations:
            iter_count += 1

            next_sponsor = await self._repository_telegram_user.get(
                user_id=user_to_add.sponsor_user_id
            )
            next_sponsor_status = getattr(next_sponsor, marketing_scope.status_orm_attr)
            if next_sponsor_status is None or (
                 next_sponsor_status.index < marketing_scope.status.index
            ):
                user_to_add = next_sponsor
                continue

            next_sponsor_matrices = await self._repository_matrix.get_user_matrices(
                owner_id=next_sponsor.id,
                marketing_scope=marketing_scope,
                for_update=True,
            )
            if not next_sponsor_matrices:
                user_to_add = next_sponsor
                continue

            for matrix in next_sponsor_matrices:
                if len(matrix.telegram_users) < settings.matrix_max_length:
                    created_matrix = await self._handle_insertion_to_free_matrix(
                        matrix,
                        current_user,
                        donate_sum,
                        marketing_scope.status,
                        transactions_data,
                        level_length,
                    )
                    return matrix, created_matrix

            if next_sponsor.is_admin:
                matrix_entity = MatrixEntity.from_marketing_scope(
                    owner_id=next_sponsor.id,
                    marketing_scope=marketing_scope,
                    engine_type=MatrixEngineType.JSON,
                )
                matrix = await self._repository_matrix.create(obj_in=matrix_entity)
                matrix.matrices, matrix.telegram_users = {}, []
                created_matrix = await self._handle_insertion_to_free_matrix(
                    matrix,
                    current_user,
                    donate_sum,
                    marketing_scope.status,
                    transactions_data,
                    level_length,
                )
                return matrix, created_matrix
            else:
                user_to_add = next_sponsor
                continue

        return None
