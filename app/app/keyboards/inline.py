from typing import Optional, Dict

import loguru
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.core.config import settings


links_buttons = [
    InlineKeyboardButton(
        text="💬 ЧАТ 💬",
        url=settings.chat_link,
    ),
    InlineKeyboardButton(
        text="📌 КАНАЛ 📌",
        url=settings.channel_link,
    ),
    InlineKeyboardButton(
        text="KOD💵DENEG ⚡️АКТИВАЦИИ",
        url=settings.donates_channel_link,
    ),
]


async def get_subscriptions_buttons(
        bot: Bot,
        user_id: int,
        sponsor_user_id: int,
) -> list[InlineKeyboardButton]:
    chat_result = await bot.get_chat_member(
        chat_id=settings.chat_id, user_id=user_id
    )
    channel_result = await bot.get_chat_member(
        chat_id=settings.channel_id, user_id=user_id
    )
    donates_channel_result = await bot.get_chat_member(
        chat_id=settings.donates_channel_id, user_id=user_id
    )
    results = (chat_result, channel_result, donates_channel_result)

    buttons = [
        links_buttons[ind] for ind, result in enumerate(results)
        if result.status in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED)
    ]
    if buttons:
        buttons.append(
            InlineKeyboardButton(
                text="Проверить подписку ✅",
                callback_data=f"menu_{sponsor_user_id}",
            )
        )

    return buttons


async def get_subscriptions_keyboard(
        bot: Bot,
        user_id: int,
        sponsor_user_id: int,
        sizes: tuple[int] = tuple(),
) -> InlineKeyboardMarkup | None:
    buttons = await get_subscriptions_buttons(
        bot, user_id, sponsor_user_id
    )
    if not buttons:
        return None

    keyboard = InlineKeyboardBuilder()
    keyboard.add(*buttons)
    sizes = (1,) * len(buttons) if not sizes else sizes

    return keyboard.adjust(*sizes).as_markup()


def get_inline_buttons_from_dict(dct: Dict[str, str]):
    inline_buttons = [
        InlineKeyboardButton(
            text=text,
            callback_data=data,
        )
        for text, data in dct.items()
    ]
    return inline_buttons

def get_confirm_inline_keyboard(
        yes_button_data: str,
        no_button_data: str,
        sizes: tuple[int, int] = (1, 1)
):
    yes_button = InlineKeyboardButton(
        text="Да",
        callback_data=yes_button_data,
        style="success",
    )
    no_button = InlineKeyboardButton(
        text="Нет",
        callback_data=no_button_data,
        style="danger",
    )
    keyboard = InlineKeyboardBuilder()
    keyboard.add(yes_button, no_button)
    return keyboard.adjust(*sizes).as_markup()