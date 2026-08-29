import uuid
from decimal import Decimal
from typing import Protocol

from app.models.telegram_user import DonateStatus
from app.schemas.transaction import MatrixTransactionContextSchema


class IMatrixNotifierProtocol(Protocol):

    async def send_matrix_transaction_message(
            self,
            context: MatrixTransactionContextSchema,
            chat_id: int,
            display_receiver: bool = False,
    ): ...

