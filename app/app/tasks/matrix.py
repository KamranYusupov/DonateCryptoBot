import asyncio
import datetime
import uuid

import loguru
from aiogram.exceptions import TelegramAPIError
from dependency_injector.wiring import Provide, inject

from app.models.matrix import Matrix, MatrixEngineType
from app.models.telegram_user import TelegramUser, statuses_colors_data
from app.services.donate_confirm_service import DonateConfirmService
from app.services.matrix_node_service import MatrixNodeService
from app.services.telegram_user_service import TelegramUserService
from app.keyboards.donate import get_donate_keyboard
from app.loader import bot
from app.models.telegram_user import DonateStatus
from app.core.config import settings
from app.models.matrix import Matrix
from app.schemas.telegram_user import generate_random_user
from app.core.container import Container
from app.services.donate_service import DonateService
from app.services.matrix_service import MatrixService
from app.services.matrix_service import AddBotToMatrixTaskModelService
from app.db.commit_decorator import commit_and_close_session
from app.core.container import Container
from app.models.matrix import AddBotToMatrixTaskModel
from app.models.donate import DonateTransactionType
from app.utils.bot import send_message_or_pass, send_transaction_messages
from app.services.statistic_service import AdminStatisticService


@inject
@commit_and_close_session
async def add_bot_to_matrix(
        obj_id: uuid.UUID,
        donate_sum: int,
        engine_type: MatrixEngineType = MatrixEngineType.JSON,
        matrix_service: MatrixService = Provide[Container.matrix_service],
        matrix_node_service: MatrixNodeService = Provide[
            Container.matrix_node_service
        ],
        telegram_user_service: TelegramUserService = Provide[Container.telegram_user_service],
        donate_service: DonateService = Provide[Container.donate_service],
        donate_confirm_service: DonateConfirmService = Provide[Container.donate_confirm_service],
) -> None:
    if engine_type == MatrixEngineType.JSON:
        obj = await matrix_service.get_matrix(id=obj_id)
        if not obj or len(obj.matrices) == 2:
            return

    else:
        obj = await matrix_node_service.get_node(id=obj_id)
        if not obj or obj.children_count == 2:
            return

    status = donate_confirm_service.get_donate_status(donate_sum)
    if not status:
        return

    owner = await telegram_user_service.get_telegram_user(id=obj.owner_id)
    bot_user = await telegram_user_service.create_bot_user(
        status=status,
        depth_level=owner.depth_level + 1,
        sponsor_user_id=owner.user_id,
    )

    donations_data = []

    if engine_type == MatrixEngineType.JSON:
        matrix = await donate_service.handle_matrix_activation(
            bot_user,
            owner,
            donate_sum,
            donations_data,
            obj.status,
            found_matrix=obj,
        )
        matrix_id = matrix.id
    else:
        inserted_node, upline_nodes = await matrix_node_service.activate_matrix_node(
            current_user_id=bot_user.id,
            sponsor_id=owner.id,
            status=status,
            donate_sum=donate_sum,
            start_bot_tasks=False
        )
        matrix_donations_data = await donate_service.update_donate_data_with_nodes(
            upline_nodes,
            donate_sum=donate_sum,
            transaction_quantity=settings.triumph_matrix_donate_amount,
            is_bot=False,
        )
        donations_data.extend(matrix_donations_data)
        matrix_id = inserted_node.matrix_id

    donate = await donate_confirm_service.create_donate(
        telegram_user_id=bot_user.id,
        donate_data=donations_data,
        matrix_id=matrix_id,
        quantity=donate_sum,
    )
    await donate_confirm_service.update_bills_by_donate_id(
        donate_id=donate.id,
    )
    sender_username = bot_user.username
    admin_user = await telegram_user_service.get_telegram_user(is_admin=True)
    admin_telegram_id = admin_user.user_id
    for data in donations_data:
        quantity = data["quantity"]
        await send_transaction_messages(
            bot=bot,
            chat_id=data["receiver_chat_id"],
            quantity=quantity,
            type_=data["type_"],
            sender_username=sender_username,
            status=status,
            sponsor_depth=data.get("sponsor_depth"),
            matrix_length=data.get("matrix_length"),
        )

        await send_message_or_pass(
            bot=bot,
            text=f"<b><em>-{quantity} от системного баланса.</em></b>\n",
            chat_id=admin_telegram_id,
        )


@inject
async def execute_bot_matrix_tasks(
    add_bot_to_matrix_task_service: AddBotToMatrixTaskModelService = Provide[
        Container.add_bot_to_matrix_task_service
    ]
):
    now = datetime.datetime.now()
    tasks = await add_bot_to_matrix_task_service.get_list(
        AddBotToMatrixTaskModel.execute_at <= now + datetime.timedelta(minutes=1),
        is_executed=False,
    )
    tasks_data = [
        {
            "id": task.id,
            "obj_id": task.obj_id,
            "donate_sum": task.donate_sum,
            "engine_type": task.engine_type,
         }
        for task in tasks
    ]
    tasks_ids = []

    for task in tasks_data:
        await add_bot_to_matrix(
            obj_id=task["obj_id"],
            donate_sum=task["donate_sum"],
            engine_type=task["engine_type"],
        )
        tasks_ids.append(task["id"])

    await add_bot_to_matrix_task_service.set_is_executed(tasks_ids, commit=True)

