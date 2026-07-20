import asyncio
from typing import Optional

import loguru
from taskiq import TaskiqDepends

from app.core.config import settings
from app.core.taskiq import broker
from app.services.infra.telegram_bot_service import TelegramBotService
from app.tasks.taskiq.dependencies.container import ContainerDependency
from app.use_cases.file import SendFileFromLoadedFileIDOrSaveUseCase
from app.loader import bot

from app.utils.itertools import batched


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
async def send_photo_task(
        chat_id: int,
        caption: str,
        file_path: str,
        file_id_path: str,
        delay: Optional[int | float] = None,
        **kwargs,
):
    if delay:
        await asyncio.sleep(delay)

    return await SendFileFromLoadedFileIDOrSaveUseCase.send_photo(
        bot=bot,
        chat_id=chat_id,
        caption=caption,
        file_path=file_path,
        file_id_path=file_id_path,
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
async def mass_mailing_task_by_batches_task(
        chat_ids: list[int],
        text: str,
        batch_size: int = 4000,
        **kwargs,
) -> None:
    for chunk in batched(chat_ids, batch_size):
        await mass_mailing_task.kiq(
            chat_ids=chunk,
            text=text,
            **kwargs,
        )


@broker.task(retry_on_error=False)
async def mass_mailing_task(
        chat_ids: list[int],
        text: str,
        *,
        container: ContainerDependency,
        **kwargs
):
    telegram_bot_service: TelegramBotService = container.telegram_bot_service()

    success_count = 0
    fail_count = 0

    for chat_id in chat_ids:
        success = await telegram_bot_service.send_message(
            chat_id=chat_id,
            text=text,
            **kwargs
        )

        if success:
            success_count += 1
        else:
            fail_count += 1

        await asyncio.sleep(0.04)

    loguru.logger.info(
        f"Mass mailing completed. "
        f"Success: {success_count}, Failed: {fail_count}, Total: {len(chat_ids)}"
    )