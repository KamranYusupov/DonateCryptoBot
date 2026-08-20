import copy
from datetime import date, timedelta, datetime
from decimal import Decimal
from typing import Any, List, Sequence
import uuid

import loguru
from aiogram import html

from app.models.telegram_user import (
    DonateStatus,
)
from app.models.telegram_user import TelegramUser
from app.schemas.triumph_bill_transaction import TriumphBillTransactionMessageSchema
from app.utils.matrix import (
    find_free_place_in_matrix,
    get_matrix_levels,
    get_sorted_matrices,
    insert_into_matrices,
)
from app.utils.pagination import Paginator
from app.core.config import settings
from app.models.matrix import Matrix, MatrixNode
from app.models.withdrawal_request import WithdrawalRequest
from app.utils.datetime import to_main_tz
from app.models.telegram_user import GlobalMarketingDonateStatus


def get_donate_confirm_message(
        donate_sum: int,
        donate_status: DonateStatus,
) -> str | None:
    if donate_status not in list(statuses_colors_data.keys()):
        return
    status = (
        f"{statuses_colors_data.get(donate_status)} - {donate_status.value.split()[0]}"
    )

    message_text = (
        f"💌 Участник получил 🎁 ${donate_sum}\n\n"
        f"🛗 Уровень: {status}\n\n"
        "🤝 Будем «НА СВЯЗИ»"
    )

    return message_text


def get_user_statuses_statistic_message(
        users: list[TelegramUser],
) -> str: #FIXME: do marketing type split
    status_emoji_data = {
        status_list[i]: status_emoji_list[i]
        for i in range(len(status_list))
    }
    statuses_data = {"🆓": 0}
    statuses_data.update({status: 0 for status in status_emoji_list})

    for user in users:
        if user.status is None:
            statuses_data["🆓"] += 1
            continue

        statuses_data[status_emoji_data[user.status]] += 1

    message = ""

    for status, count in list(statuses_data.items())[::-1]:
        message += f"{status}: {count}\n"

    return message


def get_matrices_statuses_statistic_message(
        matrices: list[Matrix],
) -> str: #FIXME: do marketing type split
    message = ""
    status_emoji_data = {
        status_list[i]: status_emoji_list[i]
        for i in range(len(status_list))
    }
    statuses_data = {status: 0 for status in status_emoji_list}

    for matrix in matrices:
        if matrix.status is None:
            continue

        statuses_data[status_emoji_data[matrix.status]] += 1

    for status, count in list(statuses_data.items())[::-1]:
        message += f"{status}: {count}\n"

    return message

def get_matrices_length_statistic_message(
        matrices: list[Matrix],
        status_list: Sequence[DonateStatus | GlobalMarketingDonateStatus],
        triumph_node_downline_count: int | None = None,
) -> str: # FIXME: Split by marketing type
    message = ""
    return message
    sorted_matrices = get_sorted_matrices(matrices, status_list)


    if triumph_node_downline_count is not None:
        brilliant_status = DonateStatus.BRILLIANT
        emoji = get(brilliant_status)

        message += (
            f"<b>{emoji} {brilliant_status.value.upper()}</b>: "
            f"{triumph_node_downline_count}/{settings.triumph_matrix_max_length}\n"
        )

    for matrix in sorted_matrices[::-1]:
        if matrix.status in (None, DonateStatus.BRILLIANT):
            continue

        emoji = statuses_colors_data.get(matrix.status)
        message += (
            f"<b>{emoji} {matrix.status.value.upper()}</b>: "
            f"{len(matrix.telegram_users)}/{settings.matrix_max_length}\n"
        )

    return message

def get_user_info_message(user: TelegramUser) -> str:
    created_at_str = to_main_tz(user.created_at).strftime("%d.%m.%Y %H:%M")
    message = (
        f"ID: {html.bold(user.id)}\n\n"
        f"Telegram ID: {html.bold(user.user_id)}\n"
        f"Username: @{user.username}\n"
        f"Полное имя: {html.bold(user.full_name)}\n"
        f"Дата и время регистрации: "
        + html.bold(created_at_str)
    )
    return message


