import uuid

from app.models.telegram_user import DonateStatus
from app.repositories.telegram_user import RepositoryTelegramUser
from app.tasks.taskiq.telegram import send_message_task
from app.utils.texts import get_sponsor_activation_text


class MatrixNotifierService:
    def __init__(
            self,
            repository_telegram_user: RepositoryTelegramUser,
    ):
        self._repository_telegram_user = repository_telegram_user

    async def notify_invited_users_about_activation(
            self,
            sponsor_user_id: int,
            status: DonateStatus,
    ) -> None:
        sponsor = self._repository_telegram_user.get(
            user_id=sponsor_user_id,
        )
        if not sponsor:
            return

        notification_text = get_sponsor_activation_text(
            username=sponsor.username,
            status=status,
        )
        invited_users = self._repository_telegram_user.list(
            sponsor_user_id=sponsor_user_id,
        )
        for user in invited_users:
            await send_message_task.kiq(
                chat_id=user.user_id,
                text=notification_text
            )


