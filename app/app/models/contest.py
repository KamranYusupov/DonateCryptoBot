import enum
from decimal import Decimal

from sqlalchemy import (
    Column,
    Numeric,
)
from sqlalchemy.sql import func, text

from app.db.base import Base
from app.models.mixins import TimestampedMixin, UUIDMixin, AbstractContest, AbstractContestPoint


class SponsorsContest(Base, AbstractContest, UUIDMixin):
    __tablename__ = "sponsors_contests"


class SponsorsContestPoint(
    Base,
    AbstractContestPoint[SponsorsContest],
    TimestampedMixin,
    UUIDMixin
):
    __tablename__ = "sponsors_contest_points"



class RegistrationContest(Base, AbstractContest, UUIDMixin):
    __tablename__ = "registration_contests"

    prize_fund = Column(Numeric(18, 6, asdecimal=True), default=Decimal("0.0"), server_default=text("0"))
    init_prize_fund = Column(Numeric(18, 6, asdecimal=True), default=Decimal("0.0"), server_default=text("0"))


class RegistrationContestPoint(Base,
    AbstractContestPoint[RegistrationContest],
    TimestampedMixin,
    UUIDMixin
):
    __tablename__ = "registration_contest_points"

