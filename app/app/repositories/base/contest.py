from typing import TypeVar, Generic, List, Optional
from sqlalchemy import select, func

from .base import RepositoryBase
from app.models.contest import AbstractContest

ContestModelType = TypeVar("ContestModelType", bound=AbstractContest)
ContestPointModelType = TypeVar("ContestPointModelType")


class RepositoryContestBase(
    RepositoryBase[ContestModelType],
    Generic[ContestModelType]
):
    """Абстрактный репозиторий для конкурсов"""

    def get_ordered_ids(self, *args, **kwargs) -> List:
        statement = (
            select(self._model.id)
            .filter(*args)
            .filter_by(**kwargs)
            .order_by(self._model.start_date)
        )
        return self._session.execute(statement).scalars().all()

    def get_ordered_list(self, *args, **kwargs) -> List[ContestModelType]:
        statement = (
            select(self._model)
            .filter(*args)
            .filter_by(**kwargs)
            .order_by(self._model.start_date)
        )
        return self._session.execute(statement).scalars().all()

    def get_last(self, *args, **kwargs) -> Optional[ContestModelType]:
        statement = (
            select(self._model)
            .filter(*args)
            .filter_by(**kwargs)
            .order_by(self._model.start_date)
        )
        return self._session.execute(statement).scalars().first()


class RepositoryContestPointBase(
    RepositoryBase[ContestPointModelType],
    Generic[ContestPointModelType]
):
    """Абстрактный репозиторий для баллов конкурса"""

    def get_count(self, *args, **kwargs) -> int:
        statement = (
            select(func.count(self._model.id))
            .filter(*args)
            .filter_by(**kwargs)
        )
        return self._session.execute(statement).scalar()