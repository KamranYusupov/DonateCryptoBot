import enum
import uuid
from decimal import Decimal

from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    Enum,
    UUID,
    Numeric,
)
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.mixins import TimestampedMixin, UUIDMixin, AbstractTelegramUser


class Donate(UUIDMixin, TimestampedMixin, Base):
    """Модель доната"""

    __tablename__ = "donates"

    telegram_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_users.id"),
        default=None,
        index=True,
    )
    quantity = Column(
        Numeric(18, 6, asdecimal=True),
        default=Decimal("0.0")
    )
    matrix_id = Column(
        UUID(as_uuid=True),
        ForeignKey("matrices.id"),
        default=None,
        index=True,
    )

    telegram_user = relationship(
        "TelegramUser",
        backref="donates",
    )
    matrix = relationship(
        "Matrix",
        backref="donates",
    )

    __table_args__ = {"extend_existing": True}


class DonateTransactionType(enum.Enum):
    SYSTEM = "system"
    SPONSOR = "sponsor"
    MATRIX = "matrix"


class DonateTransaction(UUIDMixin, TimestampedMixin, Base):
    """Модель подтверждения получения доната спонсором"""

    __tablename__ = "donate_transactions"

    sponsor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_users.id"),
        default=None,
        index=True,
    )
    donate_id = Column(
        UUID(as_uuid=True),
        ForeignKey("donates.id"),
        default=None,
        index=True,
    )
    quantity = Column(
        Numeric(18, 6, asdecimal=True),
        default=Decimal("0.0")
    )
    type_ = Column(Enum(DonateTransactionType, name="donate_transaction_enum"))
    sponsor_depth = Column(
        Integer,
        default=None,
        server_default=None,
    )

    donate = relationship(
        "Donate",
        backref="transactions"
    )

    __table_args__ = {"extend_existing": True}
