from sqlalchemy import select

from .base import RepositoryBase
from app.models.withdrawal_request import WithdrawalRequest


class RepositoryWithdrawalRequest(RepositoryBase[WithdrawalRequest]):
    """Репозиторий телеграм пользователя"""

    async def get_withdrawal_requests(self, *args, order_by: list = [], **kwargs):
        statement = (
            select(WithdrawalRequest)
            .filter(*args)
            .filter_by(**kwargs)
            .order_by(*order_by)
        )
        result = await self._session.execute(statement)
        return result.scalars().all()
