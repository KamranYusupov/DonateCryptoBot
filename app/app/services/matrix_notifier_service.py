import asyncio
from typing import List

from app.core.config import settings
from app.keyboards.donate import get_donate_keyboard
from app.models.telegram_user import DonateStatus
from app.repositories.telegram_user import RepositoryTelegramUser
from app.schemas.telegram import SendTextMessageTuple
from app.services.infra.telegram_bot_service import TelegramBotService
from app.services.base.crud_service import CrudServiceMixin
from app.utils.texts import (
    get_sponsor_activation_text,
    get_system_transaction_message_text,
    get_sponsor_transaction_message_text,
    get_matrix_transaction_message_text,
)
from app.schemas.transaction import (
    DonateTransactionContextSchema,
    SystemTransactionContextSchema,
    SponsorTransactionContextSchema,
    MatrixTransactionContextSchema,
)


class MatrixActivationNotifierService:
    def __init__(
            self,
            repository_telegram_user: RepositoryTelegramUser,
            telegram_bot_service: TelegramBotService,
    ):
        self._repository_telegram_user = repository_telegram_user
        self._telegram_bot_service = telegram_bot_service

    async def send_transaction_message(
            self,
            context: DonateTransactionContextSchema,
    ) -> None:
        messages: List[SendTextMessageTuple] = []
        if isinstance(context, SystemTransactionContextSchema):
            message_text = get_system_transaction_message_text(
                quantity=context.quantity
            )
            messages.append(
                SendTextMessageTuple(
                    chat_id=context.receiver.chat_id,
                    text=message_text
                )
            )

        elif isinstance(context, SponsorTransactionContextSchema):
            private_message_text = get_sponsor_transaction_message_text(
                sender_str=context.sender_str,
                status=context.status,
                sponsor_depth=context.sponsor_depth,
                quantity=context.quantity,
            )
            public_message_text = get_sponsor_transaction_message_text(
                sender_str="",
                status=context.status,
                sponsor_depth=context.sponsor_depth,
                quantity=context.quantity,
                is_public=True,
            )
            messages.extend([
                SendTextMessageTuple(
                    chat_id=context.receiver.chat_id,
                    text=private_message_text,
                ),
                SendTextMessageTuple(
                    chat_id=settings.donates_channel_id,
                    text=public_message_text,
                ),
                SendTextMessageTuple(
                    chat_id=settings.private_donates_channel_id,
                    text=private_message_text,
                )
            ])

        elif isinstance(context, MatrixTransactionContextSchema):
            private_message_text = get_matrix_transaction_message_text(
                receiver_str=context.receiver.full_username,
                status=context.status,
                quantity=context.quantity,
                matrix_length=context.matrix_length,
                triumph=context.triumph,
            )
            public_message_text = get_matrix_transaction_message_text(
                receiver_str=context.receiver.full_username,
                status=context.status,
                quantity=context.quantity,
                matrix_length=context.matrix_length,
                triumph=context.triumph,
                is_public=True,
            )

            messages.extend([
                SendTextMessageTuple(
                    chat_id=context.receiver.chat_id,
                    text=public_message_text
                ),
                SendTextMessageTuple(
                    chat_id=settings.donates_channel_id,
                    text=public_message_text,
                ),
                SendTextMessageTuple(
                    chat_id=settings.private_donates_channel_id,
                    text=private_message_text,
                ),
            ])

        else:
            raise ValueError(f"Unsupported transaction context type: {type(context).__name__}")

        await asyncio.gather(*(
            self._telegram_bot_service.send_message(chat_id=msg.chat_id, text=msg.text)
            for msg in messages
        ))

    async def notify_invited_users(
            self,
            sponsor_user_id: int,
            status: DonateStatus,
    ) -> None:
        sponsor = self._repository_telegram_user.get(
            user_id=sponsor_user_id,
        )
        if not sponsor:
            return

        notification_text = get_sponsor_activation_text(
            username=sponsor.username,
            status=status,
        )
        invited_users = self._repository_telegram_user.list(
            sponsor_user_id=sponsor_user_id,
        )

        reply_markup = get_donate_keyboard(
            buttons={"⚡️ Активировать площадку": "donations"}
        )

        await asyncio.gather(*(
            self._telegram_bot_service.send_message(
                chat_id=user.user_id,
                text=notification_text,
                reply_markup=reply_markup,
            )
            for user in invited_users
        ))
