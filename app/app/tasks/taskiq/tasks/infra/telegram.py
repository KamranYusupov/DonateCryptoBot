import asyncio
from typing import Optional

from taskiq import TaskiqDepends

from app.core.config import settings
from app.core.taskiq import broker
from app.services.infra.telegram_bot_service import TelegramBotService
from app.tasks.taskiq.dependencies.container import ContainerDependency


@broker.task(retry_on_error=True)
async def send_message_task(
        chat_id: int,
        text: str,
        delay: Optional[int | float] = None,
        *,
        container: ContainerDependency,
        **kwargs
):
    telegram_bot_service: TelegramBotService = container.telegram_bot_service()

    if delay:
        await asyncio.sleep(delay)

    return await telegram_bot_service.send_message(
        chat_id=chat_id,
        text=text,
        **kwargs,
    )


@broker.task(retry_on_error=True)
async def delete_message_task(
        chat_id: int,
        message_id: int,
        *,
        container: ContainerDependency,
):
    telegram_bot_service: TelegramBotService = container.telegram_bot_service()
    return await telegram_bot_service.delete_message(
        chat_id=chat_id,
        message_id=message_id,
    )


@broker.task(retry_on_error=False)
async def mass_mailing_task(
        chat_ids: list[int],
        text: str,
        **kwargs
):
    for chat_id in chat_ids:
        await send_message_task.kiq(
            chat_id=chat_id,
            text=text,
            **kwargs
        )

