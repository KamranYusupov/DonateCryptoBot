import datetime
import random
from functools import wraps

import loguru
from aiogram import Router, F
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, CommandObject, Command
from dependency_injector.wiring import inject, Provide
from sqlalchemy import text
from sqlalchemy.sql import func

from app.core.container import Container
from app.services.matrix_node_service import MatrixNodeService
from app.services.telegram_user_service import TelegramUserService
from app.schemas.telegram_user import TelegramUserEntity, generate_random_user
from app.schemas.matrix import MatrixEntity
from app.keyboards.donate import get_donate_keyboard
from app.core.config import settings
from app.models.telegram_user import status_list, DonateStatus
from app.services.matrix_service import MatrixService
from app.utils.excel import import_users_from_excel
from app.utils.sponsor import get_callback_value
from app.services.donate_service import DonateService
from app.keyboards.reply import get_reply_keyboard
from app.utils.matrix import get_matrices_length
from app.services.donate_confirm_service import DonateConfirmService
from app.keyboards.donate import get_start_inline_keyboard
from app.utils.bot import get_schema_from_user

debug_router = Router()

# Тут функции только для тестов поэтому нет DRY

@debug_router.message(Command("insert_node"))
@inject
async def insert_node(
        message: Message,
        command: CommandObject,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        matrix_node_service: MatrixNodeService = Provide[
            Container.matrix_node_service
        ],
        donate_service: DonateService = Provide[Container.donate_service],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
) -> None:
    if command.args:
        sponsor_user_id = command.args
        sponsor = await telegram_user_service.get_telegram_user(
            user_id=sponsor_user_id
        )
    else:
        sponsor = await telegram_user_service.get_telegram_user(
            is_admin=True
        )

    user = generate_random_user()
    user.status = DonateStatus.BRILLIANT
    user.sponsor_user_id = sponsor.user_id
    user.depth_level = sponsor.depth_level + 1

    fake_user = await telegram_user_service.create_telegram_user(
        user=user,
        sponsor=sponsor
    )

    matrix_node, _= await matrix_node_service.activate_matrix_node(
        current_user_id=fake_user.id,
        sponsor_id=sponsor.id,
        status=DonateStatus.BRILLIANT,
        start_bot_tasks=False,
        donate_sum=20,
    )
    await message.answer(
        "Node inserted:\n\n"
        f"UserID: {fake_user.user_id}\n"
        f"Level: {matrix_node.level}\n"
        f"Position: {matrix_node.position}",
    )

@debug_router.message(Command("clear_db"))
@inject
async def clear_db(
        message,
        session = Provide[Container.session],
):
    query = text(
        "delete from donate_transactions ; "
        "delete from donates; delete from add_to_matrix_tasks; "
        "delete from matrices;delete from withdrawal_requests; "
        "delete from sponsors_contest_points; delete from sponsors_contests; "
        "delete from registration_contest_points;"
        "delete from registration_contests;"
        "delete from telegram_users;"
        "update admin_statistic set system_bill = 0, triumph_system_bill = 0, donates_sum_for_registration = 0;"
    )
    session.execute(query)
    await message.answer("База очищена")

    await import_users_from_excel(
        file_path="telegram_users (5).xlsx",
    )
    loguru.logger.info("fdsdsd")
    return


@debug_router.message(F.text.startswith("fake_"))
@inject
async def add_fake_user(
        message: Message,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        donate_service: DonateService = Provide[Container.donate_service],
        matrix_service: MatrixService = Provide[Container.matrix_service],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
):
    donate_sum = int(message.text.split("_")[-1])
    status = donate_confirm_service.get_donate_status(
        donate_sum=donate_sum,
    )

    current_user = await telegram_user_service.get_telegram_user(
        user_id=message.from_user.id
    )

    user = generate_random_user()
    user.status = status

    user.sponsor_user_id = current_user.user_id
    user.depth_level = current_user.depth_level + 1

    fake_user = await telegram_user_service.create_telegram_user(
        user=user,
        sponsor=current_user
    )
    donations_data = []

    for _ in range(30):
        matrix = await donate_service.handle_matrix_activation(
        (current_user, None, None),
        fake_user,
        donate_sum,
        donations_data,
        status,
    )

    donate = await donate_confirm_service.create_donate(
        telegram_user_id=current_user.id,
        donate_data=donations_data,
        matrix_id=matrix.id,
        quantity=donate_sum,
    )
    fake_user.status = status
    await message.answer(
        f"✅ пользователь {fake_user.username} успешно добавлен в {matrix.id}!\n"
        f"Статус стола: <b>{matrix.status.value}</b>\n"
        f"{settings.bot_link}?start={fake_user.user_id}",
        parse_mode="HTML",
    )


@debug_router.message(Command("create_admin"))
@inject
async def create_fake_admin(
        message: Message,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        matrix_service: MatrixService = Provide[Container.matrix_service],
):
    admin_user = await telegram_user_service.get_telegram_user(is_admin=True)
    if admin_user:
        return
    user = generate_random_user()
    user.status = DonateStatus.SILVER
    user.is_admin = True

    admin_user = await telegram_user_service.create_telegram_user(user=user)

    for status in status_list:
        matrix_dict = {"owner_id": admin_user.id, "status": status}
        await matrix_service.create_matrix(
            matrix=MatrixEntity(
                **matrix_dict,
            )
        )

    await message.answer(
        f"✅ Готово - {settings.bot_link}?start={admin_user.user_id}",
    )


@debug_router.message(F.text.startswith("fakeadmin_"))
@inject
async def add_fake_user(
        message: Message,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        donate_service: DonateService = Provide[Container.donate_service],
        matrix_service: MatrixService = Provide[Container.matrix_service],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
):
    donate_sum = int(message.text.split("_")[-1])
    status = donate_confirm_service.get_donate_status(
        donate_sum=donate_sum,
    )
    admin_user = await telegram_user_service.get_telegram_user(
        is_admin=True,
    )

    user = generate_random_user()
    user.status = status

    user.sponsor_user_id = admin_user.user_id

    fake_user = await telegram_user_service.create_telegram_user(
        user=user
    )
    matrix_dict = {
        "owner_id": fake_user.id,
        "status": status,
    }
    created_matrix = await matrix_service.create_matrix(
        matrix=MatrixEntity(**matrix_dict)
    )

    admin_matrix = await matrix_service.get_matrix(
        owner_id=admin_user.id,
        status=status,
    )
    await matrix_service.add_to_matrix(admin_matrix, created_matrix, fake_user)

    await message.answer(
        f"✅ пользователь {fake_user.username} успешно добавлен в {admin_matrix.id}!\n"
        f"Статус стола: <b>{admin_matrix.status.value}</b>\n"
        f"{settings.bot_link}?start={fake_user.user_id}",
        parse_mode="HTML",
    )
