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
            display_receiver: bool = False,
    ) -> None:
        await send_matrix_transaction_message_task.kiq(
            chat_id=chat_id,
            display_receiver=display_receiver,
            receiver_id=context.receiver.id,
            receiver_str=context.receiver.full_username,
            status_label=context.status.label,
            status_emoji=context.status.emoji,
            matrix_length=context.matrix_length,
            matrix_max_length=context.matrix_max_length,
            marketing_type_name=context.marketing_type.name,
            triumph=context.triumph,
            quantity=context.quantity,
        )

