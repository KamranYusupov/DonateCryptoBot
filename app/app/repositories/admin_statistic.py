from decimal import Decimal

from sqlalchemy import select, update

from app.models.statistic import AdminStatistic
from app.repositories.base import RepositoryBase


class RepositoryAdminStatistic(RepositoryBase[AdminStatistic]):
    """Репозиторий статистики админа"""

    def get(self) -> bool:
        statement = select(AdminStatistic)
        return self._session.execute(statement).scalar_one()

    def increment_system_bill_and_total_donates_sum(
            self,
            *,
            system_bill_amount: Decimal | int,
            total_donates_sum_amount: Decimal | int,
            triumph: bool = True,
    ) -> None:
        system_bill_field, system_bill_field_name = (
            AdminStatistic.get_system_bill_field_with_name(triumph)
        )
        total_donates_sum_field = AdminStatistic.total_donates_sum
        values = {
            system_bill_field_name: system_bill_field + system_bill_amount,
            "total_donates_sum": total_donates_sum_field + total_donates_sum_amount,
        }

        statement = update(AdminStatistic).values(**values)
        self._session.execute(statement)

    def increment_system_bill(
            self,
            amount: Decimal | int,
            triumph: bool = True,
    ) -> None:
        system_bill_field, system_bill_field_name = (
            AdminStatistic.get_system_bill_field_with_name(triumph)
        )
        values = {system_bill_field_name: system_bill_field + amount}

        statement = update(AdminStatistic).values(**values)
        self._session.execute(statement)

    def increment_total_donates_sum(
            self,
            amount: int | Decimal,
    ) -> None:
        total_donates_sum_field = getattr(AdminStatistic, "total_donates_sum")
        values = {"total_donates_sum": total_donates_sum_field + amount}

        statement = update(AdminStatistic).values(**values)
        self._session.execute(statement)



