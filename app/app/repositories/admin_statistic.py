from decimal import Decimal

from sqlalchemy import select, update

from app.models.statistic import AdminStatistic
from app.repositories.base import RepositoryBase


class RepositoryAdminStatistic(RepositoryBase[AdminStatistic]):
    """Репозиторий статистики админа"""

    def get(self) -> bool:
        statement = select(AdminStatistic)
        return self._session.execute(statement).scalar_one()

    def increment_system_bill(
            self,
            quantity: Decimal,
            triumph: bool = True,
    ) -> None:
        system_bill_field_name = "system_bill"
        if triumph:
            system_bill_field_name = f"triumph_{system_bill_field_name}"

        system_bill_field = getattr(AdminStatistic, system_bill_field_name)
        values = {system_bill_field_name: system_bill_field + quantity}

        statement = update(AdminStatistic).values(**values)
        self._session.execute(statement)