def get_withdrawal_request_info_message(
        withdrawal_request: WithdrawalRequest,
        withdrawal_request_user: TelegramUser,
) -> str:
    created_at_str = \
        to_main_tz(withdrawal_request.created_at).strftime("%d.%m.%Y %H:%M")

    message = (
        f"ID: {html.bold(withdrawal_request.id)}\n\n"
        f"Адрес кошелька: {html.code(withdrawal_request.wallet_address)}\n"
        f"Сеть: {html.bold(withdrawal_request.network.value)}\n"
        f"Сумма: ${html.code(withdrawal_request.tokens_count)}\n"
        f"Пользователь: "
        f"@{html.bold(withdrawal_request_user.username)} "
        f"({withdrawal_request_user.user_id})\n"
        f"Подтвержден: " + html.bold("да" if withdrawal_request.is_paid else "нет") + "\n"
        f"Дата и время создания: "
        + html.bold(created_at_str)
    )
    return message


def get_triumph_bill_transaction_message(
        transaction: TriumphBillTransactionMessageSchema,
) -> str:
    created_at_str = to_main_tz(transaction.created_at).strftime("%d.%m.%Y %H:%M")

    return (
        f"ID: {html.bold(transaction.id)}\n\n"
        f"Пользователь: @{html.bold(transaction.telegram_user_username)}\n"
        f"Сумма: ${html.bold(format_decimal(transaction.amount, round_digits=2))}\n"
        f"Дата и время создания: {html.bold(created_at_str)}"
    )

async def get_my_team_message(
        matrices: list[Matrix],
        status_list: list[DonateStatus | GlobalMarketingDonateStatus],
        page_number: int,
        per_page: int = 1,
        callback_data_prefix: str = "team",
        previous_page_number: int | None = None,
        matrix_node: MatrixNode | None = None,
        downline_nodes: list[MatrixNode] | None = None,
):
    downline_nodes = [] if not downline_nodes else downline_nodes
    message = ""
    if matrices:
        sorted_matrices = get_sorted_matrices(matrices, status_list)
    else:
        sorted_matrices = []

    if matrix_node:
        sorted_matrices.append(matrix_node)

    paginator = Paginator(
        sorted_matrices,
        page_number=page_number,
        per_page=per_page
    )
    buttons = {}
    sizes = (1, 1)

    if paginator.get_page():
        matrix = paginator.get_page()[0]
        if isinstance(matrix, Matrix):
            message += get_matrix_info_message(matrix)
        elif isinstance(matrix, MatrixNode):
            matrix_node = matrix
            message += get_downline_nodes_message(
                matrix_node,
                status=DonateStatus.BRILLIANT,
                downline_nodes=downline_nodes,
                matrix_max_length=settings.triumph_matrix_max_length,
            )
    else:
        message += "У вас нет активированных уровней"

    pagination_button_data = (
            f"{callback_data_prefix}_"
            + "{page_number}"
            + (f"_{previous_page_number}" if previous_page_number else "")
    )

    if paginator.has_previous():
        buttons |= {"◀ Пред.": pagination_button_data.format(page_number=page_number - 1)}
    if paginator.has_next():
        buttons |= {"След. ▶": pagination_button_data.format(page_number=page_number + 1)}

    if len(buttons) == 2:
        sizes = (2, 1)

    return message, page_number, buttons, sizes


