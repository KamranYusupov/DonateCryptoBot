from typing import Sequence, Optional
import uuid

from sqlalchemy import desc
from sqlalchemy.sql import select

from app.models import TriumphBillTransaction
from app.repositories.base import RepositoryBase
from app.repositories.base.mixins import CountMixin


class RepositoryTriumphBillTransaction(
    RepositoryBase[TriumphBillTransaction],
    CountMixin,
):
    async def get_ordered_ids(
            self,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            **kwargs
    ) -> Sequence[uuid.UUID]:
        statement = (
            select(TriumphBillTransaction.id)
            .filter_by(**kwargs)
            .order_by(desc(TriumphBillTransaction.created_at))
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.execute(statement)
        return result.scalars().all()

    async def get_ordered_transactions(
            self,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            **kwargs
    ) -> Sequence[TriumphBillTransaction]:
        statement = (
            select(TriumphBillTransaction)
            .filter_by(**kwargs)
            .order_by(desc(TriumphBillTransaction.created_at))
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.execute(statement)
        return result.scalars().all()
