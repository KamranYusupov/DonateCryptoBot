import enum
from decimal import Decimal

from sqlalchemy import (
    Column,
    Integer,
    Float,
    ForeignKey,
    Enum,
    UUID,
    Boolean,
    BigInteger,
    UniqueConstraint,
    String,
    Numeric,
)
from sqlalchemy.orm import relationship, InstrumentedAttribute
from sqlalchemy.sql import text

from app.db.base import Base
from app.models.mixins import (TimestampedMixin, UUIDMixin)


class TriumphBillIncrementTransaction(Base, UUIDMixin, TimestampedMixin):
    __tablename__ = "triumph_increment_transactions"

    amount = Column(
        Numeric(18, 6, asdecimal=True),
        default=Decimal("0.0"),
        server_default=text("0.0"),
        nullable=False
    )
    telegram_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_users.id"),
        default=None,
        index=True,
    )

    telegram_user = relationship(
        "TelegramUser",
        backref="triumph_increment_transactions",
    )

