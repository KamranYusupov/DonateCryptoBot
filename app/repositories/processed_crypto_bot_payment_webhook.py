from app.models.payments import ProcessedCryptoBotPaymentWebhook
from app.repositories.base import RepositoryBase


class RepositoryProcessedCryptoBotPaymentWebhook(
    RepositoryBase[ProcessedCryptoBotPaymentWebhook]
):
    """Репозиторий вебхуков от CryptoBot"""