def get_downline_nodes_message(
        matrix_node: MatrixNode,
        status: DonateStatus,
        downline_nodes: List[MatrixNode],
        matrix_max_length: int,
        matrix_max_level: int = 4
):
    """
    Выводит бинарное дерево матрицы по нижестоящим nodes.
    """

    color = statuses_colors_data.get(status)
    lines = [f"<b>{color} {status.value}: {matrix_node.id.hex[0:5]}</b>"]

    if not downline_nodes:
        lines.append(f"\nМест занято: <b>{0} из {matrix_max_length}\n</b>")

        return "\n".join(lines)

    levels_data = {
        i: ["Свободно"] * (2 ** i)
        for i in range(1, matrix_max_level + 1)
    }

    for node in downline_nodes:
        rel_level = node.level - matrix_node.level

        # Вычисляем глобальную позицию самого левого узла на этом уровне
        level_start_position = matrix_node.position * (2 ** rel_level)

        # Вычисляем индекс узла в нашем массиве (от 0 до 2^rel_level - 1)
        index_on_level = node.position - level_start_position
        levels_data[rel_level][index_on_level] = "Занято"

    for level_number in range(1, matrix_max_level + 1):
        lines.append(f"\n<b>{level_number}️⃣ Уровень:</b>")

        for idx, status in enumerate(levels_data[level_number], start=1):
            lines.append(f"{idx}) {status}")

        lines.append("")

    lines.append(
        f"\nМест занято: <b>{matrix_node.downline_count} из {matrix_max_length}\n</b>"
    )

    return "\n".join(lines)

def get_matrix_info_message(
        matrix: Matrix,
        order_map: dict[str, int] | None = None,
        level_length: int = settings.level_length,
):
    """
    Выводит бинарное дерево матрицы.
    """
    color = statuses_colors_data.get(matrix.status)
    lines = [f"<b>{color} {matrix.status.value}: {matrix.id.hex[0:5]}</b>"]
    if not matrix.matrices:
        lines.append(f"\nМест занято: <b>{len(matrix.telegram_users)} из {settings.matrix_max_length}\n</b>")

        return "\n".join(lines)
    counter = 1

    matrices = copy.deepcopy(matrix.matrices)

    matrix_len = len(matrix.telegram_users)
    while matrix_len != settings.matrix_max_length:
        free_place_path = find_free_place_in_matrix(
            matrices,
            order_map=order_map,
            level_length=level_length)
        free_place_level = len(free_place_path) + 1

        insert_into_matrices(
            matrices, 
            free_place_path,
            free_place_level,
            f"none_{uuid.uuid4()}"
        )
        matrix_len += 1

    levels_data = get_matrix_levels(matrices)
    for level_number in sorted(levels_data.keys()):
        if level_number > settings.matrix_max_level:
            break
        level = levels_data[level_number]

        lines.append(f"\n<b>{level_number}️⃣ Уровень:</b>")
        for obj in level:
            value = "Свободно" if obj is None else "Занято"
            lines.append(f"{counter}) {value}")
            counter += 1

    lines.append(f"\nМест занято: <b>{len(matrix.telegram_users)} из {settings.matrix_max_length}\n</b>")

    return "\n".join(lines)


def get_period_message(
        start_at: datetime,
        period_days: int,
        show_time: bool = False,
) -> str:
    start_at = to_main_tz(start_at)
    end_date = start_at + timedelta(days=period_days)
    parse_format = "%d.%m.%Y" + (" %H:%M" if show_time else "")

    start_str = start_at.strftime(parse_format)
    end_str = end_date.strftime(parse_format)

    return f"{start_str} - {end_str}"


def get_contest_top_10_rating_message(
        top_10_rating: list[tuple[str, int]],
        start_at: datetime,
        prize_fund: int,
        title: str = "🏆 Топ‑10",
        period_days: int = 7,
        show_time: bool = False,
) -> str:
    lines = []
    if not top_10_rating:
        lines.append("В конкурсе пока нет результатов.")
    else:
        lines.append(f"<b>{title}</b>\n")

    for place, (full_name, points) in enumerate(top_10_rating):
        try:
            place_emoji = places_emoji_list[place]
        except IndexError:
            break

        lines.append(f"{place_emoji} {full_name} — {points}")

        if place == 2:
            lines.append("")

    period_str = get_period_message(
        start_at,
        period_days=period_days,
        show_time=show_time,
    )

    lines.append(f"\n🗓 Период: <b>{period_str}</b>")
    lines.append(f"💰 Призовой фонд: <b>${format_decimal(prize_fund, round_digits=0)}</b>")

    return "\n".join(lines)

