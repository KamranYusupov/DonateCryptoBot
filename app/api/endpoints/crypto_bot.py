import loguru
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette.responses import Response
from starlette import status

from app.core.container import Container
from app.orchestrators.crypto_bot_payment import CryptoBotPaymentOrchestrator
from app.services.crypto_bot_processed_webhook_service import CryptoBotProcessedWebhookService
from app.api.schemas.crypto_bot import UpdateWebhookSchema, CryptoInvoiceSchema

router = APIRouter(tags=['CryptoBot'], prefix='/crypto-bot')

@router.post(
    '/updates-webhook',
    status_code=status.HTTP_200_OK,
)
@inject
async def updates_webhook(
        body: UpdateWebhookSchema,
        processed_webhook_service: CryptoBotProcessedWebhookService = Depends(
            Provide[Container.crypto_bot_processed_webhook_service],
        ),
        orchestrator: CryptoBotPaymentOrchestrator = Depends(
            Provide[Container.crypto_bot_payment_orchestrator]
        ),
) -> Response:
    if body.update_type != "invoice_paid":
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    is_processed = await processed_webhook_service.exists(
        update_id=body.update_id
    )
    if is_processed:
        return Response(status_code=status.HTTP_200_OK)

    invoice_request = CryptoInvoiceSchema(**body.payload)

    if invoice_request.status == "paid":
        await orchestrator.handle_paid_invoice_request(
            body, invoice_request
        )
        return Response(status_code=status.HTTP_200_OK)

    return Response(status_code=status.HTTP_400_BAD_REQUEST)

