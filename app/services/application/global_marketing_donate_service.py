import uuid
from typing import List, Tuple

from app.services import (
    DonateService,
    MatrixNodeService,
)
from app.models import MatrixNode
from app.models.telegram_user import GlobalMarketingDonateStatus
from app.schemas.transaction import (
    SponsorTransactionContextSchema,
    SystemTransactionContextSchema,
    MatrixTransactionContextSchema,
    DonateTransactionContextSchema,
    TransactionReceiverSchema,
)
from app.repositories import RepositoryTelegramUser
from app.core.config import settings
from app.schemas.marketing import GlobalMarketingScope


class GlobalMarketingDonateService:
    def __init__(
            self,
            donate_service: DonateService,
            matrix_node_service: MatrixNodeService,
            repository_telegram_user: RepositoryTelegramUser,
    ) -> None:
        self._donate_service = donate_service
        self._matrix_node_service = matrix_node_service
        self._repository_telegram_user = repository_telegram_user

    async def execute(
            self,
            current_user_id: uuid.UUID,
            first_sponsor_id: uuid.UUID,
            status: GlobalMarketingDonateStatus,
    ) -> Tuple[MatrixNode, List[DonateTransactionContextSchema]]:
        marketing_scope = GlobalMarketingScope(status=status)
        inserted_node, upline_nodes = await self._matrix_node_service.activate_matrix_node(
            current_user_id=current_user_id,
            sponsor_id=first_sponsor_id,
            marketing_scope=marketing_scope,
            max_upline_depth=settings.global_marketing_matrix_max_level,
        )
        transactions_data = []
        matrix_transaction = await self._get_transaction_for_matrix(
            upline_nodes=upline_nodes,
            status=status,
        )
        transactions_data.append(matrix_transaction)

        return inserted_node, transactions_data

    async def _get_transaction_for_matrix(
            self,
            upline_nodes: List[MatrixNode],
            status: GlobalMarketingDonateStatus,
    ):
        from loguru import logger

        logger.info(f"upline_nodes: {upline_nodes}")
        logger.info(f"status: {status.index}")

        try:
            donate_receiver_node = upline_nodes[status.index]
        except IndexError:
            if upline_nodes[-1].position == 1:
                donate_receiver_node = upline_nodes[-1]

        receiver = await self._repository_telegram_user.get(
            id=donate_receiver_node.owner_id
        )
        receiver_schema = TransactionReceiverSchema.model_validate(receiver)
        transaction = MatrixTransactionContextSchema(
            receiver=receiver_schema,
            quantity=status.amount,
            status=status,
            matrix_length=settings.global_marketing_matrix_max_length,
        )

        return transaction
