import os

import loguru
from aiogram import Router, F, html
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, or_f
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from dependency_injector.wiring import inject, Provide

from app.core.container import Container
from app.loader import bot
from app.models import Matrix
from app.services.matrix_node_service import MatrixNodeService
from app.services.telegram_user_service import TelegramUserService
from app.keyboards.donate import get_donate_keyboard
from app.core.config import settings
from app.services.matrix_service import MatrixService
from app.use_cases.file import SendFileFromLoadedFileIDOrSaveUseCase
from app.utils.pagination import Paginator
from app.utils.matrix import get_active_matrices, get_archived_matrices
from app.models.telegram_user import DonateStatus
from app.utils.texts import get_my_team_message, get_matrix_info_message, get_downline_nodes_message
from app.models.telegram_user import TelegramUser
from app.utils.texts import (
    kod_deneg_movie_caption,
    kod_mood_movie_caption,
)
from app.models.matrix import MatrixMarketingType

info_router = Router()


@info_router.message(F.text.lower() == "kod💵deneg")
@inject
async def about_handler(
        message: Message,
) -> None:
    presentation_keyboard = InlineKeyboardBuilder()
    presentation_keyboard.add(
        InlineKeyboardButton(
            text="🎬 Фильм «KOD 💵 DENEG»",
            callback_data="kod_deneg_movie"
        ),
        InlineKeyboardButton(
            text="🎬 Фильм «КОД СОСТОЯНИЯ»",
            callback_data="kod_mood_movie"
        ),
        InlineKeyboardButton(
            text="📎 Инструкция к фильму",
            url="https://t.me/kod_deneg_film/11"
        ),
        InlineKeyboardButton(
            text="🖥 Презентация",
            url=settings.presentation_link,
        ),
        InlineKeyboardButton(
            text="🏆 КОНКУРС КУРАТОРОВ",
            callback_data=settings.sponsors_contest_callback_prefix,
        ),
        InlineKeyboardButton(
            text="🌊 ВОЛНА ИЗОБИЛИЯ",
            callback_data=settings.registration_contest_callback_prefix,
        ),
        InlineKeyboardButton(
            text="📌 Канал",
            url=settings.channel_link
        ),
        InlineKeyboardButton(
            text="💬 Чат ",
            url=settings.chat_link
        ),
    )
    sizes = (1, 1, 1, 1, 1, 1, 2)
    await SendFileFromLoadedFileIDOrSaveUseCase.send_photo(
        bot=bot,
        chat_id=message.from_user.id,
        file_path=settings.about_image_file_path,
        file_id_path=settings.about_image_file_id_path,
        reply_markup=presentation_keyboard.adjust(*sizes).as_markup(),
    )

@info_router.callback_query(F.data == "kod_deneg_movie")
@inject
async def kod_deneg_movie_handler(
        callback: CallbackQuery,
):
    await callback.message.delete()
    await SendFileFromLoadedFileIDOrSaveUseCase.send_video(
        bot=bot,
        chat_id=callback.from_user.id,
        file_path=settings.kod_deneg_movie_file_path,
        file_id_path=settings.kod_deneg_movie_file_id_path,
        caption=kod_deneg_movie_caption,
        protect_content=True,
        supports_streaming=True,
        width=1080,
        height=1920,
    )

@info_router.callback_query(F.data == "kod_mood_movie")
@inject
async def kod_mood_movie_handler(
        callback: CallbackQuery,
):
    await callback.message.delete()
    await SendFileFromLoadedFileIDOrSaveUseCase.send_video(
        bot=bot,
        chat_id=callback.from_user.id,
        file_path=settings.kod_mood_movie_file_path,
        file_id_path=settings.kod_mood_movie_file_id_path,
        caption=kod_mood_movie_caption,
        protect_content=True,
        supports_streaming=True,
        width=1920,
        height=1080,
    )