places_emoji_list = (
    "🥇",
    "🥈",
    "🥉",
    "4⃣",
    "5⃣",
    "6⃣",
    "7⃣",
    "8⃣",
    "9⃣",
    "🔟",
)


sponsor_activation_text_template = html.bold(
"🏆 КУРАТОР СДЕЛАЛ АКТИВАЦИЮ\n\n"
"👤 @{username}\n"
"{status}\n\n"
"📊 Выше площадка — больше бонусов."
)


def get_sponsor_activation_text(
        username: str,
        status: DonateStatus,
) -> str:
    status_color_emoji = statuses_colors_data.get(status)
    status_str = f"{status_color_emoji} {status.label.upper()}"

    return sponsor_activation_text_template.format(
        username=username,
        status=status_str,
    )


def format_decimal(decimal: Decimal, round_digits: int = 2) -> str:
    s = f"{round(decimal, round_digits):f}"

    if '.' in s:
        s = s.rstrip('0').rstrip('.')

    return s

def get_sponsor_transaction_message_text(
        *,
        sender_str: str,
        status: DonateStatus,
        sponsor_depth: int,
        quantity: Decimal,
        is_public: bool = False,
) -> str:
    display_name = "ПАРТНЁР" if is_public else sender_str
    template = (
        "<b>👥 {sender_str} АКТИВИРОВАЛ \n"
        "<b>{status_color} {status_name}</b>\n"
        "🎁 Бонус от {sponsor_depth} линии: +{quantity_str}$\n</b>"
        "🤝 Команда растёт\n\n"
        "🔥 На Шаг ближе к Триумфу!"
    )
    status_color = statuses_colors_data.get(status)
    status_name = status.value.upper()

    return template.format(
        sender_str=display_name,
        status_color=status_color,
        status_name=status_name,
        sponsor_depth=sponsor_depth,
        quantity_str=format_decimal(quantity),
    )

def get_system_transaction_message_text(
        *,
        quantity: Decimal,
) -> str:
    template = "Системный аккаунт <b>${quantity_str}</b>"

    return template.format(
        quantity_str=format_decimal(quantity),
    )

def get_matrix_transaction_message_text(
        *,
        receiver_str: str,
        receiver_donates_sum: Decimal,
        status: DonateStatus,
        quantity: Decimal,
        matrix_length: int,
        matrix_max_length: int,
        triumph: bool = False,
        is_public: bool = False,
):
    template = (
        "<b>🤖 БОТ ЗАКРЫЛ МЕСТО {receiver_str}</b>\n"
        "💸 <b>+{quantity_str}$</b> на счёт\n"
        "🎯 Площадка: <b>{status_str}</b> \n"
        "{statistic_line}\n\n"
        "<b>🎁 Всего получено: ${receiver_donates_sum}</b>\n\n"
        "🔥 Делитесь <b>KOD💵DENEG</b> — получайте бонусы."
    )

    receiver_str = "" if is_public else receiver_str
    status_color = statuses_colors_data.get(status, "")
    status_name = status.value.upper()
    status_str = f"{status_color} {status_name}"

    if triumph:
        current_sum_str = format_decimal(quantity * matrix_length)
        statistic_line = (
            f"🏦 Получено: <b>${current_sum_str} "
            f"из ${settings.triumph_max_donates_sum_from_matrix}</b>"
        )
    else:
        statistic_line = f"📦 <b>{matrix_length} из {matrix_max_length}</b> мест занято"

    return template.format(
        receiver_str=receiver_str,
        receiver_donates_sum=format_decimal(receiver_donates_sum),
        status_str=status_str,
        statistic_line=statistic_line,
        quantity_str=format_decimal(quantity),
    )


increase_triumph_bills_message_text = html.bold(
    f"🏦 СЕЙФ «ТРИУМФ» +{settings.start_marketing.triumph_bill_increase_percent}%\n\n"
    "⚡️ Активации площадок = рост сейфа\n\n"
    "🌀 Состояние → Действие → Результат\n\n"
)

