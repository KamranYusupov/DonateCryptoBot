from typing import Optional
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
