import uuid
from typing import Optional, Sequence
from uuid import UUID

from app.models import TriumphBillTransaction, TriumphBillTransactionType
from app.repositories.triumph_bill_transaction import RepositoryTriumphBillTransaction
from app.services.base.crud_service import CrudServiceMixin


class TriumphBillTransactionService(CrudServiceMixin[RepositoryTriumphBillTransaction]):
    def __init__(
            self,
            repository_triumph_bill_transaction: RepositoryTriumphBillTransaction,
    ):
        super().__init__(repository=repository_triumph_bill_transaction)
        self._repository_triumph_bill_transaction = repository_triumph_bill_transaction

    async def get_ordered_ids(
            self,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            **kwargs,
    ) -> Sequence[uuid.UUID]:
        return (
            self._repository_triumph_bill_transaction
            .get_ordered_ids(
                limit=limit,
                offset=offset,
                **kwargs
            )
        )

    async def get_ordered_transactions(
            self,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            **kwargs
    ) -> Sequence[TriumphBillTransaction]:
        return (
            self._repository_triumph_bill_transaction
            .get_ordered_transactions(
                limit=limit,
                offset=offset,
                **kwargs
            )
        )

    async def get_count(self, **kwargs):
        return self._repository_triumph_bill_transaction.get_count(**kwargs)
