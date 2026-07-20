import string
from urllib.parse import urljoin

from sqlalchemy import (
    Column,
    Boolean,
    ForeignKey,
    UUID,
    Index,
    String,
)
from nanoid import generate

from app.db.base import Base
from app.models.mixins import TimestampedMixin, UUIDMixin
from app.core.config import settings


def generate_nanoid():
    alphabet = (string.ascii_letters + string.digits + "-")
    return generate(
        size=10,
        alphabet=alphabet
    )


class ReferralLink(UUIDMixin, TimestampedMixin, Base):
    """Модель реферальной ссылки"""

    __tablename__ = "referral_links"

    code = Column(
        String(10),
        default=generate_nanoid,
        unique=True,
        index=True,
        nullable=False
    )
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
            url=f"?start={self.code}",
        )

