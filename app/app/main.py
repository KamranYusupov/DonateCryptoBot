import asyncio
from typing import TYPE_CHECKING

import loguru

from app.core.config import settings
from app.handlers.routing import get_all_routers
from app.middlewares.throttling import (
    private_chat_only_middleware,
    rate_limit_middleware,
)
from app.middlewares.ban_user import (
    ban_user_middleware,
)
from app.middlewares.session_middleware import SQLAlchemySessionMiddleware
from app.middlewares.subscriptions import subscription_checker_middleware
from loader import dp, bot

if TYPE_CHECKING:
    from app.core.container import Container


async def main(container: 'Container'):
    """Запуск бота."""

    try:
        all_routers = get_all_routers()
        dp.include_routers(all_routers)
        dp.update.outer_middleware(
            SQLAlchemySessionMiddleware(sync_session=container.db())
        )
        dp.message.middleware(private_chat_only_middleware)
        dp.message.middleware(rate_limit_middleware)
        dp.message.middleware(subscription_checker_middleware)
        dp.message.middleware(ban_user_middleware)
        dp.callback_query.middleware(ban_user_middleware)

        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    loguru.logger.info("Bot is starting")

    from app.core.container import Container
    container = Container()
    asyncio.run(main(container=container))