import uuid
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select, delete, update, func
from sqlalchemy.orm import selectinload

from app.models.telegram_user import TelegramUser, DonateStatus
from app.schemas.marketing import MatrixMarketingScope
from .base import RepositoryBase
from app.models.donate import Donate, DonateTransaction, DonateTransactionType
from app.models.matrix import Matrix, MatrixEngineType, MatrixMarketingType


class RepositoryDonate(RepositoryBase[Donate]):
    """Репозиторий доната"""

    async def get_matrix_engine_type(
            self,
            donate_id: uuid.UUID,
    ) -> MatrixEngineType:
        statement = (
            select(Matrix.engine_type)
            .join(Donate, Donate.matrix_id == Matrix.id)
            .where(Donate.id == donate_id)
        )

        result = await self._session.execute(statement)
        return result.scalar()

    async def get_quantity_by_id(self, donate_id: uuid.UUID) -> Optional[Decimal]:
        statement = (
            select(Donate.quantity)
            .where(Donate.id == donate_id)
        )

        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_donates_list(
            self,
            *args,
            marketing_type: MatrixMarketingType | None = None,
            **kwargs
    ):
        statement = (
            select(Donate)
            .filter(*args)
            .filter_by(**kwargs)
        )

        if marketing_type:
            statement = (
                statement
                .join(Donate.matrix)
                .where(Matrix.marketing_type == marketing_type)
            )

        statement = (
            statement
            .order_by(Donate.created_at.desc())
        )

        result = await self._session.execute(statement)
        return result.scalars().all()

    async def get_donate_by_telegram_user_id(
            self,
            telegram_user_id: uuid.UUID,
    ):
        statement = (
            select(Donate).filter_by(
                telegram_user_id=telegram_user_id,
            )
        ).order_by(Donate.created_at.desc())

        result = await self._session.execute(statement)
        return result.scalars().all()

    async def delete_donate_with_transactions(self, donate_id: uuid.UUID):
        delete_transactions_statement = (
            delete(DonateTransaction)
            .where(DonateTransaction.donate_id == donate_id)
        )

        delete_donate_statement = (
            delete(Donate)
            .where(Donate.id == donate_id)
        )

        await self._session.execute(delete_transactions_statement)
        await self._session.execute(delete_donate_statement)

    async def get_count(self, *args, **kwargs) -> int:
        statement = (
            select(func.count(Donate.id))
            .filter(*args)
            .filter_by(**kwargs)
        )

        result = await self._session.execute(statement)
        return result.scalar()

    async def get_donates_by_matrices_ids(
            self,
            matrices_ids: List[uuid.UUID | str],
            **kwargs,
    ):
        statement = (
            select(Donate)
            .filter(Donate.matrix_id.in_(matrices_ids))
            .filter_by(**kwargs)
            .order_by(Donate.created_at.desc())
        )

        result = await self._session.execute(statement)
        return result.scalars().all()

    async def get_donates_quantities(self, *args, **kwargs):
        statement = (
            select(Donate.quantity)
            .join(Donate.telegram_user)
            .filter(TelegramUser.is_bot == False, *args).filter_by(**kwargs))

        result = await self._session.execute(statement)
        return result.scalars().all()


class RepositoryDonateTransaction(RepositoryBase[DonateTransaction]):
    """Репозиторий доната"""

    async def get_transactions_list(self):
        statement = select(DonateTransaction).order_by(
            DonateTransaction.created_at.desc()
        )

        result = await self._session.execute(statement)
        return result.scalars().all()

    async def get_transactions_quantities(self, *args, **kwargs):
        statement = select(
            DonateTransaction.quantity
        ).filter(*args).filter_by(**kwargs)

        result = await self._session.execute(statement)
        return result.scalars().all()

    async def get_bots_transactions_quantities(self):
        statement = (
            select(DonateTransaction.quantity)
            .join(DonateTransaction.donate)
            .join(Donate.telegram_user)
            .where(
                DonateTransaction.type_ == DonateTransactionType.MATRIX,
                TelegramUser.is_bot == True
            )
        )

        result = await self._session.execute(statement)
        return result.scalars().all()

    async def get_donate_transaction_by_sponsor_id(
            self,
            sponsor_id: uuid.UUID,
            marketing_type: MatrixMarketingType | None = None,
    ):
        statement = select(DonateTransaction)


        if marketing_type:
            statement = (
                statement
                .join(DonateTransaction.donate)
                .join(Donate.matrix)
                .where(Matrix.marketing_type == marketing_type)
            )

        statement = (
            statement
            .where(DonateTransaction.sponsor_id == sponsor_id)
            .order_by(DonateTransaction.created_at.desc())
        )

        result = await self._session.execute(statement)
        return result.scalars().all()

