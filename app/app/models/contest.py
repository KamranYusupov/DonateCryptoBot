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
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import relationship

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


class RegistrationContestPoint(Base,
    AbstractContestPoint[RegistrationContest],
    TimestampedMixin,
    UUIDMixin
):
    __tablename__ = "registration_contest_points"

