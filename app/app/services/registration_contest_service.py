from datetime import datetime
from typing import Dict

from app.models import RegistrationContestPoint
from app.models.telegram_user import TelegramUser
from app.repositories.registration_contest import (
    RepositoryRegistrationContest,
    RepositoryRegistrationContestPoint,
)
from app.repositories.telegram_user import RepositoryTelegramUser
from app.services.base.contest import BaseContestService
from app.services.base.crud_service import CrudServiceMixin
from app.utils.datetime import get_saturday_noon_period_start


class RegistrationContestService(
    BaseContestService[RepositoryRegistrationContest, RepositoryRegistrationContestPoint],
    CrudServiceMixin[RepositoryRegistrationContest],
):
    def __init__(
            self,
            repository_contest: RepositoryRegistrationContest,
            repository_contest_point: RepositoryRegistrationContestPoint,
            repository_telegram_user: RepositoryTelegramUser,
    ) -> None:
        BaseContestService.__init__(
            self,
            repository_contest=repository_contest,
            repository_contest_point=repository_contest_point
        )
        CrudServiceMixin.__init__(self, repository=repository_contest)
        self._repository_telegram_user = repository_telegram_user

    async def create_contest_point(self, user_id: int) -> RegistrationContestPoint:
        current_contest, _ = await self.get_or_create_current_contest()
        contest_data = {
            "user_id": user_id,
            "contest_id": current_contest.id,
        }
        return await self._repository_contest_point.create(contest_data)

    def _get_period_start(self) -> datetime:
        return get_saturday_noon_period_start()

    async def _get_user_str_map(
            self,
            user_ids: set[int]
    ) -> Dict[int, str]:
        users = await  self._repository_telegram_user.list(
            TelegramUser.user_id.in_(user_ids)
        ) if user_ids else []

        return {u.user_id: u.full_name for u in users}

    def _calculate_prize_fund(
            self,
            init_prize_fund: int,
            total_points: int
    ) -> int:
        return init_prize_fund + (total_points // 100) * 10
