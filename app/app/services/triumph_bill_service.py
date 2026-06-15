from decimal import Decimal

from app.core.config import settings
from app.models import TelegramUser
from app.repositories import RepositoryTelegramUser


class TriumphBillService:
    def __init__(
            self,
            repository_telegram_user: RepositoryTelegramUser,
    ) -> None:
        self._repository_telegram_user = repository_telegram_user

    async def increment_one(self, user_id: int, amount: int) -> None    :
        user = self._repository_telegram_user.get(
            user_id=user_id,
        )
        if user.triumph_bill is None:
            user.triumph_bill = 0

        user.triumph_bill += amount

    async def increase_bills_by_percent(
            self,
            percent: Decimal = settings.triumph_bill_increase_percent
    ) -> None:
        return (
            self._repository_telegram_user
            .increase_triumph_bills_by_percent(percent)
        )