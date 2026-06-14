import asyncio
import datetime
import uuid
from decimal import Decimal

import loguru
from dependency_injector.wiring import Provide, inject

from app.models.matrix import Matrix, MatrixEngineType, MatrixNode
from app.services import MatrixActivationNotifierService
from app.services.donate_confirm_service import DonateConfirmService
from app.services.matrix_node_service import MatrixNodeService
from app.services.telegram_user_service import TelegramUserService
from app.core.config import settings
from app.models.matrix import Matrix
from app.services.donate_service import DonateService
from app.services.matrix_service import MatrixService
from app.services.add_bot_to_matrix_task_service import AddBotToMatrixTaskService
from app.db.commit_decorator import commit_and_close_session
from app.core.container import Container
from app.models.matrix import AddBotToMatrixTaskModel
from app.tasks.taskiq.infra.telegram import send_message_task
from app.utils.texts import format_decimal


@inject
@commit_and_close_session
async def add_bot_to_matrix(
        obj_id: uuid.UUID,
        donate_sum: Decimal,
        engine_type: MatrixEngineType = MatrixEngineType.JSON,
        create_donates: bool = True,
        matrix_service: MatrixService = Provide[Container.matrix_service],
        matrix_node_service: MatrixNodeService = Provide[
            Container.matrix_node_service
        ],
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        donate_service: DonateService = Provide[Container.donate_service],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
        matrix_activation_notifier_service: MatrixActivationNotifierService = Provide[
            Container.matrix_activation_notifier_service
        ]
) -> None:
    if engine_type == MatrixEngineType.JSON:
        obj: Matrix = await matrix_service.get_matrix(id=obj_id)
        if not obj or len(obj.matrices) == 2:
            return

    else:
        obj: MatrixNode = await matrix_node_service.get_node(id=obj_id)
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

    transactions_data = []

    if engine_type == MatrixEngineType.JSON:
        result = await donate_service.handle_matrix_activation(
            bot_user,
            owner,
            donate_sum,
            transactions_data,
            obj.status,
            found_matrix=obj,
        )
        if not result:
            return

        matrix, _ = result
        matrix_id = matrix.id
    else:
        inserted_node, upline_nodes = await matrix_node_service.activate_matrix_node(
            current_user_id=bot_user.id,
            sponsor_id=owner.id,
            status=status,
        )
        matrix_transactions_data = await donate_service.update_transactions_data_with_nodes(
            upline_nodes,
            status=status,
            donate_sum=donate_sum,
            transaction_percent=settings.triumph_matrix_transaction_percent,
        )
        transactions_data.extend(matrix_transactions_data)
        matrix_id = inserted_node.matrix_id

    if not create_donates:
        return
    donate = await donate_confirm_service.create_donate(
        telegram_user_id=bot_user.id,
        transactions=transactions_data,
        matrix_id=matrix_id,
        quantity=donate_sum,
    )
    await donate_confirm_service.update_bills_by_donate_id(
        donate_id=donate.id,
        is_bot=True,
    )

    admin_user = await telegram_user_service.get_telegram_user(is_admin=True)
    admin_telegram_id = admin_user.user_id

    coroutines = []
    for transaction in transactions_data:
        coroutines.extend([
            matrix_activation_notifier_service.send_transaction_message(
                transaction
            ),
            send_message_task.kiq(
                text=(
                    f"<b><em>-{format_decimal(transaction.quantity)} "
                    f"от системного баланса.</em></b>\n"
                ),
                chat_id=admin_telegram_id,
            )]
        )

    await asyncio.gather(*coroutines)


@inject
async def execute_bot_matrix_tasks(
    add_bot_to_matrix_task_service: AddBotToMatrixTaskService = Provide[
        Container.add_bot_to_matrix_task_service
    ]
):
    now = datetime.datetime.now()
    tasks = await add_bot_to_matrix_task_service.get_list(
        AddBotToMatrixTaskModel.execute_at <= now,
        is_executed=False,
    )
    tasks_data = [
        {
            "id": task.id,
            "obj_id": task.obj_id,
            "donate_sum": task.donate_sum,
            "engine_type": task.engine_type,
            "create_donates": task.create_donates,
         }
        for task in tasks
    ]
    tasks_ids = []

    for task in tasks_data:
        await add_bot_to_matrix(
            obj_id=task["obj_id"],
            donate_sum=task["donate_sum"],
            engine_type=task["engine_type"],
            create_donates=task["create_donates"],
        )
        tasks_ids.append(task["id"])

    await add_bot_to_matrix_task_service.set_executed(tasks_ids, commit=True)

