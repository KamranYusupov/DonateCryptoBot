import asyncio
from decimal import Decimal
from typing import List

from app.core.config import settings
from app.keyboards.donate import get_donate_keyboard
from app.models.telegram_user import DonateStatus
from app.repositories.telegram_user import RepositoryTelegramUser
from app.utils.concurrency import gather_by_batches
from app.utils.texts import (
    get_sponsor_activation_text,
    get_system_transaction_message_text,
    get_sponsor_transaction_message_text,
)
from app.schemas.transaction import (
    DonateTransactionContextSchema,
    SystemTransactionContextSchema,
    SponsorTransactionContextSchema,
    MatrixTransactionContextSchema,
)
from app.services.interfaces import (
    ITelegramBotProtocol,
    IMatrixNotifierProtocol,
)


class MatrixActivationNotifierService:
    def __init__(
            self,
            repository_telegram_user: RepositoryTelegramUser,
            telegram_bot_adapter: ITelegramBotProtocol,
            matrix_notifier_adapter: IMatrixNotifierProtocol,
    ):
        self._repository_telegram_user = repository_telegram_user
        self._telegram_bot_adapter = telegram_bot_adapter
        self._matrix_notifier_adapter = \
            matrix_notifier_adapter

    async def send_transaction_message(
            self,
            context: DonateTransactionContextSchema,
    ) -> None:
        match context:
            case SystemTransactionContextSchema():
                await self._apply_system_transaction_mailing(context)

            case SponsorTransactionContextSchema():
                await self._apply_sponsor_transaction_mailing(context)

            case MatrixTransactionContextSchema():
                await self._apply_matrix_transaction_mailing(context)

            case _:
                raise ValueError(
                    f"Unsupported transaction "
                    f"context type: {type(context).__name__}"
                )

    async def _apply_system_transaction_mailing(
            self,
            context: SystemTransactionContextSchema,
    ) -> None:
        message_text = get_system_transaction_message_text(
            quantity=context.quantity
        )
        await self._telegram_bot_adapter.send_message(
            chat_id=context.receiver.chat_id,
            text=message_text,
        )

    async def _apply_sponsor_transaction_mailing(
            self,
            context: SponsorTransactionContextSchema,
    ) -> None:
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
        tasks = (
            self._telegram_bot_adapter.send_message(
                chat_id=context.receiver.chat_id,
                text=private_message_text,
            ),
            self._telegram_bot_adapter.send_message(
                chat_id=settings.donates_channel_id,
                text=public_message_text,
            ),
            self._telegram_bot_adapter.send_message(
                chat_id=settings.private_donates_channel_id,
                text=private_message_text,
            ),
        )
        await asyncio.gather(*tasks)

    async def _apply_matrix_transaction_mailing(
            self,
            context: MatrixTransactionContextSchema
    ) -> None:
        tasks = (
            self._matrix_notifier_adapter.send_matrix_transaction_message(
                context,
                chat_id=context.receiver.chat_id,
            ),
            self._matrix_notifier_adapter
            .send_matrix_transaction_message(
                context,
                chat_id=settings.private_donates_channel_id,
            ),
            self._matrix_notifier_adapter
            .send_matrix_transaction_message(
                context,
                chat_id=settings.donates_channel_id,
                is_public=True,
            )
        )
        await asyncio.gather(*tasks)


    async def notify_invited_users(
            self,
            sponsor_user_id: int,
            status: DonateStatus,
    ) -> None:
        sponsor = await self._repository_telegram_user.get(
            user_id=sponsor_user_id,
        )
        if not sponsor:
            return

        notification_text = get_sponsor_activation_text(
            username=sponsor.username,
            status=status,
        )
        invited_users = await self._repository_telegram_user.list(
            sponsor_user_id=sponsor_user_id,
        )

        reply_markup = get_donate_keyboard(
            buttons={"⚡️ Активировать площадку": "donations"}
        )
        tasks = (
            self._telegram_bot_adapter.send_message(
                chat_id=user.user_id,
                text=notification_text,
                reply_markup=reply_markup,
            )
            for user in invited_users
        )
        await gather_by_batches(
            tasks,
            chunk_size=30,
            sleep_after_chunk=2,
        )
