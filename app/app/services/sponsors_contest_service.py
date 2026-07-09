from datetime import datetime, time, timedelta
from typing import Dict

import loguru

from app.core.config import settings
from app.exceptions.donate import DonateStatusNotFoundError
from app.models import SponsorsContestPoint
from app.repositories.telegram_user import RepositoryTelegramUser
from app.repositories.sponsors_contest import (
    RepositorySponsorsContest,
    RepositorySponsorsContestPoint,
)
from app.services.base.contest import BaseContestService
from app.services.base.crud_service import CrudServiceMixin
from app.models.telegram_user import TelegramUser, DonateStatus
from app.utils.datetime import get_start_of_week, to_main_tz


class SponsorsContestService(
    BaseContestService[RepositorySponsorsContest, RepositorySponsorsContestPoint],
    CrudServiceMixin[RepositorySponsorsContest],
):
    def __init__(
            self,
            repository_contest: RepositorySponsorsContest,
            repository_contest_point: RepositorySponsorsContestPoint,
            repository_telegram_user: RepositoryTelegramUser,
    ) -> None:
        BaseContestService.__init__(
            self,
            repository_contest=repository_contest,
            repository_contest_point=repository_contest_point
        )
        CrudServiceMixin.__init__(self, repository=repository_contest)
        self._repository_telegram_user = repository_telegram_user

    def get_points_count_by_status(self, status: DonateStatus) -> int:
        return int(status.get_status_donate_value() / 25)

    async def create_contest_point(
            self,
            user_id: int,
            status: DonateStatus,
    ) -> SponsorsContestPoint:
        current_contest, _ = await self.get_or_create_current_contest()
        points_count = self.get_points_count_by_status(status)
        contest_data = {
            "user_id": user_id,
            "count": points_count,
            "contest_id": current_contest.id,
        }
        return await self._repository_contest_point.create(contest_data)

    def _get_period_start(self) -> datetime:
        now = to_main_tz(datetime.now())

        this_week_monday_date = get_start_of_week(now.date())

        this_week_start_at = datetime.combine(
            this_week_monday_date,
            time(12, 0, 0),
            tzinfo=settings.timezone_info
        )

        if now >= this_week_start_at:
            return this_week_start_at

        return this_week_start_at - timedelta(days=7)

    async def _get_user_str_map(
            self,
            user_ids: set[int]
    ) -> Dict[int, str]:
        users = await self._repository_telegram_user.list(
            TelegramUser.user_id.in_(user_ids)
        ) if user_ids else []

        return {u.user_id: u.full_name for u in users}

    def _calculate_prize_fund(
            self,
            init_prize_fund: int,
            total_points: int
    ) -> int:
        return init_prize_fund + (total_points // 10) * 10