registration_donate_text = (
    "<b>🎁 ПРОМО: БОНУС ЗА КАЖДОГО</b>\n\n"
    f"💸 <b>+{settings.donate_for_registration}$</b> уже на счёте\n\n"
    "<b>🔥 Больше первых линий = больше бонусов</b>"
)

registration_donate_triumph_bill_text = html.bold(
    "🎁 +{0}$ В СЕЙФ ЗА РЕГИСТРАЦИЮ {1}\n\n"
    "👥 Новый участник — Сейф пополнен.\n"
    "💰 Приглашайте — копите на Триумф.\n\n"
    "🌀 Состояние → Действие → Результат"
)

kod_deneg_movie_caption = html.bold(
    "🎬 ФИЛЬМ «KOD💵DENEG»\n\n"
    "🧘 Никаких сложных техник\n"
    "💰 Пишешь свою сумму на бумаге\n"
    "🎧 Просто смотришь фильм 30 минут\n\n"
    "🌀 Результат: мозг переключается из дефицита в изобилие. "
    "Ты начинаешь замечать деньги и возможности там, "
    "где раньше видел стены. А если у тебя уже всё "
    "хорошо — станет ещё лучше‼️\n\n"
    "🚫 Без магии,\n"
    "🧠 С нейронаукой."
)

kod_mood_movie_caption = html.bold(
    "🎬 ФИЛЬМ «КОД СОСТОЯНИЯ»\n\n"
    "📝 Пишешь слово — состояние, которое актуально прямо сейчас\n\n"
    "♥️ любовь → чтобы чувствовать\n"
    "💪 сила → чтобы действовать\n"
    "🔥 уверенность → чтобы решать\n"
    "🏥 здоровье → чтобы исцелить\n"
    "😌 спокойствие → чтобы отпустить\n"
    "💰 деньги → чтобы принимать\n"
    "🎯 ясность → чтобы видеть\n\n"
    "🎧 Смотришь фильм — мозг настраивается\n\n"
    "🌀 Результат: ты в нужном состоянии."
)

private_channel_invite_message = (
    "🎉 Поздравляем с активацией площадки!\n\n"
    "Вы достигли уровня, который открывает новые возможности.\n\n"
    "🔥 Приглашаем вас в VIP-клуб KOD💵DENEG — эксклюзивное сообщество для работы с состоянием.\n\n"

    "Вас ждут:\n\n"

    "✅ 7 треков под 7 состояний\n"
    "✅ Закрытые эфиры с основателями\n"
    "✅ Эксклюзивные стратегии и поддержка\n"
    "✅ Окружение лидеров\n\n"
    "⬇️ Присоединяйтесь сейчас: {0}\n\n"
    "🌀 Состояние → Действие → Результат"
)

triumph_bill_increase_statistic_text = (
    "📈 До увеличения сейфа <b>{matrix_activation_step_str}</b> активаций "
    "и <b>{registration_step_str}</b> регистраций."
)

def get_triumph_bill_increase_statistic_text(
        matrix_activation_count: int,
        registration_count: int,
        increase_activation_interval: int = \
            settings.start_marketing.triumph_bills_increase_activation_interval,
        increase_registration_interval: int = \
                settings.start_marketing.triumph_bills_increase_registration_interval,
) -> str:
    registration_step = (
        registration_count
        % settings.triumph_bills_increase_registration_interval
    )
    matrix_activation_step = (
        matrix_activation_count
        % settings.triumph_bills_increase_activation_interval
    )
    registration_step_str = (
        f"{registration_step}/"
        f"{increase_registration_interval}"
    )
    matrix_activation_step_str = (
        f"{matrix_activation_step}/"
        f"{increase_activation_interval}"
    )

    return triumph_bill_increase_statistic_text.format(
        matrix_activation_step_str=matrix_activation_step_str,
        registration_step_str=registration_step_str,
    )
