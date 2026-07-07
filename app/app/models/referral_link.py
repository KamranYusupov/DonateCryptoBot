from sqlalchemy import (
    Column,
    Boolean,
    ForeignKey,
    UUID,
    Index,
    UniqueConstraint,
)

from app.db.base import Base
from app.models.mixins import TimestampedMixin, UUIDMixin


class ReferralLink(UUIDMixin, TimestampedMixin, Base):
    """Модель реферальной ссылки"""

    __tablename__ = "referral_links"

    telegram_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_users.id"),
    )
    is_active = Column(
        Boolean,
        default=True,
    )

    __table_args__ = (
        Index("idx_active_user_link", telegram_user_id, is_active),
        UniqueConstraint("telegram_user_id", "is_active"),
    )
