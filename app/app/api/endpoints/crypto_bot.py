import loguru
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, BackgroundTasks
from starlette.responses import Response
from starlette import status

from app.background_tasks.crypto_bot import handle_invoice_webhook_in_bot
from app.core.container import Container
from app.services.crypto_bot_processed_webhook_service import CryptoBotProcessedWebhookService
from app import loader
from app.api.schemas.crypto_bot import UpdateWebhookSchema, CryptoInvoiceSchema
from app.services.telegram_user_service import TelegramUserService
from app.db.commit_decorator import commit_and_close_session

router = APIRouter(tags=['CryptoBot'], prefix='/crypto-bot')

@router.post(
    '/updates-webhook',
    status_code=status.HTTP_200_OK,
)
@inject
@commit_and_close_session
async def updates_webhook(
        body: UpdateWebhookSchema,
        background_tasks: BackgroundTasks,
        telegram_user_service: TelegramUserService = Depends(
            Provide[Container.telegram_user_service]
        ),
        processed_webhook_service: CryptoBotProcessedWebhookService = Depends(
            Provide[Container.crypto_bot_processed_webhook_service],
        )
) -> Response:
    if body.update_type != "invoice_paid":
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    is_processed = await processed_webhook_service.exists(
        update_id=body.update_id
    )
    if is_processed:
        return Response(status_code=status.HTTP_200_OK)

    request_invoice = CryptoInvoiceSchema(**body.payload)

    if request_invoice.status == "paid":
        telegram_id = request_invoice.payload.telegram_id
        tokens_count = request_invoice.payload.tokens_count

        telegram_user = await telegram_user_service.get_telegram_user(user_id=telegram_id)
        telegram_user.bill_for_activation += tokens_count

        await processed_webhook_service.create_by_request_body(body=body)

        background_tasks.add_task(
            handle_invoice_webhook_in_bot,
            bot=loader.bot,
            telegram_id=telegram_id,
            tokens_count=tokens_count,
            messages_to_delete_ids=request_invoice.payload.messages_to_delete_ids
        )
        return Response(status_code=status.HTTP_200_OK)

    return Response(status_code=status.HTTP_400_BAD_REQUEST)

