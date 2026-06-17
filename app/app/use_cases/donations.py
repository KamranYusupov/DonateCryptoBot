import html
from datetime import datetime, timedelta

import loguru
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dependency_injector.wiring import Provide, inject

from app.core.container import Container
from app.keyboards.donate import get_donate_keyboard, get_donations_buttons
from app.keyboards.inline import get_inline_buttons_from_dict
from app.loader import bot
from app.models import Matrix
from app.models.telegram_user import DonateStatus, TelegramUser
from app.services.donate_confirm_service import DonateConfirmService
from app.services.matrix_node_service import MatrixNodeService
from app.services.matrix_service import MatrixService
from app.services.sponsors_contest_service import SponsorsContestService
from app.services.statistic_service import StatisticService
from app.services.telegram_user_service import TelegramUserService
from app.utils.matrix import get_main_matrices
from app.utils.texts import (
    places_emoji_list,
    get_matrices_statuses_statistic_message,
    get_matrices_length_statistic_message, format_decimal,
)


@inject
async def send_donations_menu(
        from_user_id: int,
        telegram_method,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        matrix_service: MatrixService = Provide[Container.matrix_service],
        matrix_node_service: MatrixNodeService = Provide[
            Container.matrix_node_service
        ],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
        sponsors_contests_service: SponsorsContestService = Provide[
            Container.sponsors_contests_service
        ],
        statistic_service: StatisticService = Provide[
            Container.statistic_service
        ],
) -> None:
    telegram_method_kwargs = {}
    if telegram_method == bot.send_message:
        telegram_method_kwargs["chat_id"] = from_user_id

    current_user = await telegram_user_service.get_telegram_user(
        user_id=from_user_id
    )
    if not current_user:
        return
    current_sponsors_contest, _ = \
        await sponsors_contests_service.get_or_create_current_contest()
    current_user_contest_result = current_sponsors_contest.results.get(
        str(current_user.user_id), {}
    )
    current_user_place = current_user_contest_result.get("place", "-")
    if isinstance(current_user_place, int) and 0 < current_user_place <= 10:
        current_user_place = places_emoji_list[current_user_place - 1]

    default_buttons = {}
    if current_user.status != DonateStatus.NOT_ACTIVE:
        default_buttons.update({
            "АКТИВНЫЕ ПЛОЩАДКИ": f"team_1",
            "Транзакции 💳": f"transactions",
        })

    created_at_date_str = current_user.created_at.strftime("%d.%m.%Y")

    message_text = (
        f"Место в конкурсе: <b>{current_user_place}</b>\n"
        f"Лично приглашенных: <b>{current_user.invites_count}</b>\n"
        f"Баланс для активации: "
        f"<b>${format_decimal(current_user.bill_for_activation)}</b>\n"
        "Баланс для вывода: "
        f"<b>${format_decimal(current_user.bill_for_withdraw)}</b>\n"
        "Всего заработано: "
        f"<b>${format_decimal(current_user.donates_sum)}</b>\n"
    )

    if current_user.status != DonateStatus.NOT_ACTIVE:
        default_buttons.update({
            "АКТИВНЫЕ ПЛОЩАДКИ": f"team_1",
            "Транзакции 💳": f"transactions",
        })

    if current_user.is_admin:
        default_buttons.pop("Транзакции 💳")

        admin_statistic = statistic_service.get_admin_statistic()

        users_count = await telegram_user_service.get_count(is_bot=False)
        users_count_with_not_active_status = await telegram_user_service.get_count(
            status=DonateStatus.NOT_ACTIVE,
            is_bot=False,
        )
        owners_ids = await telegram_user_service.get_ids(is_bot=False)
        matrices = await matrix_service.get_list(Matrix.owner_id.in_(owners_ids)) # FIXME
        matrix_statuses_statistic_message = get_matrices_statuses_statistic_message(
            matrices,
        )
        donates_sum = await donate_confirm_service.get_donates_sum()

        bills_for_activation_sum = (
            await telegram_user_service.get_bills_for_activation_sum()
        ) - current_user.bill_for_activation
        bills_for_withdraw_sum = (
            await telegram_user_service.get_bills_for_withdraw_sum()
        ) - current_user.bill_for_withdraw

        users_count_with_bill_for_withdraw_gte_10 = (
            await telegram_user_service.get_count(
                TelegramUser.bill_for_withdraw >= 10,
                TelegramUser.is_bot == False,
        )
        )
        bills_for_withdraw_gte_10_sum = (
            await telegram_user_service.get_bills_for_withdraw_sum(
                TelegramUser.bill_for_withdraw >= 10,
                TelegramUser.is_bot == False,
            )
        ) - current_user.bill_for_withdraw
        triumph_bills_sum = await telegram_user_service.get_triumph_bills_sum()


        message_text = (
            f"Регистраций в KOD💵DENEG: <b>{users_count}</b>\n"
            f"\n{matrix_statuses_statistic_message}"
            f"🆓: {users_count_with_not_active_status}\n\n"
            "Всего подарили: "
            f"<b>${format_decimal(donates_sum)}</b>\n"
            "Системный баланс: "
            f"<b>${format_decimal(admin_statistic.system_bill)}</b>\n"
            "Системный баланс Триумф: "
            f"<b>${format_decimal(admin_statistic.triumph_system_bill)}</b>\n"
            "Число отправленных $ за регистрацию: "
            f"<b>${format_decimal(admin_statistic.donates_sum_for_registration)}</b>\n"
            "Общий баланс для активации: "
            f"<b>${format_decimal(bills_for_activation_sum)}</b>\n"
            "Общий баланс для вывода: "
            f"<b>${format_decimal(bills_for_withdraw_sum)}</b>\n"
            "Общий баланс для вывода +10$: "
            f"<b>${format_decimal(bills_for_withdraw_gte_10_sum)}</b>\n"
            "Общий сейф Триумф: "
            f"<b>${format_decimal(triumph_bills_sum)}</b>\n\n"
            "Число пользователей с балансом для вывода +10: "
            f"<b>{users_count_with_bill_for_withdraw_gte_10}</b>\n\n"
        ) + message_text

        buttons = default_buttons
        admin_buttons = {
            "Скачать базу ⬇️": "excel_users",
            "Заявки на вывод 💸": "withdrawal_requests_1",
            "Список забаненных пользователей 📇🅱️": "banned_users_1",
            "Внутренние переводы": "transfer-list_1",
            "Забанить пользователя 🔒": "ban_user",
        }
        buttons.update(admin_buttons)
        inline_buttons = get_inline_buttons_from_dict(buttons)
        inline_buttons.append(
            InlineKeyboardButton(
                text="Внутренний перевод 💸",
                callback_data="start_transfer",
                style="success",
            ),
        )
        keyboard = InlineKeyboardBuilder()
        keyboard.add(*inline_buttons)
        sizes = (1,) * len(inline_buttons)

        await telegram_method(
            **telegram_method_kwargs,
            text=message_text,
            reply_markup=keyboard.adjust(*sizes).as_markup(),
        )
        return

    current_user_matrices = await matrix_service.get_list(
        Matrix.status != DonateStatus.BRILLIANT,
        order_by_create_at=True,
        owner_id=current_user.id,
    )
    current_user_main_matrices = get_main_matrices(current_user_matrices)
    triumph_node = await matrix_node_service.get_node(owner_id=current_user.id)

    if current_user_main_matrices or triumph_node:
        triumph_node_downline_count = (
            triumph_node.downline_count if triumph_node else None
        )
        matrices_length_statistic_message = (
                "\n" +
                get_matrices_length_statistic_message(
                    matrices=current_user_main_matrices,
                    triumph_node_downline_count=triumph_node_downline_count,
                )
        )
    else:
        matrices_length_statistic_message = "не открыты"

    triumph_node = await matrix_node_service.get_node(
        owner_id=current_user.id,
    )

    buttons = {}
    sponsor = await telegram_user_service.get_telegram_user(
        user_id=current_user.sponsor_user_id
    )
    user_statuses = await matrix_service.get_unique_statuses_by_owner_id(
        owner_id=current_user.id,
    )
    if triumph_node:
        user_statuses.append(DonateStatus.BRILLIANT)

    donations_inline_buttons = get_donations_buttons(user_statuses=user_statuses)


    triumph_node_deadline_template = "{0} дней {1}"
    triumph_node_deadline_str = ""

    if triumph_node:
        now = datetime.now(triumph_node.last_activation.tzinfo)
        triumph_node_expires_at = triumph_node.last_activation + timedelta(days=365)
        time_difference = triumph_node_expires_at - now
        triumph_node_expires_in_days = time_difference.days

        triumph_node_deadline_additional_str = ""

        if triumph_node_expires_in_days == 1:
            remaining_seconds = time_difference.seconds
            hours = remaining_seconds // 3600
            minutes = (remaining_seconds % 3600) // 60

            triumph_node_deadline_additional_str = f" {hours} ч. {minutes} мин."
        else:
            triumph_node_expires_in_days += 1


        triumph_node_deadline_str = triumph_node_deadline_template.format(
            triumph_node_expires_in_days,
            triumph_node_deadline_additional_str
        )

    message_parts = [
        f"Активные площадки: {matrices_length_statistic_message}"
    ]

    if triumph_node:
        message_parts.append(f"Срок действия площадки <b>🏆 ТРИУМФ</b>: {triumph_node_deadline_str}")

    message_parts.append(f"Мой куратор: {sponsor.full_username}")
    message_parts.append(f"Дата регистрации: <b>{created_at_date_str}</b>")

    message_text = "\n".join(message_parts) + "\n" + message_text

    inline_buttons = []
    inline_buttons.extend(donations_inline_buttons)

    if default_buttons:
        inline_buttons.extend(get_inline_buttons_from_dict(default_buttons))

    inline_buttons.append(
        InlineKeyboardButton(
            text=f"🏦 Сейф Триумф: {format_decimal(current_user.triumph_bill)} USDT",
            callback_data="increment_trumph_bill",
        )
    )
    sizes = (1, ) * len(inline_buttons)

    inline_buttons.extend([
        InlineKeyboardButton(
            text="📤 Вывести USDT",
            callback_data="withdrawal_request",
            style="primary"

        ),
        InlineKeyboardButton(
            text="Пополнить USDT 📥",
            callback_data="start_buy_tokens_state",
            style="primary"
        ),
        InlineKeyboardButton(
            text="Внутренний перевод 💸",
            callback_data="start_transfer",
            style="success",
        ),
    ])
    keyboard = InlineKeyboardBuilder()
    keyboard.add(*inline_buttons)
    sizes += (2, 1)
    await telegram_method(
        **telegram_method_kwargs,
        text=message_text,
        reply_markup=keyboard.adjust(*sizes).as_markup(),
    )
