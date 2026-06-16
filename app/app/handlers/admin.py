import loguru
from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, CommandObject, Command
from dependency_injector.wiring import inject, Provide

from app.core.config import settings
from app.core.container import Container
from app.models.matrix import MatrixEngineType
from app.models.telegram_user import status_list, DonateStatus
from app.services.add_bot_to_matrix_task_service import AddBotToMatrixTaskService
from app.services.donate_confirm_service import DonateConfirmService
from app.services.donate_service import DonateService
from app.services.matrix_node_service import MatrixNodeService
from app.services.telegram_user_service import TelegramUserService

admin_router = Router()


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
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
        add_bot_to_matrix_task_service: AddBotToMatrixTaskService = Provide[
            Container.add_bot_to_matrix_task_service
        ]
):
    sender_user = await telegram_user_service.get_telegram_user(
        user_id=message.from_user.id,
    )
    if not sender_user or not sender_user.is_admin:
        return


    user_id, status_index = command.args.split(" ")
    status_index = int(status_index)

    try:
        status = status_list[status_index - 1]
    except IndexError:
        await message.answer("Некорректный номер статуса")
        return
    try:
        user_id = int(user_id)
        current_user = await telegram_user_service.get_telegram_user(
            user_id=user_id
        )
    except:
        username = user_id[1:] if "@" == user_id[0] else user_id

        current_user = await telegram_user_service.get_telegram_user(
            username=username,
        )

    if not current_user:
        await message.answer("Пользователь не найден")
        return

    donate_sum = DonateStatus.get_status_donate_value(status)
    is_triumph = (status in (DonateStatus.BRILLIANT,))
    create_tasks_data = {
        "donate_sum": donate_sum,
        "create_donates": False,
        "first_task_minutes_delay": 0,
        "second_task_minutes_delay": 0,

    }
    first_sponsor = await telegram_user_service.get_telegram_user(
        user_id=current_user.sponsor_user_id,
    )

    if not is_triumph:
        result = await donate_service.handle_matrix_activation(
            current_user,
            first_sponsor,
            donate_sum,
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
            current_user_id=current_user.id,
            sponsor_id=first_sponsor.id,
            status=status,
        )
        create_tasks_data["obj_id"] = inserted_node.id
        create_tasks_data["engine_type"] = MatrixEngineType.NODES

    if (
        donate_sum >
        DonateStatus.get_status_donate_value(current_user.status)
    ):
        current_user.status = status

    await add_bot_to_matrix_task_service.create_tasks(**create_tasks_data)

    await message.answer("🎉")
    await message.answer(
        "<b>Площадка успешно активирована, бот начал свою работу ✅</b>"
    )





