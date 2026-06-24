import enum
from decimal import Decimal

from sqlalchemy import Column, Enum, ForeignKey, Numeric, String, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.db.base import Base
from app.models.mixins import TimestampedMixin, UUIDMixin


class TriumphBillTransactionType(str, enum.Enum):
    INCREMENT = "increment"
    DECREMENT = "decrement"


class TriumphBillTransaction(Base, UUIDMixin, TimestampedMixin):
    __tablename__ = "triumph_bill_transactions"

    amount = Column(
        Numeric(18, 6, asdecimal=True),
        default=Decimal("0.0"),
        server_default=text("0.0"),
        nullable=False,
    )
    type_ = Column(
        Enum(TriumphBillTransactionType),
        nullable=False,
        index=True,
    )
    telegram_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_users.id"),
        default=None,
        index=True,
        nullable=False,
    )

    telegram_user = relationship(
        "TelegramUser",
        backref="triumph_bill_transactions",
    )
