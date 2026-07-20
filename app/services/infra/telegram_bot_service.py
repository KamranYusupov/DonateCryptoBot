import asyncio
import random
from typing import Any, Union

import loguru
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter

from app import loader
from app.core.config import settings


ChatIDType = Union[int, str]

class TelegramBotService:
    def __init__(self, bot: Bot = loader.bot):
        self._bot = bot

    async def send_message(
            self,
            chat_id: ChatIDType,
            text: str,
            **kwargs: Any
    ) -> bool:
        try:
            await self._bot.send_message(chat_id=chat_id, text=text, **kwargs)
            loguru.logger.info(f"send to {chat_id}")
            await asyncio.sleep(settings.mailing_success_delay_seconds)
            return True
        except TelegramRetryAfter as e:
            delay_seconds = e.retry_after + jitter
            loguru.logger.warning(
                f"Flood control for {chat_id}. Retry after {e.retry_after}s"
            )
            await asyncio.sleep(delay_seconds)
            raise
        except TelegramAPIError:
            return False
        except Exception as e:
            loguru.logger.warning(f"Failed to send to {chat_id}: {e}")
            return False

    async def delete_message(
            self,
            chat_id: ChatIDType,
            message_id: int,
    ) -> bool:
        try:
            await self._bot.delete_message(
                chat_id=chat_id,
                message_id=message_id,
            )
            return True
        except TelegramAPIError:
            return False
