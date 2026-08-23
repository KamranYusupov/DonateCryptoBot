import asyncio
import os

import loguru
from aiogram import Router, F, html
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from dependency_injector.wiring import inject, Provide

from app.core.container import Container
from app.keyboards.inline import get_confirm_inline_keyboard
from app.keyboards.reply import reply_cancel_keyboard, get_reply_keyboard
from app.loader import bot
from app.models import TriumphBillTransactionType
from app.schemas.triumph_bill_transaction import CreateTriumphBillTransactionSchema
from app.services import (
    TriumphBillService,
    TriumphBillTransactionService,
)
from app.services.telegram_user_service import TelegramUserService
from app.keyboards.donate import get_donate_keyboard
from app.use_cases.donations import SendDonationsMenuUseCase
from app.utils.bot import delete_message_or_pass
from app.models.telegram_user import DonateStatus
from app.models.telegram_user import TelegramUser
from app.models.matrix import MatrixMarketingType

triumph_bill_router = Router()

class IncrementTriumphBillState(StatesGroup):
    amount = State()

@triumph_bill_router.callback_query(F.data.startswith("start_increment_trumph_bill"))
@inject
async def start_triumph_bill_handler(
        callback: CallbackQuery,
        state: FSMContext,
        current_user: TelegramUser,
) -> None:
    bill_type = callback.data.split("_")[-1]
    bill_value = getattr(current_user, f"bill_for_{bill_type}")

    if not bill_value:
        await callback.message.edit_text(
            "Баланс равен нулю.",
            reply_markup=get_donate_keyboard(
                buttons={"🔙 Назад": "open_triumph_bill"}
            )
        )
        return

    triumph_bill_limit = DonateStatus.BRILLIANT.amount
    if current_user.triumph_bill is not None and \
            current_user.triumph_bill > triumph_bill_limit:
        await callback.message.edit_text(
            f"Сейф Триумф достиг лимита({triumph_bill_limit} USDT).",
            reply_markup=get_donate_keyboard(
                buttons={"🔙 Назад": "donations"}
            )
        )
        return

    data_to_update = {"bill_type": bill_type}
    await state.set_state(IncrementTriumphBillState.amount)

    message_text = "Напишите сумму USDT для перевода."
    await state.update_data(**data_to_update),
    await callback.message.delete(),
    await callback.message.answer(
        message_text,
        reply_markup=reply_cancel_keyboard,
    )


@triumph_bill_router.message(F.text, IncrementTriumphBillState.amount)
@inject
async def process_amount(
        message: Message,
        state: FSMContext,
        current_user: TelegramUser,
) -> None:

    try:
        amount = int(message.text)
    except ValueError:
        await message.answer(
            "❌ Некорректный ввод. Отправьте положительное, целое число."
        )
        return

    if amount <= 0:
        await message.answer(
            "❌ Некорректный ввод. Отправьте положительное, целое число."
        )
        return

    state_data = await state.get_data()
    bill_type = state_data["bill_type"]
    bill_value = getattr(current_user, f"bill_for_{bill_type}")

    current_triumph_bill = current_user.triumph_bill if current_user.triumph_bill is not None else 0
    triumph_bill_limit = DonateStatus.BRILLIANT.amount
    if current_triumph_bill + amount > triumph_bill_limit:
        await message.answer(
            f"Сейф Триумф достиг лимита({triumph_bill_limit} USDT).",
            reply_markup=get_donate_keyboard(
                buttons={"🔙 Назад": "donations"}
            )
        )
        await state.clear()
        return

    if not bill_value:
        await state.clear()
        await message.answer(
            "❌ Некорректный ввод. Баланс равен нулю.",
            reply_markup=get_reply_keyboard(current_user),
        )
        return
    if amount > bill_value:
        await message.answer(
            "❌ Некорректный ввод. Число превышает сумму на балансе."
        )
        return

    await state.update_data(amount=amount)

    message_text = html.bold(
        f"Пополнить 🏦 Сейф Триумф на {amount} USDT.\n\n"
        "Вы уверены?"
    )

    reply_markup = get_confirm_inline_keyboard(
        yes_button_data="confirm_triumph_bill_increment",
        no_button_data="cancel",
    )

    await message.answer(
        message_text,
        reply_markup=reply_markup,
    )


@triumph_bill_router.callback_query(F.data == "confirm_triumph_bill_increment")
@inject
async def confirm_triumph_bill_increment_handler(
        callback: CallbackQuery,
        state: FSMContext,
        current_user: TelegramUser,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        triumph_bill_service: TriumphBillService = Provide[
            Container.triumph_bill_service
        ],
        triumph_bill_transaction_service: TriumphBillTransactionService = Provide[
            Container.triumph_bill_transaction_service
        ],
        send_donations_menu_use_case: SendDonationsMenuUseCase = Provide[
            Container.send_donations_menu_use_case
        ]
) -> None:
    state_data = await state.get_data()
    bill_type = state_data["bill_type"]
    amount = state_data["amount"]

    bill_field_name = f"bill_for_{bill_type}"
    bill_value = getattr(current_user, bill_field_name)

    current_triumph_bill = current_user.triumph_bill if current_user.triumph_bill is not None else 0
    triumph_bill_limit = DonateStatus.BRILLIANT.amount
    if current_triumph_bill + amount > triumph_bill_limit:
        await callback.message.edit_text(
            f"Сейф Триумф достиг лимита({triumph_bill_limit} USDT).",
            reply_markup=get_donate_keyboard(
                buttons={"🔙 Назад": "donations"}
            )
        )
        return

    if not bill_value:
        await state.clear()
        await callback.message.answer(
            "❌ Некорректный ввод. Баланс равен нулю.",
            reply_markup=get_reply_keyboard(current_user),
        )
        return
    if amount > bill_value:
        await callback.message.answer(
            "❌ Некорректный ввод. Число превышает сумму на балансе."
        )
        return

    transaction_schema = CreateTriumphBillTransactionSchema(
        amount=amount,
        telegram_user_id=current_user.id,
        type_=TriumphBillTransactionType.INCREMENT,
    )
    await triumph_bill_service.increment_one(
        user_id=current_user.user_id,
        amount=amount,
    )
    await triumph_bill_transaction_service.create(transaction_schema),
    await telegram_user_service.update(
          obj_id=current_user.id,
        obj_in={bill_field_name: bill_value - amount}
    )

    await delete_message_or_pass(callback.message)
    await callback.message.answer(
        "💸",
        reply_markup=get_reply_keyboard(current_user),
    )
    await callback.message.answer(
        html.bold(f"🏦 Сейф Триумф успешно пополнен на {amount} USDT ✅")
    )
    await send_donations_menu_use_case.execute(
        marketing_type=MatrixMarketingType.START,
        from_user_id=callback.from_user.id,
        current_user_id=current_user.id,
        telegram_method=bot.send_message,
        callback_suffix=callback.data
    )

    await state.clear()

