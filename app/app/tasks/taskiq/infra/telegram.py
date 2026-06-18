import time

import loguru
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app import loader
from app.core.taskiq import broker

import asyncio
from taskiq import TaskiqDepends
from aiogram.exceptions import TelegramRetryAfter


@broker.task(retry_on_error=True)
async def send_message_task(
        chat_id: int,
        text: str,
        bot: Bot = loader.bot,
        **kwargs
):
    try:
        await bot.send_message(chat_id=chat_id, text=text, **kwargs)
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        raise e
    except TelegramAPIError:
        return
    except Exception as e:
        loguru.logger.warning(f"Failed to send to {chat_id}: {e}")


@broker.task(retry_on_error=False)
async def mass_mailing_dispatcher(
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

        await asyncio.sleep(0.001)
