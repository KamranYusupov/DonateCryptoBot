import typing
import uuid
from typing import TypeVar, Generic, Type

from urllib.parse import urljoin

from sqlalchemy.ext.mutable import MutableList, MutableDict
from sqlalchemy.orm import relationship, declared_attr

from app.core.config import settings

from sqlalchemy import (
    Column,
    DateTime,
    BigInteger,
    String,
    Boolean,
    Integer,
    Date,
    text, ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func


class UUIDMixin:
    """UUID миксин для ID моделей"""

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)


class TimestampedMixin:
    """Миксин для даты создания и даты обновления"""

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class AbstractTelegramUser:
    """Базовый пользователь телеграм"""

    user_id = Column(
        BigInteger, nullable=False, unique=True, index=True, doc="ID пользователя"
    )
    username = Column(String, nullable=True, doc="Username")
    first_name = Column(String, nullable=True, doc="Имя пользователя")
    last_name = Column(String, nullable=True, doc="Фамилия пользователя")
    is_active = Column(Boolean, default=True, doc="Активность")

    @property
    def full_name(self) -> str:
        """Получаем имя и фамилию пользователя вместе"""
        parts = [self.first_name, self.last_name]
        return " ".join(filter(None, parts))

    @property
    def full_username(self) -> str | None:
        """Получение username пользователя с возможностью перейти к нему."""
        return f"@{self.username}" if self.username else None

    @property
    def referral_url(self) -> str:
        """Получение реферальной ссылки, в качестве идентификатора используется Telegram ID пользователя"""

        if not isinstance(settings.bot_link, str) or not isinstance(
            settings.bot_name, str
        ):
            return "Ссылка на бота или имя бота не заданы в настройках."

        if self.user_id is None:
            return "User ID не задан."

        return urljoin(
            base=settings.bot_link.format(bot_name=settings.bot_name),
            url=f"?start={self.user_id}",
        )


class AbstractAdminUser:
    """Базовая модель пользователя для административной панели"""

    login = Column(String(255), doc="Логин")
    password = Column(String(80), doc="Пароль")
    is_active = Column(Boolean, default=True, doc="Активность")


class AbstractContest:
    """Абстрактная модель конкурса."""
    start_date = Column(Date, unique=True, index=True)
    prize_fund = Column(Integer, default=100, server_default=text("100"))
    init_prize_fund = Column(Integer, default=100, server_default=text("100"))
    top_10_rating = Column(MutableList.as_mutable(JSONB), default=list)
    results = Column(MutableDict.as_mutable(JSONB), index=True, default=dict)
    is_archived = Column(Boolean, default=False)


ContestModelType = TypeVar("ContestModelType")

class AbstractContestPoint(Generic[ContestModelType]):
    """
    Абстрактная модель балла конкурса.
    """
    __contest_model__: Type[ContestModelType]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # Сканируем базовые классы в поисках parameterized-родителя (AbstractContestPoint[...])
        for base in getattr(cls, "__orig_bases__", []):
            if typing.get_origin(base) is AbstractContestPoint:
                args = typing.get_args(base)
                if args and not isinstance(args[0], TypeVar):
                    # Магия: вытаскиваем SponsorsContest и записываем в класс
                    cls.__contest_model__ = args[0]
                    break

    user_id = Column(
        BigInteger,
        ForeignKey("telegram_users.user_id"),
        index=True,
    )

    @declared_attr
    def contest_id(cls):
        return Column(
            UUID(as_uuid=True),
            ForeignKey(f"{cls.__contest_model__.__tablename__}.id"),
            index=True,
        )

    @declared_attr
    def contest(cls):
        return relationship(
            cls.__contest_model__.__name__,
            backref="points"
        )
