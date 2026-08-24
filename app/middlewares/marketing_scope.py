from typing import Any, Awaitable, Callable, Dict, Sequence
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, CallbackQuery

from app.schemas.marketing import create_marketing_scope


class MatrixMarketingScopeCallbackMiddleware(BaseMiddleware):

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)

        marketing_type = data.get('marketing_type')
        current_user = data.get('current_user')
        if marketing_type is None or current_user is None:
            data['marketing_scope'] = None
        else:
            data['marketing_scope'] = create_marketing_scope(
                marketing_type,
                current_user,
            )

        return await handler(event, data)