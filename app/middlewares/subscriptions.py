from typing import Optional

from aiogram.enums import ChatMemberStatus
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dependency_injector.wiring import inject, Provide

from app.core.container import Container
from app.models import TelegramUser
from app.services.telegram_user_service import TelegramUserService
from app.keyboards.inline import get_subscriptions_keyboard
from app.loader import bot


@inject
async def subscription_checker_middleware(
        handler,
        event: Message,
        data: dict,
):
    """
    Middleware, для обработки проверки подписки на каналы.
    """
    current_user: Optional[TelegramUser] = data.get("current_user")
    real_user: Optional[TelegramUser] = data.get("real_user")
    if not current_user or real_user.is_admin:
        return await handler(event, data)

    reply_markup = await get_subscriptions_keyboard(
        bot=bot,
        user_id=event.from_user.id,
        sponsor_user_id=current_user.sponsor_user_id,
    )
    if not reply_markup:
        return await handler(event, data)

    await event.answer(
        "🔑 Для доступа к основным ресурсам бота, подпишитесь на "
        "ЧАТ, КАНАЛ и KOD💵DENEG ⚡️ АКТИВАЦИИ ⤵️",
        reply_markup=reply_markup
    )
    return

