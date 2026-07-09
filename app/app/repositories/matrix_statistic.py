from typing import TypeVar, Type

from sqlalchemy.orm import Session

from app.models.statistic import MatrixStatistic
from app.repositories.base import RepositoryBase

from sqlalchemy import update, select


ModelType = TypeVar("ModelType")

class RepositoryMatrixStatistic:
    """Репозиторий таблицы matrix_statistic"""

    def __init__(
            self,
            session: Session,
            model: Type[ModelType] = MatrixStatistic
    ):
        self._session = session
        self._model = model

    async def get_activation_count(self) -> int:
        statement = select(MatrixStatistic.activation_count)

        result = await self._session.execute(statement)
        return result.scalar_one()

    async def increment_activations_count(self) -> int:
        statement = (
            update(MatrixStatistic)
            .where(MatrixStatistic.id == 1)
            .values(activation_count=MatrixStatistic.activation_count + 1)
            .returning(MatrixStatistic.activation_count)
        )

        result = await self._session.execute(statement)
        return result.scalar()
