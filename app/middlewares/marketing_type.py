from typing import Any, Awaitable, Callable, Dict, Sequence
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, CallbackQuery

from app.models.matrix import MatrixMarketingType


class MarketingTypeMiddleware(BaseMiddleware):

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)

        callback_data = event.data
        marketing_type_name = callback_data.split("_", 1)[0].upper()

        try:
            marketing_type = MatrixMarketingType[marketing_type_name]
        except KeyError:
            marketing_type = None

        data['marketing_type'] = marketing_type

        return await handler(event, data)
