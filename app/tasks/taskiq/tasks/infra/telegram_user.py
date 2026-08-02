import uuid

import loguru

from app.core.config import settings
from app.core.taskiq import broker
from app.tasks.taskiq.dependencies.container import ContainerDependency
from app.db.commit_decorator import commit_and_close_session
from app.repositories import RepositoryTelegramUser


@broker.task(retry_on_error=True)
@commit_and_close_session
async def update_username_task(
        telegram_user_id: str,
        new_username: str,
        *,
        container: ContainerDependency,
):
    try:
        telegram_user_id = uuid.UUID(telegram_user_id)
    except ValueError:
        loguru.logger.error(
            "Telegram user id is invalid. Please provide a valid UUID."
        )
        return

    repository_telegram_user: RepositoryTelegramUser = (
        await container.repository_telegram_user()
    )

    return await repository_telegram_user.update_username(
        telegram_user_id=telegram_user_id,
        new_username=new_username,
    )