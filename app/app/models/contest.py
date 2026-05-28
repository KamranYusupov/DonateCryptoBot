import enum

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
    Date,
    text,
)

from app.db.base import Base
from app.models.mixins import TimestampedMixin, UUIDMixin, AbstractContest, AbstractContestPoint


class SponsorsContest(Base, AbstractContest, UUIDMixin):
    __tablename__ = "sponsors_contests"


class SponsorsContestPoint(Base, TimestampedMixin, UUIDMixin):

    __tablename__ = "sponsors_contest_points"

    user_id = Column(
        BigInteger,
        ForeignKey("telegram_users.user_id"),
        index=True,
    )
    contest_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sponsors_contests.id"),
        index=True,
    )

    contest = relationship(
        "SponsorsContest",
        remote_side="SponsorsContest.id",
        backref="points"
    )



