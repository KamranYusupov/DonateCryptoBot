from datetime import datetime, timedelta

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dependency_injector.wiring import Provide, inject

from app.core.container import Container
from app.keyboards.donate import get_donate_keyboard, get_donations_keyboard
from app.loader import bot
from app.models import Matrix
from app.models.telegram_user import DonateStatus, TelegramUser
from app.services.donate_confirm_service import DonateConfirmService
from app.services.matrix_node_service import MatrixNodeService
from app.services.matrix_service import MatrixService
from app.services.sponsors_contest_service import SponsorsContestService
from app.services.statistic_service import AdminStatisticService
from app.services.telegram_user_service import TelegramUserService
from app.utils.matrix import get_main_matrices
from app.utils.texts import places_emoji_list, get_matrices_statuses_statistic_message, \
    get_matrices_length_statistic_message


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
        admin_statistic_service: AdminStatisticService = Provide[
            Container.admin_statistic_service
        ],
) -> None:
    telegram_method_kwargs = {}
    if telegram_method == bot.send_message:
        telegram_method_kwargs["chat_id"] = from_user_id

    current_user = await telegram_user_service.get_telegram_user(
        user_id=from_user_id
    )
    current_sponsors_contest, _ = \
        await sponsors_contests_service.get_or_create_current_contest()
    current_user_contest_result = current_sponsors_contest.results.get(
        str(current_user.user_id), {}
    )
    current_user_place = current_user_contest_result.get("place", "-")
    if isinstance(current_user_place, int) and 0 < current_user_place <= 10:
        current_user_place = places_emoji_list[current_user_place - 1]

    default_buttons = {}
    message_text = (
        f"Место в конкурсе: <b>{current_user_place}</b>\n"
        f"Лично приглашенных: <b>{current_user.invites_count}</b>\n"
        f"Баланс для активации: "
        f"<b>${current_user.bill_for_activation}</b>\n"
        "Баланс для вывода: "
        f"<b>${current_user.bill_for_withdraw}</b>\n"
        "Всего заработано: "
        f"<b>${current_user.donates_sum}</b>\n"
    )

    if current_user.status != DonateStatus.NOT_ACTIVE:
        default_buttons.update({
            "АКТИВНЫЕ ПЛОЩАДКИ": f"team_1",
            "Транзакции 💳": f"transactions",
        })

    default_buttons.update({"Внутренний перевод 💸": "start_transfer" ,})

    if current_user.is_admin:
        admin_statistic = admin_statistic_service.get_statistic()

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


        message_text = (
            f"Регистраций в KOD💵DENEG: <b>{users_count}</b>\n"
            f"\n{matrix_statuses_statistic_message}"
            f"🆓: {users_count_with_not_active_status}\n\n"
            "Всего подарили: "
            f"<b>${donates_sum}</b>\n"
            "Системный баланс: "
            f"<b>${admin_statistic.system_bill}</b>\n"
            "Системный баланс Триумф: "
            f"<b>${admin_statistic.triumph_system_bill}</b>\n"
            "Число отправленных $ за регистрацию: "
            f"<b>${admin_statistic.donates_sum_for_registration}</b>\n"
            "Общий баланс для активации: "
            f"<b>${bills_for_activation_sum}</b>\n"
            "Общий баланс для вывода: "
            f"<b>${bills_for_withdraw_sum}</b>\n"
            "Общий баланс для вывода +10$: "
            f"<b>${bills_for_withdraw_gte_10_sum}</b>\n"
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

        await telegram_method(
            **telegram_method_kwargs,
            text=message_text,
            reply_markup=get_donate_keyboard(
                buttons=default_buttons,
            ),
        )
        return

    current_user_matrices = await matrix_service.get_user_matrices(
        owner_id=current_user.id,
    )
    current_user_main_matrices = get_main_matrices(current_user_matrices)
    matrices_length_statistic_message = (
            "\n" + get_matrices_length_statistic_message(current_user_main_matrices)
    ) if current_user_main_matrices else "не открыты"

    buttons = {}
    sponsor = await telegram_user_service.get_telegram_user(
        user_id=current_user.sponsor_user_id
    )
    buttons.update(get_donations_keyboard())

    triumph_node = await matrix_node_service.get_node(
        owner_id=current_user.id,
    )
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

    message_parts.append(f"\nМой куратор: {sponsor.full_username}")

    message_text = "\n".join(message_parts) + "\n" + message_text

    inline_buttons = [
        InlineKeyboardButton(
            text=text,
            callback_data=data,
        )
        for text, data in buttons.items()
    ]

    inline_buttons.extend([
        InlineKeyboardButton(
            text="📤 Вывод USDT",
            callback_data="start_buy_tokens_state",
        ),
        InlineKeyboardButton(
            text="📥 Пополнить USDT",
            callback_data="start_buy_tokens_state",
        ),
        InlineKeyboardButton(
            text="Внутренний перевод 💸",
            callback_data="start_buy_tokens_state",
        ),
    ])
    keyboard = InlineKeyboardBuilder()
    keyboard.add(*inline_buttons)
    sizes = ((1, ) * len(buttons)) + (1, 1)

    await telegram_method(
        **telegram_method_kwargs,
        text=message_text,
        reply_markup=keyboard.adjust(*sizes).as_markup(),
    )
