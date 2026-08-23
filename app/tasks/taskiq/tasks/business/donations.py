from uuid import UUID

from aiogram.filters import callback_data

from app.core.taskiq import broker
from app.db.commit_decorator import commit_and_close_session
from app.loader import bot
from app.tasks.taskiq.dependencies.container import ContainerDependency
from app.models.matrix import MatrixMarketingType
from app.use_cases.donations import SendDonationsMenuUseCase


@broker.task
@commit_and_close_session
async def send_donations_menu_task(
        chat_id: int,
        current_user_id: str,
        marketing_type: MatrixMarketingType,
        callback_suffix: str = "donations",
        *,
        container: ContainerDependency,
) -> None:
    send_donations_menu_use_case: SendDonationsMenuUseCase = container.send_donations_menu_use_case()

    current_user_id = UUID(current_user_id)
    await send_donations_menu_use_case.execute(
        marketing_type=marketing_type,
        from_user_id=chat_id,
        current_user_id=current_user_id,
        telegram_method=bot.send_message,
        callback_suffix=callback_suffix,
    )
