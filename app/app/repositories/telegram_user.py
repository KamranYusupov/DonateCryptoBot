from decimal import Decimal
from uuid import UUID
from typing import Optional

from sqlalchemy import select, func, update
from sqlalchemy.orm import joinedload, aliased

from .base import RepositoryBase
from app.models.telegram_user import TelegramUser, DonateStatus
from app.schemas.telegram_user import BillType
from app.core.config import settings


class RepositoryTelegramUser(RepositoryBase[TelegramUser]):
    """Репозиторий телеграм пользователя"""

    def get_list(
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
        return self._session.execute(statement).scalars().all()

    def get_ids(self, *args, **kwargs) -> list[UUID]:
        statement = (
            select(TelegramUser.id)
            .filter(*args)
            .filter_by(**kwargs)
        )
        return self._session.execute(statement).scalars().all()

    def get_active_users_by_ids(self, ids: list[UUID], **kwargs):
        statement = (
            select(TelegramUser)
            .where(
                TelegramUser.status != DonateStatus.NOT_ACTIVE,
                TelegramUser.id.in_(ids),
            )
            .filter_by(**kwargs)
        )

        users = self._session.execute(statement).scalars().all()
        mapping = {user.id: user for user in users}

        return [mapping[i] for i in ids if i in mapping]

    def get_count(
            self,
            *args,
            **kwargs
    ) -> int:
        statement = (
            select(func.count(TelegramUser.user_id))
            .filter(*args)
            .filter_by(**kwargs)
        )
        return self._session.execute(statement).scalar()

    def get_invited_users(
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

        return self._session.execute(statement).scalars().all()

    def get_telegram_user_with_sponsors(
        self, user_id: int
    ) -> tuple[TelegramUser, TelegramUser, TelegramUser]:
        t1, t2, t3, t4 = [aliased(TelegramUser) for _ in range(4)]
        sponsors = (
            self._session.query(t1, t2, t3, t4)
            .outerjoin(t2, t2.user_id == t1.sponsor_user_id)
            .outerjoin(t3, t3.user_id == t2.sponsor_user_id)
            .outerjoin(t4, t4.user_id == t3.sponsor_user_id)
            .filter(t1.user_id == user_id)
            .limit(1)
            .one_or_none()
        )

        return sponsors

    def get_sponsor_recursively(
            self,
            *args,
            sponsor_user_id: int,
            **kwargs
    ) -> TelegramUser | None:
        sponsor_by_user_id = self.get(user_id=sponsor_user_id)

        if not sponsor_by_user_id:
            return None

        if not (args or kwargs):
            return sponsor_by_user_id

        sponsor_by_full_query = self.get(*args, user_id=sponsor_user_id, **kwargs)
        if sponsor_by_full_query:
            return sponsor_by_full_query

        return self.get_sponsor_recursively(
            *args,
            sponsor_user_id=sponsor_by_user_id.sponsor_user_id,
            **kwargs)


    def get_telegram_users_by_ids(
            self,
            telegram_users_ids: list[UUID]
    ) -> list[TelegramUser]:
        statement = select(TelegramUser).filter(
            TelegramUser.id.in_(telegram_users_ids)
        )
        return self._session.execute(statement).scalars().all()

    def get_bills(
            self,
            *args,
            bill_type: BillType,
            **kwargs,
    ) -> list[Decimal]:
        bill_field = getattr(TelegramUser, f"bill_for_{bill_type.value}")
        statement = select(bill_field).filter(*args).filter_by(**kwargs)
        return self._session.execute(statement).scalars().all()

    def increment_bill(
            self,
            telegram_user_id: UUID,
            bill_type: BillType,
            amount: Decimal,
            with_donate_sum: bool = False,
    ) -> None:
        bill_field_name = f"bill_for_{bill_type.value}"
        donates_sum_field_name = "donates_sum"

        bill = getattr(TelegramUser, bill_field_name)
        donates_sum = getattr(TelegramUser, donates_sum_field_name)
        update_values = {bill_field_name: bill + amount}

        if with_donate_sum:
            update_values["donates_sum"] = donates_sum + amount

        statement = (
            update(TelegramUser)
            .where(TelegramUser.id == telegram_user_id)
            .values(**update_values)
        )

        self._session.execute(statement)

    def increment_triumph_bill(
            self,
            user_id: int,
            amount: int,
    ):
        statement = (
            update(TelegramUser)
            .where(TelegramUser.user_id == user_id)
            .values(triumph_bill=TelegramUser.triumph_bill + amount)
        )

        self._session.execute(statement)

    def increase_triumph_bills_by_percent(
            self,
            percent: Decimal = settings.triumph_bill_increase_percent,
    ) -> None:
        multiplier = percent / 100
        statement = (
            update(TelegramUser)
            .where(TelegramUser.triumph_bill.is_not(None))
            .values(triumph_bill=(
                TelegramUser.triumph_bill
                + TelegramUser.triumph_bill * multiplier
            ))
        )

        self._session.execute(statement)
