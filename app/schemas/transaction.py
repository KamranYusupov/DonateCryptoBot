import uuid
from decimal import Decimal
from typing import Literal, Annotated, Union
from pydantic import BaseModel, Field, ConfigDict

from app.models.donate import DonateTransactionType
from app.models.telegram_user import DonateStatus, GlobalMarketingDonateStatus



class TransactionReceiverSchema(BaseModel):
    id: uuid.UUID
    chat_id: int = Field(alias="user_id")
    username: str
    is_banned: bool
    is_bot: bool

    @property
    def full_username(self) -> str:
        return f"@{self.username}" if self.username else ""

    model_config = ConfigDict(from_attributes=True)


class BaseTransactionContextSchema(BaseModel):
    receiver: TransactionReceiverSchema
    quantity: Decimal


class SystemTransactionContextSchema(BaseTransactionContextSchema):
    type_: Literal[DonateTransactionType.SYSTEM] = DonateTransactionType.SYSTEM


class SponsorTransactionContextSchema(BaseTransactionContextSchema):
    type_: Literal[DonateTransactionType.SPONSOR] = DonateTransactionType.SPONSOR
    sender_str: str
    status: DonateStatus | GlobalMarketingDonateStatus
    sponsor_depth: int


class MatrixTransactionContextSchema(BaseTransactionContextSchema):
    type_: Literal[DonateTransactionType.MATRIX] = DonateTransactionType.MATRIX
    status: DonateStatus | GlobalMarketingDonateStatus
    matrix_length: int
    matrix_max_length: int
    triumph: bool = False

DonateTransactionContextSchema = Annotated[
    Union[
        SystemTransactionContextSchema,
        SponsorTransactionContextSchema,
        MatrixTransactionContextSchema,
    ],
    Field(discriminator="type_")
]