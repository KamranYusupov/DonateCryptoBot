from aiogram.enums import ChatMemberStatus
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dependency_injector.wiring import inject, Provide

from app.services import telegram_user_service
from app.core.container import Container
from app.services.telegram_user_service import TelegramUserService
from app.db.commit_decorator import commit_and_close_session
from app.core.config import settings
from app.keyboards.donate import get_donate_keyboard
from app.keyboards.inline import get_subscriptions_keyboard
from app.loader import bot
from app.utils.bot import send_subscription_menu


@inject
async def subscription_checker_middleware(
        handler,
        event: Message,
        data: dict,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
):
    """
    Middleware, для обработки проверки подписки на каналы.
    """
    current_user = await telegram_user_service.get_telegram_user(
        user_id=event.from_user.id
    )
    if not current_user or not current_user.captcha_verified:
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