@info_router.callback_query(F.data.startswith("team_"))
@info_router.callback_query(F.data.startswith("archive_team_"))
@inject
async def team_inline_handler(
        callback: CallbackQuery,
        current_user: TelegramUser,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        matrix_service: MatrixService = Provide[Container.matrix_service],
        matrix_node_service: MatrixNodeService = Provide[
            Container.matrix_node_service
        ],
) -> None:
    callback_data_list = callback.data.split("_")
    is_archive = callback_data_list[0] == "archive"

    matrices = await matrix_service.get_list(
        Matrix.status != DonateStatus.BRILLIANT,
        owner_id=current_user.id,
    )
    archived_matrices = get_archived_matrices(matrices)
    get_my_team_message_kwargs = {}

    if is_archive:
        matrices = archived_matrices
        title_text = "АРХИВ УРОВНЕЙ:"
        page_number, previous_page_number = \
            map(int, callback.data.split("_")[-2:])
        callback_data_prefix = f"archive_team"
        back_button_data = f"team_{previous_page_number}"
    else:
        matrices = get_active_matrices(matrices)
        title_text = "АКТИВНЫЕ ПЛОЩАДКИ:"
        page_number = int(callback.data.split("_")[-1])
        previous_page_number = None
        back_button_data = f"donations"
        callback_data_prefix = f"team"
        matrix_node = await matrix_node_service.get_node(
            owner_id=current_user.id,
            marketing_type=MatrixMarketingType.START,
        )
        if matrix_node:
            downline_nodes = await matrix_node_service.get_downline_nodes(
                matrix_id=matrix_node.matrix_id,
                position=matrix_node.position,
                level=matrix_node.level,
                max_level=settings.start_marketing.triumph_matrix_max_level
            )
            get_my_team_message_kwargs["downline_nodes"] = downline_nodes

        get_my_team_message_kwargs["matrix_node"] = matrix_node


    if current_user.is_admin:
        for matrix in matrices:
            if matrix.status == DonateStatus.BRILLIANT:
                matrices.remove(matrix)


    get_my_team_message_kwargs.update(dict(
        matrices=matrices,
        page_number=page_number,
        previous_page_number=previous_page_number,
        callback_data_prefix=callback_data_prefix,
    ))

    message, page_number, buttons, sizes = await get_my_team_message(
        **get_my_team_message_kwargs,
    )
    message = f"<b>{title_text}</b>\n\n" + message


    if not is_archive and archived_matrices:
        buttons["АРХИВ УРОВНЕЙ 🗄"] = f"archive_team_1_{page_number}"

    if current_user.status is not None and not current_user.is_admin:
        buttons.update({"Транзакции 💳": f"{MatrixMarketingType.START.label}_transactions"})

    buttons["🔙 Назад"] = back_button_data

    await callback.message.edit_text(
        message,
        reply_markup=get_donate_keyboard(buttons=buttons, sizes=sizes),
        parse_mode="HTML",
    )


@inject
async def referral_handler(
        current_user: TelegramUser,
        page_number=1,
        per_page=20,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> tuple[str | None, InlineKeyboardMarkup | None]:
    invited_users = await telegram_user_service.get_invited_users(
        sponsor_user_id=current_user.user_id
    )
    default_buttons = {}

    if not invited_users:
        return "У вас пока нет рефералов.", get_donate_keyboard(buttons=default_buttons)

    paginator = Paginator(
        invited_users,
        page_number=page_number,
        per_page=per_page
    )

    buttons = {}
    message_text = f"<b>Ваши рефералы (страница {page_number}):</b>\n\n"

    if paginator.has_previous():
        buttons |= {"◀ Пред.": f"referrals_{page_number - 1}"}
    if paginator.has_next():
        buttons |= {"След. ▶": f"referrals_{page_number + 1}"}

    if len(buttons) == 2:
        sizes = (2, 1, 1)
    else:
        sizes = (1, 1, 1)

    if current_user.is_admin:
        buttons.update({
            "Отправить рассылку рефералам 📨": f"ref_msg_sponsor_{page_number}",
            "Отправить рассылку всем пользователям 👥📨": f"ref_msg_everyone_{page_number}",
            "Отправить рассылку всем неактивным пользователям 🆓📨": f"ref_msg_free_{page_number}",
            "Отправить рассылку всем платным пользователям 💸📨": f"ref_msg_paid_{page_number}",
        })
    else:
        buttons.update({"Отправить рассылку 📨": f"ref_msg_sponsor_{page_number}"})

    buttons.update(default_buttons)


    start_count = per_page * page_number - per_page + 1
    for order, user in enumerate(paginator.get_page(), start=1):
        user_status_order_emoji = f"{order}️⃣"  if user.status else "🆓"
        message_text += f"{start_count}. @{user.username}: {user_status_order_emoji}\n"
        start_count += 1

    reply_markup = get_donate_keyboard(
        buttons=buttons,
        sizes=sizes
    )

    return message_text, reply_markup


@info_router.message(F.text.lower() == "⚙️ настройки")
@info_router.callback_query(F.data.startswith("referrals_"))
@inject
async def send_referral_message_handler(
        event: Message | CallbackQuery,
        current_user: TelegramUser,
) -> None:
    if not current_user:
        return

    if isinstance(event, Message):
        telegram_method = event.answer
        page_number = 1
    else:
        callback = event
        page_number = int(callback.data.split("_")[-1])
        telegram_method = callback.message.edit_text

    message_text, reply_markup = await referral_handler(
        current_user=current_user,
        page_number=page_number,
    )

    await telegram_method(
        text=message_text,
        reply_markup=reply_markup,
    )



