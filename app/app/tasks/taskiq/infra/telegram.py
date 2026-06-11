import time

import loguru
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app import loader
from app.core.taskiq import broker


@broker.task
async def send_message_task(
        chat_id: int,
        text: str,
        bot: Bot = loader.bot,
        **kwargs
) -> None:
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            **kwargs,
        )
    except TelegramAPIError as e:
        loguru.logger.error(str(e))
