from datetime import datetime, time
from typing import Dict

import loguru

from app.core.config import settings
from app.repositories.telegram_user import RepositoryTelegramUser
from app.repositories.sponsors_contest import (
    RepositorySponsorsContest,
    RepositorySponsorsContestPoint,
)
from app.services.base.contest import BaseContestService
from app.models.telegram_user import TelegramUser
from app.utils.datetime import get_start_of_week


class SponsorsContestService(
    BaseContestService[RepositorySponsorsContest, RepositorySponsorsContestPoint]
):
    def __init__(
            self,
            repository_contest: RepositorySponsorsContest,
            repository_contest_point: RepositorySponsorsContestPoint,
            repository_telegram_user: RepositoryTelegramUser,
    ) -> None:
        super().__init__(
            repository_contest=repository_contest,
            repository_contest_point=repository_contest_point
        )
        self._repository_telegram_user = repository_telegram_user

    def _get_period_start(self) -> datetime:
        start_of_week = get_start_of_week()

        start_at = datetime.combine(
            start_of_week,
            time(12, 0, 0),
            tzinfo=settings.timezone_info
        )
        return start_at

    async def _get_user_str_map(
            self,
            user_ids: set[int]
    ) -> Dict[int, str]:
        users = self._repository_telegram_user.list(
            TelegramUser.user_id.in_(user_ids)
        ) if user_ids else []

        return {u.user_id: u.full_name for u in users}

    def _calculate_prize_fund(
            self,
            init_prize_fund: int,
            total_points: int
    ) -> int:
        return init_prize_fund + (total_points // 10) * 10






