from decimal import Decimal

import loguru
from aiogram import Router, F, html
from aiogram.filters import Command, or_f
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from dependency_injector.wiring import Provide, inject

from app.keyboards.donate import get_donate_keyboard
from app.keyboards.inline import get_bill_type_choice_buttons
from app.core.container import Container
from app.models.telegram_user import DonateStatus
from app.services import (
    DonateConfirmService,
    StatisticService,
)
from app.utils.texts import format_decimal, get_triumph_bill_increase_statistic_text
from app.models.telegram_user import TelegramUser
from app.filters.marketing_type import MarketingTypeFilter
from app.models.matrix import MatrixMarketingType

bill_type_router = Router()

@bill_type_router.callback_query(
    or_f(
        MarketingTypeFilter("start_transfer"),
        MarketingTypeFilter("increment_trumph_bill"),
    )
)
@inject
async def bill_type_handler(
        callback: CallbackQuery,
        current_user: TelegramUser,
        marketing_type: MatrixMarketingType,
        statistic_service: StatisticService = Provide[
            Container.statistic_service
        ],
) -> None:

    message_text = ''
    callback_prefix = None
    if callback.data == "start_transfer":
        callback_prefix = "transfer"

    elif callback.data == "increment_trumph_bill":
        callback_prefix = "start_increment_trumph_bill"
        matrix_activation_count = await statistic_service.get_matrix_activations_count()
        registration_count = await statistic_service.get_registrations_count()

        message_text = get_triumph_bill_increase_statistic_text(
            matrix_activation_count=matrix_activation_count,
            registration_count=registration_count,
        )
        message_text += html.bold(
            "\n\n"
            f"🏦 Сейф Триумф: "
            f"{format_decimal(current_user.triumph_bill)} USDT.\n\n"
        )

    if not callback_prefix:
        return

    buttons = get_bill_type_choice_buttons(
        bill_for_withdraw=current_user.bill_for_withdraw,
        bill_for_activation=current_user.bill_for_activation,
        callback_prefix=callback_prefix,
    )
    buttons["🔙 Назад"] = f"{marketing_type.label}_donations"
    await callback.message.edit_text(
        message_text + "Выберите баланс:",
        reply_markup=get_donate_keyboard(
            buttons=buttons,
            sizes=(1, 1, 1),
        )
    )



