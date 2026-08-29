import asyncio
from datetime import datetime, timedelta
import uuid
from decimal import Decimal
import random
import logging

from app.core.config import settings
from app.core.taskiq import broker, redis_source
from app.models.matrix import Matrix, MatrixEngineType, MatrixNode, MatrixMarketingType
from app.db.commit_decorator import commit_and_close_session, set_scope_session
from app.repositories import RepositoryTelegramUser
from app.services import TelegramBotService
from app.tasks.taskiq.dependencies.container import ContainerDependency
from app.utils.texts import format_decimal, get_matrix_transaction_message_text

logger = logging.getLogger(__name__)


@broker.task(name="Add bot to Matrix")
@commit_and_close_session
async def add_bot_to_matrix_task(
        obj_id: str,
        donate_sum_str: str,
        engine_type_str: str = MatrixEngineType.JSON.value,
        create_donates: bool = True,
        *,
        container: ContainerDependency,
) -> None:
    matrix_service = await container.matrix_service()
    matrix_node_service = await container.matrix_node_service()
    telegram_user_service = await container.telegram_user_service()
    donate_service = await container.donate_service()
    donate_confirm_service = await container.donate_confirm_service()
    matrix_activation_notifier_service = await container.matrix_activation_notifier_service()
    telegram_bot_service = container.telegram_bot_service()

    donate_sum = Decimal(donate_sum_str)
    engine_type = MatrixEngineType(engine_type_str)

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
            current_user=bot_user,
            sponsor=owner,
            transactions_data=transactions_data,
            status=obj.status,
            found_matrix=obj,
            matrix_max_length=settings.start_marketing.matrix_max_length
        )
        if not result:
            return

        matrix, _ = result
        matrix_id = matrix.id
    else:
        inserted_node, upline_nodes = await matrix_node_service.activate_matrix_node(
            current_user_id=bot_user.id,
            sponsor_id=owner.id,
            matrix_status=status,
            marketing_type=MatrixMarketingType.START,
            max_upline_depth=settings.triumph_matrix_max_level,
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
            telegram_bot_service.send_message(
                text=(
                    f"<b><em>-{format_decimal(transaction.quantity)} "
                    f"от системного баланса.</em></b>\n"
                ),
                chat_id=admin_telegram_id,
            )
        ])

    await asyncio.gather(*coroutines)


async def apply_bot_matrix_tasks(
        obj_id: uuid.UUID,
        donate_sum: int,
        engine_type: MatrixEngineType,
        create_donates: bool = True,
        first_task_minutes_delay: int | None = None,
        second_task_minutes_delay: int | None = None,
):
    now = datetime.now()

    task_data = {
        "obj_id": str(obj_id),
        "donate_sum_str": str(donate_sum),
        "engine_type_str": engine_type.value,
        "create_donates": create_donates
    }

    if first_task_minutes_delay is None:
        first_task_minutes_delay = random.randint(
            settings.add_bot_to_matrix_first_task_interval.min_minutes,
            settings.add_bot_to_matrix_first_task_interval.max_minutes
        )

    if second_task_minutes_delay is None:
        second_task_minutes_delay = random.randint(
            settings.add_bot_to_matrix_second_task_interval.min_minutes,
            settings.add_bot_to_matrix_second_task_interval.max_minutes
        )

    first_task_execute_at = now + timedelta(minutes=first_task_minutes_delay)
    second_task_execute_at = now + timedelta(minutes=second_task_minutes_delay)

    await (
        add_bot_to_matrix_task
        .schedule_by_time(
            redis_source,
            first_task_execute_at,
            **task_data,
        )
    )
    await (
        add_bot_to_matrix_task
        .schedule_by_time(
            redis_source,
            second_task_execute_at,
            **task_data,
        )
    )


@broker.task(retry_on_error=True)
@set_scope_session
async def send_matrix_transaction_message_task(
        receiver_id: str,
        chat_id: int,
        receiver_str: str,
        status_label: str,
        status_emoji: str,
        matrix_length: int,
        matrix_max_length: int,
        triumph: bool,
        quantity: Decimal,
        display_receiver: bool = False,
        *,
        container: ContainerDependency,
) -> None:
    try:
        receiver_id = uuid.UUID(receiver_id)
    except ValueError:
        logger.error("Invalid receiver_id. Task accepts only UUID!")
        return

    repository_telegram_user: RepositoryTelegramUser = \
        await container.repository_telegram_user()

    donates_sum = await repository_telegram_user.get_donates_sum_with_for_update_by_id(
        receiver_id
    )

    if donates_sum is None:
        logger.error(f"donates_sum not found for TelegramUser.id: {receiver_id}")
        return

    telegram_bot_service: TelegramBotService = \
        container.telegram_bot_service()

    message_text = get_matrix_transaction_message_text(
        receiver_str=receiver_str,
        status_label=status_label,
        status_emoji=status_emoji,
        matrix_length=matrix_length,
        matrix_max_length=matrix_max_length,
        triumph=triumph,
        quantity=quantity,
        receiver_donates_sum=donates_sum,
        display_receiver=display_receiver,
    )

    await telegram_bot_service.send_message(
        chat_id=chat_id,
        text=message_text,
    )

