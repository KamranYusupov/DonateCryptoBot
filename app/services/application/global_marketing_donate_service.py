import uuid
from decimal import Decimal
from typing import List, Tuple

import loguru

from app.services import (
    DonateService,
    MatrixNodeService,
)
from app.models import MatrixNode, TelegramUser
from app.models.telegram_user import GlobalMarketingDonateStatus
from app.schemas.transaction import (
    SystemTransactionContextSchema,
    MatrixTransactionContextSchema,
    DonateTransactionContextSchema,
    TransactionReceiverSchema,
)
from app.repositories import RepositoryTelegramUser, RepositoryMatrixNode
from app.core.config import settings
from app.models.matrix import MatrixMarketingType


class GlobalMarketingDonateService:
    def __init__(
            self,
            donate_service: DonateService,
            matrix_node_service: MatrixNodeService,
            repository_matrix_node: RepositoryMatrixNode,
            repository_telegram_user: RepositoryTelegramUser,
    ) -> None:
        self._donate_service = donate_service
        self._matrix_node_service = matrix_node_service
        self._repository_telegram_user = repository_telegram_user
        self._repository_matrix_node = repository_matrix_node

    async def execute(
            self,
            current_user_id: uuid.UUID,
            first_sponsor_id: uuid.UUID,
            status: GlobalMarketingDonateStatus,
            matrix_max_length: int = settings.global_marketing.matrix_max_length,
            max_upline_depth: int = settings.global_marketing.matrix_max_level,
    ) -> Tuple[MatrixNode, List[DonateTransactionContextSchema]]:
        inserted_node, _ = await self._matrix_node_service.activate_matrix_node(
            current_user_id=current_user_id,
            sponsor_id=first_sponsor_id,
            marketing_type=MatrixMarketingType.GLOBAL,
            matrix_status=None,
            max_upline_depth=max_upline_depth,
        )
        transactions_data = []
        matrix_transaction = await self._get_transaction_for_matrix(
            inserted_node=inserted_node,
            status=status,
            matrix_max_length=matrix_max_length,
        )
        transactions_data.append(matrix_transaction)

        return inserted_node, transactions_data

    async def _find_donate_node_with_receiver(
            self,
            inserted_node: MatrixNode,
            status: GlobalMarketingDonateStatus,
    ) -> tuple[MatrixNode, TelegramUser, bool]:
        status_index = status.index
        allowed_statuses = [
            s for s in GlobalMarketingDonateStatus
            if status_index <= s.index
        ]
        status_order_number = status_index + 1

        next_donate_node_position = inserted_node.position
        while next_donate_node_position != 1:
            upline_node_positions = self._matrix_node_service.get_upline_node_positions(
                position=next_donate_node_position,
                max_upline_depth=status_order_number,
            )
            next_donate_node_position = upline_node_positions[-1]
            next_donate_node = await self._repository_matrix_node.get(
                marketing_type=MatrixMarketingType.GLOBAL,
                position=next_donate_node_position,
            )
            receiver = await self._repository_telegram_user.get(
                TelegramUser.global_marketing_status.in_(allowed_statuses),
                id=next_donate_node.owner_id,
            )
            if not receiver:
                continue

            send_to_system = len(upline_node_positions) < status_order_number
            return next_donate_node, receiver, send_to_system


    async def _get_transaction_for_matrix(
            self,
            inserted_node: MatrixNode,
            status: GlobalMarketingDonateStatus,
            matrix_max_length: int = settings.global_marketing.matrix_max_length,
            transaction_percent: int | Decimal = \
                    settings.global_marketing.donates_config.matrix_donate_transaction_percent,
    ) -> MatrixTransactionContextSchema | SystemTransactionContextSchema:
        donate_receiver_node, receiver, send_to_system = await self._find_donate_node_with_receiver(
            inserted_node=inserted_node,
            status=status,
        )

        receiver_schema = TransactionReceiverSchema.model_validate(receiver)
        transaction_quantity = (status.amount * transaction_percent / 100)

        if send_to_system:
            transaction = SystemTransactionContextSchema(
                receiver=receiver_schema,
                quantity=transaction_quantity,
            )
            return transaction

        transaction = MatrixTransactionContextSchema(
            receiver=receiver_schema,
            quantity=transaction_quantity,
            status=status,
            matrix_length=donate_receiver_node.downline_count,
            matrix_max_length=matrix_max_length,
            marketing_type=MatrixMarketingType.GLOBAL,
        )

        return transaction
