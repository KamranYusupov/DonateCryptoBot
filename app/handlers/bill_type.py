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
from app.schemas.marketing import MatrixMarketingScope

bill_type_router = Router()

@bill_type_router.callback_query(
    or_f(
        F.data == "start_transfer",
        MarketingTypeFilter("increment_safe"),
    )
)
@inject
async def bill_type_handler(
        callback: CallbackQuery,
        current_user: TelegramUser,
        marketing_type: MatrixMarketingType,
        marketing_scope: MatrixMarketingScope,
        statistic_service: StatisticService = Provide[
            Container.statistic_service
        ],
) -> None:

    message_text = ''
    callback_prefix = None
    if callback.data == "start_transfer":
        callback_prefix = "transfer"

    elif callback.data.endswith("increment_safe"):
        callback_prefix = f"{marketing_type.label}_start_increment_safe"

        if marketing_type is MatrixMarketingType.START:
            matrix_activation_count = await statistic_service.get_matrix_activations_count()
            registration_count = await statistic_service.get_registrations_count()

            message_text += get_triumph_bill_increase_statistic_text(
                matrix_activation_count=matrix_activation_count,
                registration_count=registration_count,
            )

        safe_value = getattr(current_user, marketing_scope.user_safe_orm_attr)
        message_text += html.bold(
            "\n\n"
            f"🏦 Сейф {marketing_type.title}: "
            f"{format_decimal(safe_value)} USDT.\n\n"
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



