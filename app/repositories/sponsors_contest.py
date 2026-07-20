import uuid
from typing import List

from sqlalchemy import select, delete, update, func
from sqlalchemy.orm import selectinload

from app.models.contest import SponsorsContest, SponsorsContestPoint
from app.repositories.base.contest import RepositoryContestBase, RepositoryContestPointBase


class RepositorySponsorsContest(
    RepositoryContestBase[SponsorsContest]):
    pass


class RepositorySponsorsContestPoint(
    RepositoryContestPointBase[SponsorsContestPoint]
):

    async def get_grouped_points(self, contest_id: uuid.UUID) -> list[tuple[int, int]]:
        """
        Возвращает список кортежей (user_id, points_count),
        отсортированный  по количеству поинтов и created_at последнего point,
        для поля top_10_rating модели конкурса
        """
        statement = (
            select(
                SponsorsContestPoint.user_id,
                func.sum(SponsorsContestPoint.count).label("points")
            )
            .filter_by(contest_id=contest_id)
            .group_by(SponsorsContestPoint.user_id)
            .order_by(
                func.sum(SponsorsContestPoint.count).desc(),
                func.max(SponsorsContestPoint.created_at).asc(),
            )
        )
        result = await self._session.execute(statement)
        return result.all()
