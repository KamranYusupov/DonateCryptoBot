import math
import uuid
from decimal import Decimal
from typing import Tuple, Any, Optional, List

import loguru

from app.repositories.statistic import RepositoryAdminStatistic
from app.repositories.telegram_user import RepositoryTelegramUser
from app.repositories.donate import RepositoryDonate, RepositoryDonateTransaction
from app.models.telegram_user import TelegramUser, DonateStatus
from app.schemas.donate import (
    DonateEntity,
    CreateDonateTransactionSchema,
    DonateTransactionSchema,
)
from app.models.donate import DonateTransactionType
from app.schemas.telegram_user import BillType
from app.schemas.transaction import DonateTransactionContextSchema


class DonateConfirmService:

    def __init__(
        self,
        repository_donate: RepositoryDonate,
        repository_donate_transaction: RepositoryDonateTransaction,
        repository_telegram_user: RepositoryTelegramUser,
        repository_admin_statistic: RepositoryAdminStatistic,

    ):
        self._repository_donate = repository_donate
        self._repository_donate_transaction = repository_donate_transaction
        self._repository_telegram_user = repository_telegram_user
        self._repository_admin_statistic = repository_admin_statistic

    @staticmethod
    def get_donate_status(
            donate_sum: int | Decimal,
    ) -> DonateStatus | None:
        if donate_sum == 10:
            return DonateStatus.TEST
        elif donate_sum == 25:
            return DonateStatus.BASE
        elif donate_sum == 50:
            return DonateStatus.BRONZE
        elif donate_sum == 100:
            return DonateStatus.SILVER
        elif donate_sum == 250:
            return DonateStatus.GOLD
        elif donate_sum == 500:
            return DonateStatus.PLATINUM
        elif donate_sum == 1000:
            return DonateStatus.BRILLIANT

        return None

    async def create_donate(
        self,
        telegram_user_id: uuid.UUID,
        transactions: list[DonateTransactionContextSchema],
        matrix_id: uuid.UUID,
        quantity: Decimal,
    ):
        """Создание сущности доната"""
        donate_dict = {
            "telegram_user_id": telegram_user_id,
            "quantity": quantity,
            "matrix_id": matrix_id,
        }
        donate = DonateEntity(**donate_dict)
        donate_obj = self._repository_donate.create(obj_in=donate.model_dump())
        await self._create_donate_transaction(
            donate_id=donate_obj.id, transactions=transactions
        )
        return donate_obj

    async def _create_donate_transaction(
            self,
            donate_id: uuid.UUID,
            transactions: list[DonateTransactionContextSchema],
    ):
        """
        Создание конкретной транзакции (часть доната), перечисляемой одному спонсору.
        При создании доната через create_donate - создаются автоматически.
        Всю инфу берет из donate_data.
        """
        for transaction in transactions:
            receiver = transaction.receiver

            if receiver.is_banned:
                receiver = self._repository_telegram_user.get(is_admin=True)

            donate_transaction_dict_obj = CreateDonateTransactionSchema(
                sponsor_id=receiver.id,
                donate_id=donate_id,
                quantity=transaction.quantity,
                type_=transaction.type_,
            )
            self._repository_donate_transaction.create(
                obj_in=donate_transaction_dict_obj.model_dump()
            )

    async def get_donate_by_id(self, donate_id: uuid.UUID):
        """Получить донат по id доната"""
        return self._repository_donate.get(id=donate_id)

    async def get_donate_by_telegram_user_id(
            self,
            telegram_user_id: uuid.UUID,
    ):
        return self._repository_donate.get_donate_by_telegram_user_id(
            telegram_user_id=telegram_user_id,
        )

    async def get_donate_transaction_by_id(self, donate_transaction_id: uuid.UUID):
        """Получить транзакцию по id"""
        return self._repository_donate_transaction.get(id=donate_transaction_id)

    async def get_donate_transaction_by_sponsor_id(self, sponsor_id: uuid.UUID):
        """Получить список транзакций по id спонсора (кому должны перечислить)."""
        return self._repository_donate_transaction.get_donate_transaction_by_sponsor_id(
            sponsor_id
        )

    async def get_all_my_donates_and_transactions(
            self,
            telegram_user_id: uuid.UUID,
    ):
        """Получить все свои отправленные донаты в виде словаря {донат: транзакции доната}"""
        get_donates_kwargs = {"telegram_user_id": telegram_user_id}
        donates = self._repository_donate.get_donates_list(**get_donates_kwargs)
        output_dict = {}
        for donate in donates:
            donate_transactions = self._repository_donate_transaction.list(
                donate_id=donate.id
            )
            output_dict[donate] = donate_transactions
        return output_dict

    async def get_donate_transactions_by_donate_id(
            self,
            donate_id: uuid.UUID,
            return_schemas: bool = False,
    ) -> List[DonateTransactionSchema]:
        transactions = self._repository_donate_transaction.list(
            donate_id=donate_id,
        )

        if not return_schemas:
            return transactions

        if not transactions:
            return []

        return [
            DonateTransactionSchema.model_validate(transaction)
            for transaction in transactions
        ]

    async def update_bills_by_donate_id(
            self,
            donate_id: uuid.UUID,
            is_bot: bool = False
    ):
        transactions = self._repository_donate_transaction.list(
            donate_id=donate_id,
        )
        system_bill_donate = 0
        for transaction in transactions:
            # FIXME: N+1 проблема с repository_telegram_user.increment_bill
            if transaction.type_ == DonateTransactionType.SYSTEM:
                system_bill_donate += transaction.quantity
                continue

            self._repository_telegram_user.increment_bill(
                telegram_user_id=transaction.sponsor_id,
                bill_type=BillType.WITHDRAW,
                amount=transaction.quantity,
                with_donate_sum=True,
            )
            if is_bot:
                system_bill_donate -= transaction.quantity

        if not system_bill_donate:
            return

        donate  = self._repository_donate.get(id=donate_id)
        status = self.get_donate_status(int(donate.quantity))

        is_triumph: bool = (status in (DonateStatus.BRILLIANT, ))
        self._repository_admin_statistic.increment_system_bill(
            quantity=system_bill_donate,
            triumph=is_triumph
        )


    async def get_all_donates_and_transactions(
            self,
    ):
        """Получить все свои отправленные донаты в виде словаря {донат: транзакции доната}"""
        get_donates_kwargs = dict()

        donates = self._repository_donate.get_donates_list(**get_donates_kwargs)
        output_dict = {}
        for donate in donates:
            donate_transactions = self._repository_donate_transaction.list(
                donate_id=donate.id
            )
            output_dict[donate] = donate_transactions
        return output_dict

    async def get_all_donate_transactions(self):
        return self._repository_donate_transaction.get_transactions_list()

    async def delete_donate_with_transactions(self, donate_id: uuid.UUID) -> None:
        return self._repository_donate.delete_donate_with_transactions(
            donate_id=donate_id
        )

    async def get_donates_count(self, *args, **kwargs) -> int:
        return self._repository_donate.get_count(*args, **kwargs)

    async def get_donates_by_matrices_ids(self, matrices_ids: List[uuid.UUID | str]):
        return self._repository_donate.get_donates_by_matrices_ids(matrices_ids)

    async def get_system_bill(self) -> Decimal:
        transactions_quantities = (
            self._repository_donate_transaction.get_transactions_quantities(
                type_=DonateTransactionType.SYSTEM
            )
        )
        bots_transactions_quantities = \
            self._repository_donate_transaction.get_bots_transactions_quantities()

        return sum(transactions_quantities) - sum(bots_transactions_quantities)

    async def get_donates_sum(self, *args, **kwargs) -> Decimal:
        return sum(self._repository_donate.get_donates_quantities(*args, **kwargs))

    async def get_transactions_sum(self, *args, **kwargs):
        return sum(
            self._repository_donate_transaction.get_transactions_quantities(
                *args,
                **kwargs
            )
        )

