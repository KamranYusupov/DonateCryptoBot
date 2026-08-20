from typing import Sequence

import loguru
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

from app.models.telegram_user import DonateStatus


def get_donate_keyboard(*, buttons: dict[str, str], sizes: tuple = (1, 1)):
    keyboard = InlineKeyboardBuilder()

    for text, data in buttons.items():
        keyboard.add(InlineKeyboardButton(text=text, callback_data=data))

    return keyboard.adjust(*sizes).as_markup()

def get_donations_buttons(user_statuses: Sequence[DonateStatus]) -> list[InlineKeyboardButton]:
    buttons = []
    for status in list(DonateStatus)[::-1]:
        style = None

        if status in user_statuses:
            style = "success"

        button_text = (
            f"{status.label_emoji} {status.value} - "
            f"${status.amount} {status.label_emoji}"
        )

        button = InlineKeyboardButton(
            text=button_text.upper(),
            callback_data=f"confirm_donate_🟢_{status.amount}",
            style=style,
        )
        buttons.append(button)


    return buttons


def get_start_inline_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(
            text="🎬 Фильм «KOD 💵 DENEG»",
            url="https://t.me/kod_deneg_film/15"
        ),
        InlineKeyboardButton(
            text="👨‍💻 Полная презентация",
            url="https://t.me/kod_deneg_chat/2902"
        ),
        InlineKeyboardButton(
            text="🤖 Обзор функций бота",
            url="https://t.me/kod_deneg_chat/2926"
        ),
    )

    return keyboard.adjust(*(1, 1, 1)).as_markup()
