from uuid import UUID

import loguru

from app.core.taskiq import broker
from app.db.commit_decorator import commit_and_close_session
from app.loader import bot
from app.tasks.taskiq.dependencies.container import ContainerDependency
from app.models.matrix import MatrixMarketingType
from app.use_cases.donations import SendDonationsMenuUseCase
from app.schemas.marketing import create_marketing_scope


@broker.task
@commit_and_close_session
async def send_donations_menu_task(
        chat_id: int,
        current_user_id: str,
        marketing_type_name: str,
        status_name: str,
        callback_suffix: str = "donations",
        *,
        container: ContainerDependency,
) -> None:
    try:
        marketing_type = MatrixMarketingType[marketing_type_name]
    except KeyError:
        loguru.logger.warning(
            f'Not valid marketing type name "{marketing_type_name}"'
        )
        return

    try:
        status = marketing_type.status_enum[status_name]
    except KeyError:
        loguru.logger.warning(
            f'Not valid status "{status_name}" '
            f'for marketing type "{marketing_type_name}"'
        )
        return

    send_donations_menu_use_case: SendDonationsMenuUseCase = (
        await container.send_donations_menu_use_case()
    )

    marketing_scope = create_marketing_scope(
        marketing_type=marketing_type,
        status=status,
    )

    current_user_id = UUID(current_user_id)
    await send_donations_menu_use_case.execute(
        marketing_scope=marketing_scope,
        from_user_id=chat_id,
        current_user_id=current_user_id,
        telegram_method=bot.send_message,
        callback_suffix=callback_suffix,
    )
