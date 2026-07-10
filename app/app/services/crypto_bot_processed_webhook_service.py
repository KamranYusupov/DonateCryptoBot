from app.api.schemas.crypto_bot import UpdateWebhookSchema
from app.repositories.processed_crypto_bot_payment_webhook import RepositoryProcessedCryptoBotPaymentWebhook
from app.services.base.crud_service import CrudServiceMixin


class CryptoBotProcessedWebhookService(CrudServiceMixin[RepositoryProcessedCryptoBotPaymentWebhook]):
    def __init__(
            self,
            repository_processed_webhook: RepositoryProcessedCryptoBotPaymentWebhook,
    ) -> None:
        super().__init__(repository=repository_processed_webhook)
        self._repository_processed_webhook = repository_processed_webhook

    async def get_by_update_id(self, update_id: int):
        return await self._repository_processed_webhook.get(update_id=update_id)

    async def exists(self, update_id: int):
        return await self._repository_processed_webhook.exists(update_id=update_id)

    async def create_by_request_body(self, body: UpdateWebhookSchema):
        return await self._repository_processed_webhook.create(obj_in=body.model_dump())