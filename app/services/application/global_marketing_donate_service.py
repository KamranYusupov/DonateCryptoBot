import uuid
from decimal import Decimal
from typing import List, Tuple

import loguru

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
from app.utils.status import is_status_higher


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
            matrix_max_length: int = settings.global_marketing.matrix_max_length,
            max_upline_depth: int = settings.global_marketing.matrix_max_level,
    ) -> Tuple[MatrixNode, List[DonateTransactionContextSchema]]:
        marketing_scope = GlobalMarketingScope(status=status)
        inserted_node, upline_nodes = await self._matrix_node_service.activate_matrix_node(
            current_user_id=current_user_id,
            sponsor_id=first_sponsor_id,
            marketing_scope=marketing_scope,
            max_upline_depth=max_upline_depth,
        )
        transactions_data = []
        matrix_transaction = await self._get_transaction_for_matrix(
            upline_nodes=upline_nodes,
            status=status,
            matrix_max_length=matrix_max_length,
        )
        transactions_data.append(matrix_transaction)

        return inserted_node, transactions_data

    async def _find_donate_node(
            self,
    ): ...

    async def _get_transaction_for_matrix(
            self,
            upline_nodes: List[MatrixNode],
            status: GlobalMarketingDonateStatus,
            matrix_max_length: int = settings.global_marketing.matrix_max_length,
            transaction_percent: int | Decimal = \
                    settings.global_marketing.donates_config.matrix_donate_transaction_percent,
    ): #FIXME: add _find_donate_node realization
        send_to_system = False
        try:
            donate_receiver_node = upline_nodes[status.index]
        except IndexError:
            if upline_nodes[-1].position == 1:
                donate_receiver_node = upline_nodes[-1]
                send_to_system = True

        receiver = await self._repository_telegram_user.get(
            id=donate_receiver_node.owner_id
        )
        # if not is_status_higher(
        #     status,
        #     receiver.status,
        #     or_equal=True,
        # ):

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
        )

        return transaction
