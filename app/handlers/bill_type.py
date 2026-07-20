from decimal import Decimal

import loguru
from aiogram import Router, F, html
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from dependency_injector.wiring import Provide, inject

from app.keyboards.donate import get_donate_keyboard
from app.keyboards.inline import get_bill_type_choice_buttons
from app.core.container import Container
from app.models.telegram_user import DonateStatus
from app.services import DonateConfirmService
from app.services.telegram_user_service import TelegramUserService
from app.utils.texts import format_decimal
from app.models.telegram_user import TelegramUser

bill_type_router = Router()


@bill_type_router.callback_query(F.data.startswith("confirm_donate_"))
@bill_type_router.callback_query(F.data == "start_transfer")
@bill_type_router.callback_query(F.data == "increment_trumph_bill")
@inject
async def bill_type_handler(
        callback: CallbackQuery,
        current_user: TelegramUser,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
) -> None:
    callback_data = callback.data.split("_")
    triumph_bill = None

    message_text = ''
    callback_prefix = None
    if callback.data.startswith("confirm_donate_"):
        callback_prefix = "send_" + "_".join(callback_data[1:])
        donate_sum = Decimal(callback.data.split("_")[-1])
        status = donate_confirm_service.get_donate_status(donate_sum)
        supported_statuses_for_triumph_bill = (
            DonateStatus.SILVER,
            DonateStatus.GOLD,
            DonateStatus.PLATINUM,
            DonateStatus.BRILLIANT
        )

        if status in supported_statuses_for_triumph_bill:
            triumph_bill = current_user.triumph_bill

    elif callback.data == "start_transfer":
        callback_prefix = "transfer"

    elif callback.data == "increment_trumph_bill":
        callback_prefix = "start_increment_trumph_bill"
        message_text = html.bold(
            f"🏦 Сейф Триумф: "
            f"{format_decimal(current_user.triumph_bill)} USDT.\n\n"
        )

    if not callback_prefix:
        return

    buttons = get_bill_type_choice_buttons(
        bill_for_withdraw=current_user.bill_for_withdraw,
        bill_for_activation=current_user.bill_for_activation,
        callback_prefix=callback_prefix,
        triumph_bill=triumph_bill,
    )
    buttons["🔙 Назад"] = "donations"
    await callback.message.edit_text(
        message_text + "Выберите баланс:",
        reply_markup=get_donate_keyboard(
            buttons=buttons,
            sizes=(1, 1, 1),
        )
    )


