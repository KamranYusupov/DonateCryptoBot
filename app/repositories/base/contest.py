from typing import TypeVar, Generic, List, Optional
import uuid

from sqlalchemy import select, func, desc

from .base import RepositoryBase
from app.models.contest import AbstractContest

ContestModelType = TypeVar("ContestModelType", bound=AbstractContest)
ContestPointModelType = TypeVar("ContestPointModelType")


class RepositoryContestBase(
    RepositoryBase[ContestModelType],
    Generic[ContestModelType]
):
    """Абстрактный репозиторий для конкурсов"""

    async def get_ordered_ids(self, *args, **kwargs) -> List:
        statement = (
            select(self._model.id)
            .filter(*args)
            .filter_by(**kwargs)
            .order_by(desc(self._model.start_at))
        )
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def get_ordered_list(self, *args, **kwargs) -> List[ContestModelType]:
        statement = (
            select(self._model)
            .filter(*args)
            .filter_by(**kwargs)
            .order_by(desc(self._model.start_at))
        )
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def get_last(self, *args, **kwargs) -> Optional[ContestModelType]:
        statement = (
            select(self._model)
            .filter(*args)
            .filter_by(**kwargs)
            .order_by(desc(self._model.start_at))
            .limit(1)
        )
        result = await self._session.execute(statement)
        return result.scalars().first()

    async def get_previous_active_contest(self, current_contest_id: uuid.UUID):
        statement = (
            select(self._model)
            .where(
                self._model.id != current_contest_id,
                self._model.is_archived == False,
            )
            .order_by(desc(self._model.start_at))
            .limit(1)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()


class RepositoryContestPointBase(
    RepositoryBase[ContestPointModelType],
    Generic[ContestPointModelType]
):
    """Абстрактный репозиторий для баллов конкурса"""

    async def get_count(self, *args, **kwargs) -> int:
        statement = (
            select(func.count(self._model.id))
            .filter(*args)
            .filter_by(**kwargs)
        )
        result = await self._session.execute(statement)
        return result.scalar()

    async def get_grouped_points(self, contest_id: uuid.UUID) -> list[tuple[int, int]]:
        """
        Возвращает список кортежей (user_id, points_count),
        отсортированный  по количеству поинтов и created_at последнего point,
        для поля top_10_rating модели конкурса
        """

        statement = (
            select(self._model.user_id, func.count(self._model.id).label("points"))
            .filter_by(contest_id=contest_id)
            .group_by(self._model.user_id)
            .order_by(
                func.count(self._model.id).desc(),
                func.max(self._model.created_at).asc(),
            )
        )
        result = await self._session.execute(statement)
        return result.all()
