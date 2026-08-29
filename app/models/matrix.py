import uuid
import enum
from decimal import Decimal
from typing import Type

from sqlalchemy import (
    Column,
    UUID,
    ForeignKey,
    Enum,
    Boolean,
    Integer,
    DateTime,
    BigInteger,
    Index,
    UniqueConstraint,
    func,
    Numeric, CheckConstraint, ForeignKeyConstraint,
)
from sqlalchemy.sql import text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import relationship
from sqlalchemy_json import mutable_json_type

from app.models.mixins import UUIDMixin, TimestampedMixin
from app.db.base import Base
from app.models.telegram_user import DonateStatus, GlobalMarketingDonateStatus


class MatrixEngineType(enum.Enum):
    JSON = "legacy_json"
    NODES = "nodes"

class MatrixMarketingType(enum.Enum):
    START = ("start", "ТРИУМФ", DonateStatus)
    GLOBAL = ("global", "Прайм-Тайм", GlobalMarketingDonateStatus)

    def __init__(
            self,
            label: str,
            title: str,
            status_enum: Type[
                DonateStatus |
                GlobalMarketingDonateStatus
            ],
    ):
        self.label = label
        self.title = title
        self.status_enum = status_enum


class MatrixEngineTypeMixin:
    engine_type = Column(
        Enum(MatrixEngineType),
        nullable=False,
        default=MatrixEngineType.JSON,
        server_default=text("'JSON'"),
        index=True,
    )

class Matrix(Base, UUIDMixin, TimestampedMixin, MatrixEngineTypeMixin):
    __tablename__ = "matrices"

    owner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_users.id"),
        default=uuid.uuid4,
        index=True,
    )
    marketing_type = Column(
        Enum(MatrixMarketingType),
        nullable=False,
        default=MatrixMarketingType.START,
        index=True,
    )
    status = Column(Enum(DonateStatus), index=True)
    closed_places_count = Column(
        BigInteger,
        default=0,
    )

    # legacy json engine
    matrices = Column(mutable_json_type(dbtype=JSONB, nested=True), index=True, default=dict)
    telegram_users = Column(MutableList.as_mutable(JSONB), index=True, default=list)


    # new nodes engine
    root_node_id = Column(
        UUID(as_uuid=True),
        ForeignKey("matrix_nodes.id"),
        nullable=True,
    )
    is_closed = Column(
        Boolean,
        default=False,
        index=True,
    )

    nodes = relationship(
        "MatrixNode",
        foreign_keys="[MatrixNode.matrix_id]",
        back_populates="matrix",
        cascade="all, delete-orphan",
    )
    root_node = relationship(
        "MatrixNode",
        foreign_keys=[root_node_id],
        post_update=True,
    )

    __table_args__ = (
        UniqueConstraint("id", "marketing_type", name="uq_matrix_id_marketing_type"),

        Index(
            "ix_matrices_marketing_type_status",
            marketing_type,
            status,
        ),

        CheckConstraint(
            """
            (
                marketing_type = 'START'
                AND engine_type IN ('JSON', 'NODES')
                AND status IS NOT NULL            )
            OR
            (
                marketing_type = 'GLOBAL'
                AND engine_type = 'NODES'
                AND status IS NULL
            )
            """,
            name="ck_matrix_marketing_engine",
        ),
    )


class MatrixNode(UUIDMixin, TimestampedMixin, Base):
    __tablename__ = "matrix_nodes"


    owner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_users.id"),
        nullable=False,
    )

    matrix_id = Column(
        UUID(as_uuid=True),
        nullable=False,
    )
    marketing_type = Column(
        Enum(MatrixMarketingType),
        nullable=False,
        default=MatrixMarketingType.START,
        server_default=text("'START'"),
        index=True,
    )

    level = Column(
        Integer,
        nullable=False,
        index=True,
    )
    position = Column(
        BigInteger,
        nullable=False,
        index=True,
    )
    children_count = Column(
        BigInteger,
        default=0,
    )
    downline_count = Column(
        BigInteger,
        default=0,
    )
    last_activation = Column(
        DateTime,
        default=func.now(),
    )

    matrix = relationship(
        "Matrix",
        foreign_keys=[matrix_id],
        back_populates="nodes",
    )
    owner = relationship(
        "TelegramUser",
        foreign_keys=[owner_id],
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["matrix_id", "marketing_type"],
            ["matrices.id", "matrices.marketing_type"],
            ondelete="CASCADE",
        ),
        Index("idx_matrix_free", matrix_id, children_count, level, position),
        Index("idx_user_matrix", owner_id, matrix_id),
        UniqueConstraint("matrix_id", "position",),
    )
