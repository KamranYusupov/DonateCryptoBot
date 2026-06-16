import enum
import random
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict

from app.core.config import settings
from app.models.telegram_user import DonateStatus

class BaseUserEntity(BaseModel):
    """Модель пользователя"""

    user_id: int = Field(title="ID пользователя")
    username: str | None = Field(title="Username", default=None)
    first_name: str | None = Field(title="Имя", default=None)
    last_name: str | None = Field(title="Фамилия", default=None)
    sponsor_user_id: int | None = Field(title="ID спонсора", default=None)
    status: DonateStatus | str = Field(
        title="Статус", default=DonateStatus.NOT_ACTIVE
    )
    invites_count: int = Field(title="Число приглашений", default=0)
    donates_sum: Decimal = Field(title="Сумма донатов", default=0)
    bill_for_activation: Decimal = Field(title="Счет для активации", default=0)
    bill_for_withdraw: Decimal = Field(title="Счет для вывода", default=0)
    is_bot: bool = Field(title="Бот", default=False)
    is_admin: bool = Field(title="Супер пользователь", default=False)
    depth_level: int = Field(title="Уровень глубины")
    is_banned: bool = Field(title="Заблокирован", default=False)
    captcha_verified: bool = Field(title="Пройдена Captcha", default=False)
    is_donate_for_registration_sent: bool = Field(
        title="Отправлен донат пригласителю за регистрацию",
        default=False,
    )

    @property
    def full_username(self) -> str:
        return f"@{self.username}" if self.username else ""

class TelegramUserEntity(BaseUserEntity):
    model_config = ConfigDict(from_attributes=True)


def generate_random_user():
    return TelegramUserEntity(
        user_id=random.randint(1, 100000000),
        username=f"user_{random.randint(1, 100000000)}",
        first_name=f"User{random.randint(1, 100)}",
        last_name=f"LastName{random.randint(1, 100)}",
        depth_level=0,
    )

