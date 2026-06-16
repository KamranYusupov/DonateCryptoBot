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
from app.models import Matrix
from app.services import TriumphBillService, DonateConfirmService
from app.services.matrix_node_service import MatrixNodeService
from app.services.telegram_user_service import TelegramUserService
from app.keyboards.donate import get_donate_keyboard
from app.core.config import settings
from app.services.matrix_service import MatrixService
from app.use_cases.donations import send_donations_menu
from app.use_cases.file import SendFileFromLoadedFileIDOrSaveUseCase
from app.utils.pagination import Paginator
from app.utils.matrix import get_active_matrices, get_archived_matrices
from app.models.telegram_user import status_list, status_emoji_list, DonateStatus
from app.utils.texts import get_my_team_message, get_matrix_info_message, get_downline_nodes_message, format_decimal
from app.models.telegram_user import TelegramUser

triumph_bill_router = Router()

class IncrementTriumphBillState(StatesGroup):
    amount = State()

@triumph_bill_router.callback_query(F.data == "triumph_bill")
@inject
async def triumph_bill_handler(
        callback: CallbackQuery,
        state: FSMContext,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:
    current_user = await telegram_user_service.get_telegram_user(
        user_id=callback.from_user.id
    )
    message_text = html.bold(
        "🏦 Сейф Триумф: "
        f"{format_decimal(current_user.triumph_bill)} USDT."
    )
    buttons = []
    triumph_bill_limit = DonateStatus.BRILLIANT.get_status_donate_value()
    if current_user.triumph_bill != triumph_bill_limit:
        buttons.append(
            InlineKeyboardButton(
                text="Пополнить сейф",
                style="primary",
                callback_data="increment_trumph_bill",
            )
        )

    buttons.append(
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="donations",
        )
    )
    keyboard = InlineKeyboardBuilder()
    keyboard.add(*buttons)
    await callback.message.edit_text(
        message_text,
        reply_markup=keyboard.adjust(1, 1).as_markup()
    )


@triumph_bill_router.callback_query(F.data.startswith("start_increment_trumph_bill"))
@inject
async def start_triumph_bill_handler(
        callback: CallbackQuery,
        state: FSMContext,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:
    bill_type = callback.data.split("_")[-1]

    current_user = await telegram_user_service.get_telegram_user(
        user_id=callback.from_user.id
    )
    bill_value = getattr(current_user, f"bill_for_{bill_type}")

    if not bill_value:
        await callback.message.edit_text(
            "Баланс равен нулю.",
            reply_markup=get_donate_keyboard(
                buttons={"🔙 Назад": "open_triumph_bill"}
            )
        )
        return

    triumph_bill_limit = DonateStatus.BRILLIANT.get_status_donate_value()
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
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
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

    current_user = await telegram_user_service.get_telegram_user(
        user_id=message.from_user.id
    )
    bill_value = getattr(current_user, f"bill_for_{bill_type}")

    current_triumph_bill = current_user.triumph_bill if current_user.triumph_bill is not None else 0
    triumph_bill_limit = DonateStatus.BRILLIANT.get_status_donate_value()
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
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        triumph_bill_service: TriumphBillService = Provide[
            Container.triumph_bill_service
        ]
) -> None:
    state_data = await state.get_data()
    bill_type = state_data["bill_type"]
    amount = state_data["amount"]


    current_user = await telegram_user_service.get_telegram_user(
        user_id=callback.from_user.id
    )
    bill_field_name = f"bill_for_{bill_type}"
    bill_value = getattr(current_user, bill_field_name)

    current_triumph_bill = current_user.triumph_bill if current_user.triumph_bill is not None else 0
    triumph_bill_limit = DonateStatus.BRILLIANT.get_status_donate_value()
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

    await triumph_bill_service.increment_one(
        user_id=current_user.user_id,
        amount=amount,
    )
    await telegram_user_service.update(
        obj_id=current_user.id,
        obj_in={bill_field_name: bill_value - amount}
    )


    await callback.message.delete()
    await callback.message.answer(
        "💸",
        reply_markup=get_reply_keyboard(current_user),
    )
    await callback.message.answer(
        html.bold(f"🏦 Сейф Триумф успешно пополнен на {amount} USDT ✅")
    )
    await send_donations_menu(
        from_user_id=callback.from_user.id,
        telegram_method=bot.send_message
    )

    await state.clear()

