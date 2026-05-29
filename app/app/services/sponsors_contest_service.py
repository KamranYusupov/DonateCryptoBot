import uuid
from collections import Counter
from typing import Dict

import loguru

from app.repositories.telegram_user import RepositoryTelegramUser
from app.repositories.sponsors_contest import (
    RepositorySponsorsContest,
    RepositorySponsorsContestPoint,
)
from app.services.base.contest import BaseContestService
from app.models.telegram_user import TelegramUser


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






