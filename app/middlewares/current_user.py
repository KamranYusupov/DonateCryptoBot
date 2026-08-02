from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from dependency_injector.wiring import Provide, inject

from app.tasks.taskiq.tasks import update_username_task
from app.core.container import Container

class CurrentUserMiddleware(BaseMiddleware):

    @inject
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        telegram_user_service = await Container.telegram_user_service()
        impersonation_service = await Container.impersonation_service()

        from_user = getattr(event, "from_user", None)

        if not from_user:
            return await handler(event, data)

        user = await telegram_user_service.get(user_id=from_user.id)

        if user.username != from_user.username:
            await update_username_task.kiq(
                telegram_user_id=user.id,
                new_username=from_user.username,
            )

        data["real_user"] = user
        data["current_user"] = user

        if not user or not user.is_admin:
            return await handler(event, data)

        impersonation_user_id = await impersonation_service.get_impersonated_user_id()

        if not impersonation_user_id:
            return await handler(event, data)

        impersonated_user = await telegram_user_service.get(user_id=impersonation_user_id)

        if impersonated_user:
            data["current_user"] = impersonated_user

        return await handler(event, data)
