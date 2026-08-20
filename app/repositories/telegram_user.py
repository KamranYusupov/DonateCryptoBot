import uuid
from decimal import Decimal
from uuid import UUID
from typing import Optional, Sequence

from sqlalchemy import select, func, update
from sqlalchemy.orm import joinedload, aliased

from .base import RepositoryBase
from app.models.telegram_user import TelegramUser, DonateStatus
from app.models.telegram_user import BillType
from app.core.config import settings


class RepositoryTelegramUser(RepositoryBase[TelegramUser]):
    """Репозиторий телеграм пользователя"""

    async def get_list(
            self,
            *args,
            join_sponsor: bool = False,
            **kwargs
    ):

        query_options = []
        if join_sponsor:
            query_options.append(joinedload(TelegramUser.sponsor))

        statement = (
            select(TelegramUser)
            .options(*query_options)
            .filter(*args)
            .filter_by(**kwargs)
            .order_by(TelegramUser.created_at)
        )
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def get_ids(self, *args, **kwargs) -> list[UUID]:
        statement = (
            select(TelegramUser.id)
            .filter(*args)
            .filter_by(**kwargs)
        )
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def get_username_by_id(self, telegram_user_id: uuid.UUID) -> Optional[str]:
        statement = (
            select(TelegramUser.username)
            .where(TelegramUser.id == telegram_user_id)
        )

        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_user_ids(self, *args, **kwargs) -> list[int]:
        statement = (
            select(TelegramUser.user_id)
            .filter(*args)
            .filter_by(**kwargs)
        )
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def get_active_users_by_ids(self, ids: list[UUID], **kwargs):
        statement = (
            select(TelegramUser)
            .where(
                TelegramUser.status != None,
                TelegramUser.id.in_(ids),
            )
            .filter_by(**kwargs)
        )

        result = await self._session.execute(statement)
        users = result.scalars().all()
        mapping = {user.id: user for user in users}

        return [mapping[i] for i in ids if i in mapping]

    async def get_count(
            self,
            *args,
            **kwargs
    ) -> int:
        statement = (
            select(func.count(TelegramUser.user_id))
            .filter(*args)
            .filter_by(**kwargs)
        )
        result = await self._session.execute(statement)
        return result.scalar()

    async def get_invited_users(
            self,
            sponsor_user_id: int
    ):
        """Получение списка всех приглашенных пользователей"""
        statement = (
            select(TelegramUser)
            .filter_by(
                sponsor_user_id=sponsor_user_id,
                is_bot=False,
            )
            .order_by(TelegramUser.created_at)
        )

        result = await self._session.execute(statement)
        return result.scalars().all()

    async def get_sponsors(
        self, sponsor_user_id: int
    ) -> tuple[TelegramUser, TelegramUser, TelegramUser]:
        t1, t2, t3 = [aliased(TelegramUser) for _ in range(3)]
        statement = (
            select(t1, t2, t3)
            .outerjoin(t2, t2.user_id == t1.sponsor_user_id)
            .outerjoin(t3, t3.user_id == t2.sponsor_user_id)
            .filter(t1.user_id == sponsor_user_id)
            .limit(1)
        )
        result = await self._session.execute(statement)

        return result.one_or_none()


    async def get_sponsor_recursively(
            self,
            *args,
            sponsor_user_id: int,
            **kwargs
    ) -> TelegramUser | None:
        sponsor_by_user_id = await self.get(user_id=sponsor_user_id)

        if not sponsor_by_user_id:
            return None

        if not (args or kwargs):
            return sponsor_by_user_id

        sponsor_by_full_query = await self.get(*args, user_id=sponsor_user_id, **kwargs)
        if sponsor_by_full_query:
            return sponsor_by_full_query

        return await self.get_sponsor_recursively(
            *args,
            sponsor_user_id=sponsor_by_user_id.sponsor_user_id,
            **kwargs)


    async def get_telegram_users_by_ids(
            self,
            telegram_users_ids: list[UUID]
    ) -> list[TelegramUser]:
        statement = select(TelegramUser).filter(
            TelegramUser.id.in_(telegram_users_ids)
        )
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def get_bills(
            self,
            *args,
            bill_type: BillType,
            **kwargs,
    ) -> list[Decimal]:
        bill_field = getattr(TelegramUser, f"bill_for_{bill_type.value}")
        statement = select(bill_field).filter(*args).filter_by(**kwargs)
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def get_triumph_bills_sum(
            self,
            *args,
            **kwargs,
    ) -> Decimal:
        statement = (
            select(func.sum(TelegramUser.triumph_bill))
            .filter(*args)
            .filter_by(**kwargs)
        )

        result = await self._session.execute(statement)
        return result.scalar()  or Decimal("0.0")

    async def increment_bill(
            self,
            telegram_user_id: UUID,
            bill_type: BillType,
            amount: Decimal,
            with_donates_sum: bool = False,
    ) -> None:
        update_values = {}

        bill_column = TelegramUser.get_bill_column_by_type(bill_type)
        bill_field_name = TelegramUser.get_bill_field_by_type(bill_type)

        update_values[bill_field_name] = bill_column + amount

        if with_donates_sum:
            update_values["donates_sum"] = TelegramUser.donates_sum + amount

        statement = (
            update(TelegramUser)
            .where(TelegramUser.id == telegram_user_id)
            .values(**update_values)
        )

        await self._session.execute(statement)

    async def increment_bill_for_registration(
            self,
            telegram_user_id: UUID,
            bill_type: BillType,
            amount: Decimal,
    ) -> None:
        update_values = {}

        bill_column = TelegramUser.get_bill_column_by_type(bill_type)
        bill_field_name = TelegramUser.get_bill_field_by_type(bill_type)

        update_values[bill_field_name] = bill_column + amount
        update_values["donates_sum_for_registration"] = \
            TelegramUser.donates_sum_for_registration + 1

        statement = (
            update(TelegramUser)
            .where(TelegramUser.id == telegram_user_id)
            .values(**update_values)
        )

        await self._session.execute(statement)

    async def increase_triumph_bills_by_percent(
            self,
            percent: Decimal = settings.start_marketing.triumph_bill_increase_percent,
    ) -> None:
        multiplier = percent / 100
        new_bill_expr = (
            TelegramUser.triumph_bill +
            TelegramUser.triumph_bill * multiplier
        )
        triumph_amount = Decimal(DonateStatus.BRILLIANT.amount)
        statement = (
            update(TelegramUser)
            .where(
                TelegramUser.triumph_bill.is_not(None),
                TelegramUser.triumph_bill < triumph_amount
            )
            .values(
                triumph_bill=func.least(new_bill_expr, triumph_amount)
            )
        )

        await self._session.execute(statement)

    async def get_donates_sum_with_for_update_by_id(
            self,
            telegram_user_id: uuid.UUID
    ) -> Decimal | None:
        statement = (
            select(TelegramUser.donates_sum)
            .where(TelegramUser.id == telegram_user_id)
            .with_for_update()
        )

        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_user_ids_by_active_triumph_bill(self) -> Sequence[int]:
        return await self.get_user_ids(TelegramUser.triumph_bill > 0)

    async def update_username(
            self,
            telegram_user_id: uuid.UUID,
            new_username: str,
    ) -> int:
        statement = (
            update(TelegramUser)
            .where(TelegramUser.id == telegram_user_id)
            .values(username=new_username)
        )

        result = await self._session.execute(statement)
        return result.rowcount
