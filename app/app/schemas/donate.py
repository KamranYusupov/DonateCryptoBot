import uuid

from pydantic import BaseModel, Field

from app.models.donate import DonateTransactionType
from app.schemas.mixins import UUIDSchemaMixin, TimestampSchemaMixin


class DonateEntity(BaseModel):
    """Представление модели Donate"""

    telegram_user_id: uuid.UUID = Field(title="ID пользователя")
    quantity: float = Field(title="Размер доната")
    matrix_id: uuid.UUID = Field(title="ID матрицы")


class BaseDonateTransactionSchema(BaseModel):
    sponsor_id: uuid.UUID = Field(title="ID спонсора")
    donate_id: uuid.UUID = Field(title="ID доната")
    quantity: float = Field(title="Размер доната")
    type_: DonateTransactionType


class CreateDonateTransactionSchema(BaseDonateTransactionSchema):
    pass


class DonateTransactionSchema(
    BaseDonateTransactionSchema,
    UUIDSchemaMixin,
    TimestampSchemaMixin,
):
    pass