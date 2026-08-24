from typing import Sequence, List

import loguru
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

from app.models.telegram_user import DonateStatus, GlobalMarketingDonateStatus
from app.models.matrix import MatrixMarketingType


def get_donate_keyboard(*, buttons: dict[str, str], sizes: tuple = (1, 1)):
    keyboard = InlineKeyboardBuilder()

    for text, data in buttons.items():
        keyboard.add(InlineKeyboardButton(text=text, callback_data=data))

    return keyboard.adjust(*sizes).as_markup()

def get_start_marketing_donations_buttons(
        user_statuses: Sequence[DonateStatus]
) -> list[InlineKeyboardButton]:
    buttons = []
    callback_data_template = \
        "{marketing_type_label}_confirm_donate_🟢_{status_name}"

    for status in list(DonateStatus)[::-1]:
        style = None

        if status in user_statuses:
            style = "success"

        button_text = (
            f"{status.emoji} {status.label} - "
            f"${status.amount} {status.emoji}"
        )

        button = InlineKeyboardButton(
            text=button_text.upper(),
            callback_data=callback_data_template.format(
                marketing_type_label=MatrixMarketingType.START.label,
                status_name=status.name,
            ),
            style=style,
        )
        buttons.append(button)


    return buttons

def get_global_marketing_donations_buttons(
        user_statuses: Sequence[GlobalMarketingDonateStatus]
) -> list[InlineKeyboardButton]:
    buttons = []
    callback_data_template = "{marketing_type_label}_confirm_donate_🟢_{status_name}"

    for status in list(GlobalMarketingDonateStatus)[::-1]:

        if status in user_statuses:
            continue

        button_text = (
            f"{status.emoji} {status.label} - "
            f"${status.amount} {status.emoji}"
        )

        button = InlineKeyboardButton(
            text=button_text.upper(),
            callback_data=callback_data_template.format(
                marketing_type_label=MatrixMarketingType.GLOBAL.label,
                status_name=status.name,
            )
        )
        buttons.append(button)


    return buttons


def get_donations_buttons(
        user_statuses: Sequence[DonateStatus | GlobalMarketingDonateStatus],
        marketing_type: MatrixMarketingType
) -> List[InlineKeyboardButton]:
    match marketing_type:
        case MatrixMarketingType.START:
            return get_start_marketing_donations_buttons(user_statuses)
        case MatrixMarketingType.GLOBAL:
            return get_global_marketing_donations_buttons(user_statuses)
        case _:
            raise ValueError("Marketing type not supported.")


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
