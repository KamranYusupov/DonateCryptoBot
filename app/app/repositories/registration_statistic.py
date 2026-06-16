from decimal import Decimal
from typing import Optional, Type, TypeVar

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.statistic import AdminStatistic, RegistrationStatistic
from app.repositories.base import RepositoryBase

ModelType = TypeVar("ModelType")

class RepositoryRegistrationStatistic:
    """Репозиторий статистики регистраций"""

    def __init__(
            self,
            session: Session,
            model: Type[ModelType] = RegistrationStatistic
    ):
        self._session = session
        self._model = model

    def increment_count(self) -> int:
        statement = (
            update(RegistrationStatistic)
            .where(RegistrationStatistic.id == 1)
            .values(count=RegistrationStatistic.count + 1)
            .returning(RegistrationStatistic.count)
        )

        result = self._session.execute(statement)
        return result.scalar()

