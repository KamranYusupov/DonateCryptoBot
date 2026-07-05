from uuid import UUID

import math
from aiogram import F, Router, html
from aiogram.types import CallbackQuery
from dependency_injector.wiring import Provide, inject

from app.core.container import Container
from app.keyboards.donate import get_donate_keyboard
from app.schemas.triumph_bill_transaction import TriumphBillTransactionMessageSchema
from app.services import TelegramUserService
from app.services.triumph_bill_transaction_service import TriumphBillTransactionService
from app.utils.datetime import to_main_tz
from app.utils.pagination import Paginator, get_pagination_buttons, OuterPaginator
from app.utils.texts import get_triumph_bill_transaction_message, format_decimal
from app.filters.admin import IsAdminFilter

triumph_bill_transaction_router = Router()
triumph_bill_transactions_list_per_page = 5

@triumph_bill_transaction_router.callback_query(
    F.data.startswith("triumph_bill_transactions_"),
    IsAdminFilter(),
)
@inject
async def triumph_bill_transactions_list_handler(
        callback: CallbackQuery,
        triumph_bill_transaction_service: TriumphBillTransactionService = Provide[
            Container.triumph_bill_transaction_service
        ],
):
    callback_data = callback.data.split("_")
    page_number = int(callback_data[-1])
    base_callback_data = "_".join(callback_data[:-1])
    per_page = triumph_bill_transactions_list_per_page

    default_buttons = {"🔙 Назад": "transactions"}
    buttons = {}
    sizes = tuple()
    offset = (page_number * per_page) - per_page

    total_transactions_count = await triumph_bill_transaction_service.get_count()
    transactions = await triumph_bill_transaction_service.get_ordered_transactions(
        limit=per_page,
        offset=offset,
    )

    paginator = OuterPaginator(
        objects_count=total_transactions_count,
        per_page=per_page,
        page_number=page_number,
    )

    if not transactions:
        buttons.update(default_buttons)
        sizes += (1,) * len(default_buttons)
        await callback.message.edit_text(
            "Список транзакций пуст.",
            reply_markup=get_donate_keyboard(buttons=buttons, sizes=sizes),
        )
        return

    for count, transaction in enumerate(transactions, start=1):
        detail_page_number = count + offset
        amount_str = format_decimal(transaction.amount, round_digits=2)
        created_at_str = to_main_tz(transaction.created_at).strftime("%d.%m.%Y %H:%M")
        buttons[f"${amount_str} - {created_at_str}"] = (
            f"t_bill_tran_{detail_page_number}"
        )

    sizes += (1,) * len(transactions)

    pagination_buttons = get_pagination_buttons(
        paginator,
        base_callback_data,
    )
    buttons.update(pagination_buttons)
    if pagination_buttons:
        sizes += (len(pagination_buttons),)

    buttons.update(default_buttons)
    sizes += (1,) * len(default_buttons)

    await callback.message.edit_text(
        html.bold("Транзакции сейфа Триумф:"),
        reply_markup=get_donate_keyboard(buttons=buttons, sizes=sizes),
    )


@triumph_bill_transaction_router.callback_query(
    F.data.startswith("t_bill_tran_")
)
@inject
async def triumph_bill_transaction_detail_handler(
        callback: CallbackQuery,
        triumph_bill_transaction_service: TriumphBillTransactionService = Provide[
            Container.triumph_bill_transaction_service
        ],
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
):
    callback_data = callback.data.split("_")
    base_callback_data = "_".join(callback_data[:-1])
    page_number = int(callback_data[-1])
    per_page = 1
    list_page_number = math.ceil(page_number / triumph_bill_transactions_list_per_page)

    if page_number == 1:
        limit = per_page * 2
        offset = 0
        page_transaction_index = 0
    else:
        limit = per_page * 3
        offset = (page_number * per_page) - per_page - 1
        page_transaction_index = 1

    total_transactions_count = await triumph_bill_transaction_service.get_count()
    transactions = await triumph_bill_transaction_service.get_ordered_transactions(
        limit=limit,
        offset=offset,
    )

    paginator = OuterPaginator(
        objects_count=total_transactions_count,
        per_page=per_page,
        page_number=page_number,
    )

    try:
        page_transaction = transactions[page_transaction_index]
    except IndexError:
        await callback.message.edit_text(
            "Транзакция не найдена.",
            reply_markup=get_donate_keyboard(
                buttons={"🔙 Назад": f"triumph_bill_transactions_{list_page_number}"},
            ),
        )
        return

    buttons = {}
    sizes = tuple()

    pagination_buttons = get_pagination_buttons(
        paginator,
        base_callback_data,
    )
    if pagination_buttons:
        sizes += (len(pagination_buttons),)

    buttons.update(pagination_buttons)
    buttons.update({"🔙 Назад": f"triumph_bill_transactions_{list_page_number}"})

    sizes += (1,) * (len(buttons) - len(pagination_buttons))

    transaction_user_username = await telegram_user_service.get_username_by_id(
        telegram_user_id=page_transaction.telegram_user_id,
    )
    transaction_message_schema = (
        TriumphBillTransactionMessageSchema
        .model_validate(page_transaction)
    )
    transaction_message_schema.telegram_user_username = transaction_user_username

    await callback.message.edit_text(
        get_triumph_bill_transaction_message(transaction_message_schema),
        reply_markup=get_donate_keyboard(
            buttons=buttons,
            sizes=sizes,
        ),
    )
