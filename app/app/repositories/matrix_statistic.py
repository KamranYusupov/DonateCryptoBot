from app.models.statistic import MatrixStatistic
from app.repositories.base import RepositoryBase

from sqlalchemy import update

class RepositoryMatrixStatistic(RepositoryBase[MatrixStatistic]):
    """Репозиторий таблицы matrix_statistic"""

    def increment_activations_count(self) -> int:
        statement = (
            update(MatrixStatistic)
            .where(MatrixStatistic.id == 1)
            .values(activation_count=MatrixStatistic.activation_count + 1)
            .returning(MatrixStatistic.activation_count)
        )

        result = self._session.execute(statement)
        return result.scalar()
