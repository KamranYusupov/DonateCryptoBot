from sqlalchemy import select

from app.models.statistic import AdminStatistic
from app.repositories.base import RepositoryBase


class RepositoryAdminStatistic(RepositoryBase[AdminStatistic]):
    """Репозиторий конкурса кураторов"""

    def get(self) -> bool:
        statement = select(AdminStatistic)
        return self._session.execute(statement).scalar_one()


