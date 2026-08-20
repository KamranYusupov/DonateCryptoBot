from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandObject, Command
from dependency_injector.wiring import inject, Provide

from app.core.config import settings
from app.core.container import Container
from app.models.matrix import MatrixEngineType
from app.models.telegram_user import DonateStatus
from app.services.donate_service import DonateService
from app.services.matrix_node_service import MatrixNodeService
from app.services.telegram_user_service import TelegramUserService
from app.tasks.taskiq.tasks.business.matrix import apply_bot_matrix_tasks
from app.services.admin_impersonation_service import AdminImpersonationService
from app.filters.admin import IsAdminFilter
from app.utils.user import parse_user_identifier

admin_router = Router()
admin_router.message.filter(IsAdminFilter())
admin_router.callback_query.filter(IsAdminFilter())


@admin_router.message(Command("activate"))
@inject
async def activate_matrix_handler(
        message: Message,
        command: CommandObject,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        matrix_node_service: MatrixNodeService = Provide[
            Container.matrix_node_service
        ],
        donate_service: DonateService = Provide[Container.donate_service],
):
    user_str, status_number = command.args.split(" ")
    status_index = int(status_number) - 1

    try:
        status = list(DonateStatus)[status_index]
    except IndexError:
        await message.answer("Некорректный номер статуса")
        return

    user_query_kwargs = {}
    user_id, username = parse_user_identifier(user_str)
    if user_id:
        user_query_kwargs["user_id"] = user_id
    elif username:
        user_query_kwargs["username"] = username
    else:
        return

    input_user = await telegram_user_service.get(**user_query_kwargs)

    if not input_user:
        await message.answer("Пользователь не найден")
        return

    is_triumph = (status in (DonateStatus.BRILLIANT,))
    create_tasks_data = {
        "donate_sum": status.amount,
        "create_donates": False,
        "first_task_minutes_delay": 0,
        "second_task_minutes_delay": 0,

    }
    first_sponsor = await telegram_user_service.get_telegram_user(
        user_id=input_user.sponsor_user_id,
    )

    if not is_triumph:
        result = await donate_service.handle_matrix_activation(
            input_user,
            first_sponsor,
            status.amount,
            transactions_data=[],
            status=status,
        )
        if not result:
            await message.answer(
                "Непредвиденая ошибка. "
                "Пожалуйста, обратитесь в службу поддержки "
                f"@{settings.support_username}"
            )
            return

        matrix, created_matrix = result
        create_tasks_data["obj_id"] = created_matrix.id
        create_tasks_data["engine_type"] = MatrixEngineType.JSON

    else:
        inserted_node, upline_nodes = await matrix_node_service.activate_matrix_node(
            current_user_id=input_user.id,
            sponsor_id=first_sponsor.id,
            status=status,
            max_upline_depth=settings.triumph_matrix_max_level,
        )
        create_tasks_data["obj_id"] = inserted_node.id
        create_tasks_data["engine_type"] = MatrixEngineType.NODES

    if status.amount > input_user.status.amount:
        input_user.status = status

    await apply_bot_matrix_tasks(**create_tasks_data)

    await message.answer("🎉")
    await message.answer(
        "<b>Площадка успешно активирована, бот начал свою работу ✅</b>"
    )


@admin_router.message(Command("start_user_session"))
@inject
async def start_user_session_handler(
        message: Message,
        command: CommandObject,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        impersonation_service: AdminImpersonationService = Provide[
            Container.impersonation_service
        ]
):
    if not command.args:
        await message.answer("Введите username или id пользователя")
        return

    user_query_kwargs = {}
    user_id, username = parse_user_identifier(command.args)
    if user_id:
        user_query_kwargs["user_id"] = user_id
    elif username:
        user_query_kwargs["username"] = username
    else:
        return

    input_user = await telegram_user_service.get(**user_query_kwargs)

    if not input_user:
        await message.answer("Пользователь не найден.")
        return

    await impersonation_service.start_impersonation(input_user.user_id)
    await message.answer("Сессия начата.")


@admin_router.message(Command("end_user_session"))
@inject
async def end_user_session_handler(
        message: Message,
        impersonation_service: AdminImpersonationService = Provide[
            Container.impersonation_service
        ]
):
    await impersonation_service.end_impersonation()
    await message.answer("Сессия закончена.")








