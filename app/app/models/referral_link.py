from urllib.parse import urljoin

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
        Index(
            "idx_unique_active_link_per_user",
            telegram_user_id,
            unique=True,
            postgresql_where=(is_active == True)
        ),
    )

    @property
    def url(self) -> str:
        return urljoin(
            base=settings.bot_link.format(bot_name=settings.bot_name),
            url=f"?start={self.id}",
        )

