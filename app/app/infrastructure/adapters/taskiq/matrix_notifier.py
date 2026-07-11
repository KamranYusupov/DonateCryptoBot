from decimal import Decimal
import uuid

from app.models.telegram_user import DonateStatus
from app.schemas.transaction import MatrixTransactionContextSchema
from app.tasks.taskiq.tasks import send_matrix_transaction_message_task

class MatrixNotifierTaskIQAdapter:

    async def send_matrix_transaction_message(
            self,
            context: MatrixTransactionContextSchema,
            chat_id: int,
            is_public: bool = False,
    ) -> None:
        await send_matrix_transaction_message_task.kiq(
            chat_id=chat_id,
            is_public=is_public,
            receiver_id=context.receiver.id,
            receiver_str=context.receiver.full_username,
            status=context.status,
            matrix_length=context.matrix_length,
            triumph=context.triumph,
            quantity=context.quantity,
        )

