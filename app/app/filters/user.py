from typing import Any
from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject

from app.models.telegram_user import TelegramUser


class UserExistsFilter(BaseFilter):

    async def __call__(
            self,
            event: TelegramObject,
            current_user: TelegramUser | None = None,
    ) -> bool:
        if not current_user:
            return False

        return True