import uuid
import enum

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
    text,

)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import relationship
from sqlalchemy_json import mutable_json_type

from app.models.mixins import UUIDMixin, TimestampedMixin
from app.db.base import Base
from app.models.telegram_user import DonateStatus


class MatrixEngineType(enum.Enum):
    JSON = "legacy_json"
    NODES = "nodes"

class Matrix(UUIDMixin, TimestampedMixin, Base):
    __tablename__ = "matrices"

    owner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_users.id"),
        default=uuid.uuid4,
        index=True,
    )
    status = Column(Enum(DonateStatus), default=DonateStatus.NOT_ACTIVE, index=True)
    engine_type = Column(
        Enum(MatrixEngineType),
        nullable=False,
        default=MatrixEngineType.JSON,
        server_default=text("'JSON'"),
        index=True,
    )
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

    __table_args__ = {"extend_existing": True}


class MatrixNode(UUIDMixin, TimestampedMixin, Base):
    __tablename__ = "matrix_nodes"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    matrix_id = Column(
        UUID(as_uuid=True),
        ForeignKey("matrices.id", ondelete="CASCADE"),
        nullable=False,
    )
    telegram_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_users.id"),
        nullable=False,
    )
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("matrix_nodes.id", ondelete="CASCADE"),
        nullable=True,
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
    is_full = Column(
        Boolean,
        default=False,
        index=True,
    )

    matrix = relationship(
        "Matrix",
        foreign_keys=[matrix_id],
        back_populates="nodes",
    )
    parent = relationship(
        "MatrixNode",
        remote_side=[id],
        backref="children",
        foreign_keys=[parent_id],
    )
    telegram_user = relationship(
        "TelegramUser",
        foreign_keys=[telegram_user_id],
    )

    __table_args__ = (
        Index("idx_matrix_free", matrix_id, is_full, level, position),
        Index("idx_user_matrix", telegram_user_id, matrix_id),
    )


class AddBotToMatrixTaskModel(UUIDMixin, TimestampedMixin, Base):
    __tablename__ = "add_to_matrix_tasks"

    execute_at = Column(DateTime, index=True)
    is_executed = Column(Boolean, default=False, index=True)

    donate_sum = Column(Integer)
    matrix_id = Column(
        UUID(as_uuid=True),
        ForeignKey("matrices.id"),
        index=True,
    )

    __table_args__ = {"extend_existing": True}



