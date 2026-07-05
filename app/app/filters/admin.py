from typing import Any
from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject

from app.models.telegram_user import TelegramUser


class IsAdminFilter(BaseFilter):
    """
    Фильтр проверяет наличие прав администратора у фактического пользователя.
    Опирается на данные (real_user), инжектированные в CurrentUserMiddleware.
    """

    async def __call__(
            self,
            event: TelegramObject,
            real_user: TelegramUser | None = None,
    ) -> bool:
        from loguru import logger
        logger.info(str(real_user))
        if not real_user:
            return False

        return bool(real_user.is_admin)