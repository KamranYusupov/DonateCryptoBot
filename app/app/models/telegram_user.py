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
from app.models.mixins import TimestampedMixin, UUIDMixin, AbstractTelegramUser

class BillType(enum.Enum):
    ACTIVATION = "activation"
    WITHDRAW = "withdraw"
    TRIUMPH = "triumph"


class DonateStatus(enum.Enum):
    NOT_ACTIVE = "не активирован"
    TEST = "Тест"
    BASE = "Старт"
    BRONZE = "Бронза"
    SILVER = "Серебро"
    GOLD = "Золото"
    PLATINUM = "Платина"
    BRILLIANT = "Триумф"

    @classmethod
    def get_donations_data(cls):
        return {
            cls.TEST: Decimal("10"),
            cls.BASE: Decimal("25"),
            cls.BRONZE: Decimal("50"),
            cls.SILVER: Decimal("100"),
            cls.GOLD: Decimal("250"),
            cls.PLATINUM: Decimal("500"),
            cls.BRILLIANT: Decimal("1000"),
        }

    def get_status_donate_value(
            self,
    ) -> Decimal:
        """Получение суммы доната"""
        return self.get_donations_data().get(self, Decimal("0"))

    @classmethod
    def get_status_list(cls) -> list:
        return [
            cls.TEST,
            cls.BASE,
            cls.BRONZE,
            cls.SILVER,
            cls.GOLD,
            cls.PLATINUM,
            cls.BRILLIANT,
        ]


status_list = DonateStatus.get_status_list()
status_emoji_list = [
    "1️⃣" ,
    "2️⃣" ,
    "3️⃣" ,
    "4️⃣" ,
    "5️⃣" ,
    "6️⃣" ,
    "7️⃣" ,
]
statuses_colors_data = {
    DonateStatus.TEST: "🔘",
    DonateStatus.BASE: "🟢",
    DonateStatus.BRONZE : "🟠",
    DonateStatus.SILVER: "⚪",
    DonateStatus.GOLD: "🟡",
    DonateStatus.PLATINUM: "⚫",
    DonateStatus.BRILLIANT: "🏆",
}

class TelegramUser(UUIDMixin, TimestampedMixin, AbstractTelegramUser, Base):
    """Модель телеграм пользователя"""

    __tablename__ = "telegram_users"

    status = Column(Enum(DonateStatus), default=DonateStatus.NOT_ACTIVE)
    sponsor_user_id = Column(
        BigInteger,
        ForeignKey("telegram_users.user_id"),
        nullable=True,
        index=True,
    )
    invites_count = Column(Integer, default=0)
    donates_sum = Column(Numeric(18, 6, asdecimal=True), default=Decimal("0.0"))
    bill_for_activation = Column(Numeric(18, 6, asdecimal=True), default=Decimal("0.0"))
    bill_for_withdraw = Column(Numeric(18, 6, asdecimal=True), default=Decimal("0.0"))
    triumph_bill = Column(
        Numeric(18, 6, asdecimal=True),
        default=Decimal("0.0"),
        server_default=text("0.0"),
        nullable=False
    )
    is_admin = Column(Boolean, index=True, default=False)
    wallet_address = Column(String, nullable=True)
    depth_level = Column(Integer, default=0)
    is_banned = Column(Boolean, default=False)
    is_bot = Column(Boolean, default=False)
    captcha_verified = Column(Boolean, default=False)
    is_donate_for_registration_sent = Column(Boolean, default=False)

    sponsor = relationship(
        "TelegramUser",
        remote_side="TelegramUser.user_id",
        backref="invited_users"
    )
    sent_transfers = relationship(
        "Transfer",
        foreign_keys="[Transfer.from_id]",
        back_populates="sender",
        cascade="all, delete-orphan",
    )
    received_transfers = relationship(
        "Transfer",
        foreign_keys="[Transfer.to_id]",
        back_populates="receiver",
        cascade="all, delete-orphan",
    )


    __table_args__ = (
        UniqueConstraint("user_id", name="unique_user_id"),
        {"extend_existing": True},
    )

    def __repr__(self) -> str:
        return (
            self.username if self.username
            else f"Пользователь: {self.user_id}"
        )

    @staticmethod
    def get_bill_field_by_type(bill_type: BillType) -> str:
        if bill_type == BillType.TRIUMPH:
            return "triumph_bill"

        elif bill_type in (BillType.WITHDRAW, BillType.ACTIVATION):
            return f"bill_for_{bill_type.value.lower()}"

        else:
            raise ValueError(f"Unsupported bill_type: {bill_type}")

    def get_bill_by_type(self, bill_type) -> Decimal:
        bill_field_name = self.get_bill_field_by_type(bill_type)
        return getattr(self, bill_field_name)

    @classmethod
    def get_bill_column_by_type(
            cls,
            bill_type: BillType,
    ) -> InstrumentedAttribute:
        if bill_type == BillType.TRIUMPH:
            return cls.triumph_bill

        elif bill_type == BillType.WITHDRAW:
            return cls.bill_for_withdraw

        elif bill_type == BillType.ACTIVATION:
            return cls.bill_for_activation

        raise ValueError(f"Unsupported bill_type: {bill_type}")
