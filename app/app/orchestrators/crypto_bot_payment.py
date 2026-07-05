from decimal import Decimal

from app.api.schemas.crypto_bot import CryptoInvoiceSchema, UpdateWebhookSchema, InvoicePayloadSchema
from app.models.telegram_user import BillType
from app.services import (
    TelegramUserService,
    CryptoBotProcessedWebhookService,
)
from app.keyboards.reply import get_reply_keyboard
from app.tasks.taskiq.tasks.infra.telegram import (
    send_message_task,
    delete_message_task,
)
from app.tasks.taskiq.tasks.business.donations import (
    send_donations_menu_task
)


class CryptoBotPaymentOrchestrator:
    def __init__(
            self,
            telegram_user_service: TelegramUserService,
            processed_webhook_service: CryptoBotProcessedWebhookService
    ):
        self._telegram_user_service = telegram_user_service
        self._processed_webhook_service = processed_webhook_service

    async def handle_paid_invoice_request(
            self,
            webhook_body: UpdateWebhookSchema,
            invoice_request: CryptoInvoiceSchema,
    ) -> None:
        await self._increment_bill_and_save_webhook(
            webhook_body,
            invoice_request,
        )
        payload = invoice_request.payload
        await self._apply_bot_actions_after_successful_payment(
            chat_id=payload.telegram_id,
            tokens_count=payload.tokens_count,
            messages_to_delete_ids=payload.messages_to_delete_ids,
        )

    async def _increment_bill_and_save_webhook(
            self,
            webhook_body: UpdateWebhookSchema,
            invoice_request: CryptoInvoiceSchema,
    ) -> None:
        telegram_id = invoice_request.payload.telegram_id
        tokens_count = invoice_request.payload.tokens_count

        telegram_user = await self._telegram_user_service.get_telegram_user(user_id=telegram_id)
        await self._telegram_user_service.increment_bill(
            telegram_user_id=telegram_user.id,
            amount=Decimal(tokens_count),
            bill_type=BillType.ACTIVATION
        )

        await self._processed_webhook_service.create_by_request_body(body=webhook_body)

    @staticmethod
    async def _apply_bot_actions_after_successful_payment(
            chat_id: int,
            tokens_count: int,
            messages_to_delete_ids: list[int],
    ) -> None:
        for message_id in messages_to_delete_ids:
            await delete_message_task.kiq(
                chat_id=chat_id,
                message_id=message_id,
            )

        await send_message_task.kiq(
            chat_id=chat_id,
            text="Оплата прошла успешно ✅\n\n"
                 f"На баланс зачислено {tokens_count} USDT.",
            reply_markup=get_reply_keyboard(None) # FIXME
        )

        await send_donations_menu_task.kiq(
            chat_id=chat_id,
            current_user_id=chat_id,
        )







