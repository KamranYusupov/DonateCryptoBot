import uuid
from decimal import Decimal
from typing import Tuple, Any, List, Optional, Sequence
from sqlalchemy.exc import IntegrityError

from app.models import TelegramUser
from app.repositories.telegram_user import RepositoryTelegramUser
from app.repositories.referral_link import RepositoryReferralLink
from app.models.telegram_user import TelegramUser, DonateStatus
from app.schemas.telegram_user import TelegramUserEntity, generate_random_user
from app.models.telegram_user import BillType
from app.models.referral_link import ReferralLink
from app.services.base.crud_service import CrudServiceMixin


class TelegramUserService(CrudServiceMixin[RepositoryTelegramUser]):

    def __init__(
            self,
            repository_telegram_user: RepositoryTelegramUser,
            repository_referral_link: RepositoryReferralLink,
    ) -> None:
        super().__init__(repository=repository_telegram_user)
        self._repository_telegram_user = repository_telegram_user
        self._repository_referral_link = repository_referral_link

    async def get_list(
            self,
            *args,
            join_sponsor: bool = False,
            **kwargs
    ) -> list[TelegramUser]:
        return await self._repository_telegram_user.get_list(
            *args,
            join_sponsor=join_sponsor,
            **kwargs
        )

    async def get_user_ids(self, *args, **kwargs) -> list[int]:
        return await self._repository_telegram_user.get_user_ids(*args, **kwargs)

    async def get_telegram_user(self, **kwargs) -> TelegramUser | None:
        return await self._repository_telegram_user.get(**kwargs)

    async def exists(self, **kwargs) -> bool:
        return await self._repository_telegram_user.exists(**kwargs)

    async def get_admin(self) -> TelegramUser | None:
        return await self._repository_telegram_user.get(is_admin=True)

    async def create_telegram_user(
        self,
        user: TelegramUserEntity,
        sponsor: TelegramUser = None,
    ) -> TelegramUser | None:
        user_exist = await self._repository_telegram_user.get(user_id=user.user_id)
        if user_exist:
            return user_exist
        if sponsor:
            user.sponsor_user_id = sponsor.user_id
            sponsor.invites_count += 1 if not user.is_bot else 0
        return await self._repository_telegram_user.create(obj_in=user.model_dump())

    async def raw_create(self, obj_in):
        return await self._repository_telegram_user.create(obj_in=obj_in)

    async def create_bot_user(
            self,
            status: DonateStatus,
            depth_level: int = 0,
            sponsor_user_id: Optional[int] = None,
    ) -> TelegramUser:
        bot_user = None
        bot_user_schema = generate_random_user()
        bot_user_schema.status = status
        bot_user_schema.is_bot = True

        while not bot_user:
            try:
                bot_user = await self.create_telegram_user(
                    user=bot_user_schema,
                )
            except Exception:
                bot_user_schema = generate_random_user()
                bot_user_schema.sponsor_user_id = sponsor_user_id
                bot_user_schema.depth_level = depth_level
                bot_user_schema.is_bot = True
                continue

            if bot_user:
                break

        return bot_user

    async def get_sponsors(
        self, sponsor_user_id: int
    ) -> tuple[TelegramUser, TelegramUser, TelegramUser]:

        return await self._repository_telegram_user.get_sponsors(
            sponsor_user_id=sponsor_user_id
        )

    async def get_one_sponsor(self, user_id: int):
        return await self._repository_telegram_user.get_one_sponsor(user_id=user_id)

    async def delete(self, obj_id: uuid.UUID):
        await self._repository_telegram_user.delete(obj_id=obj_id)

    async def get_sponsor_recursively(self, *args, sponsor_user_id: int, **kwargs):
        return await self._repository_telegram_user.get_sponsor_recursively(
            *args, sponsor_user_id=sponsor_user_id, **kwargs
        )

    async def get_invited_users(
            self,
            sponsor_user_id: int
    ):
        """Получение списка всех приглашенных пользователей"""
        return await self._repository_telegram_user.get_invited_users(
            sponsor_user_id=sponsor_user_id
        )

    async def get_user_depth_level(self, user_id: int) -> int | None:
        """
        Вычисляет глубину пользователя итеративным подъемом по спонсорам.
        """
        current_id = user_id
        depth = 0

        while True:
            user = await self._repository_telegram_user.get(user_id=current_id)

            if not user:
                return None

            if user.is_admin:
                return depth

            current_id = user.sponsor_user_id
            depth += 1

            if depth > 10000:
                return None

    async def get_telegram_user_for_update(self, telegram_user_id: uuid.UUID):
        return await self._repository_telegram_user.get_for_update(
            telegram_user_id=telegram_user_id,
        )

    async def increment_global_safe(
            self,
            telegram_user_id: uuid.UUID,
            amount: Decimal,
            with_donates_sum: bool = False,
    ) -> None:
        return await self._repository_telegram_user.increment_global_safe(
            telegram_user_id, amount, with_donates_sum
        )

    async def get_count(self, *args, **kwargs) -> int:
        return await self._repository_telegram_user.get_count(*args, **kwargs)

    async def update(self, obj_id: uuid.UUID, obj_in):
        return await self._repository_telegram_user.update(obj_id=obj_id, obj_in=obj_in)

    async def get_ids(self, *args, **kwargs) -> List[uuid.UUID]:
        return await self._repository_telegram_user.get_ids(*args, **kwargs)

    async def get_bills_for_activation_sum(self, *args, **kwargs):
        return sum(
            await self._repository_telegram_user.get_bills(
                *args,
                bill_type=BillType.ACTIVATION,
                **kwargs,
            )
        )

    async def get_bills_for_withdraw_sum(self, *args, **kwargs):
        return sum(
            await self._repository_telegram_user.get_bills(
                *args,
                bill_type=BillType.WITHDRAW,
                **kwargs,
            )
        )

    async def get_triumph_bills_sum(self, **kwargs) -> Decimal:
        return await self._repository_telegram_user.get_triumph_bills_sum(**kwargs)

    async def increment_bill(
            self,
            telegram_user_id: uuid.UUID,
            bill_type: BillType,
            amount: Decimal,
            with_donates_sum: bool = False,
    ) -> None:
        await self._repository_telegram_user.increment_bill(
            telegram_user_id=telegram_user_id,
            bill_type=bill_type,
            amount=amount,
            with_donates_sum=with_donates_sum,
        )

    async def increment_bill_for_registration(
            self,
            telegram_user_id: uuid.UUID,
            bill_type: BillType,
            amount: Decimal,
    ) -> None:
        await self._repository_telegram_user.increment_bill_for_registration(
            telegram_user_id=telegram_user_id,
            bill_type=bill_type,
            amount=amount,
        )

    async def get_username_by_id(self, telegram_user_id: uuid.UUID) -> Optional[str]:
        return await self._repository_telegram_user.get_username_by_id(telegram_user_id)


    async def get_link_by_code(
            self,
            code: str,
    ) -> Optional[ReferralLink]:
        return await self._repository_referral_link.get(
            code=code,
        )

    async def get_active_referral_link(
            self,
            telegram_user_id: uuid.UUID,
    ) -> Optional[ReferralLink]:
        return await self._repository_referral_link.get(
            telegram_user_id=telegram_user_id,
            is_active=True,
        )

    async def generate_referral_link(
            self,
            telegram_user_id: uuid.UUID,
    ) -> ReferralLink:
        return await self._repository_referral_link.generate_referral_link(
            telegram_user_id=telegram_user_id
        )

    async def set_link_expired(
            self,
            referral_link_id: uuid.UUID,
    ) -> None:
        await self._repository_referral_link.update(
            obj_id=referral_link_id,
            obj_in={"is_active": False},
        )

    async def get_user_ids_by_active_triumph_bill(self) -> Sequence[int]:
        return await self._repository_telegram_user.get_user_ids_by_active_triumph_bill()


