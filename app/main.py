import asyncio
from typing import TYPE_CHECKING

import loguru

from app.core.config import settings
from app.handlers.routing import get_all_routers
from app.middlewares import (
    private_chat_only_middleware,
    rate_limit_middleware,
    ban_user_middleware,
    MarketingTypeCallbackMiddleware,
    MatrixMarketingScopeCallbackMiddleware,
    CurrentUserMiddleware,
    subscription_checker_middleware,
    SQLAlchemySessionMiddleware,
)

from loader import dp, bot

if TYPE_CHECKING:
    from app.core.container import Container


async def main(container: "Container"):
    """Запуск бота."""
    await container.init_resources()

    try:
        all_routers = get_all_routers()
        dp.include_routers(all_routers)
        db_manager = await container.db_manager()
        dp.update.outer_middleware(
            SQLAlchemySessionMiddleware(db_manager)
        )

        await bot.delete_webhook(drop_pending_updates=True)

        current_user_middleware = CurrentUserMiddleware()

        dp.message.outer_middleware(current_user_middleware)
        dp.callback_query.outer_middleware(current_user_middleware)

        dp.message.middleware(private_chat_only_middleware)
        dp.message.outer_middleware(rate_limit_middleware)
        dp.message.middleware(subscription_checker_middleware)
        dp.message.middleware(ban_user_middleware)

        dp.callback_query.middleware(ban_user_middleware)
        dp.callback_query.middleware(MarketingTypeCallbackMiddleware())
        dp.callback_query.middleware(MatrixMarketingScopeCallbackMiddleware())

        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await container.shutdown_resources()


if __name__ == "__main__":
    loguru.logger.info("Bot is starting")

    from app.core.container import Container
    container = Container()
    asyncio.run(main(container=container))