import uuid
import enum

from sqlalchemy import (
    Column,
    DateTime,
    BigInteger,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy_json import mutable_json_type

from app.models.mixins import UUIDMixin, TimestampedMixin
from app.db.base import Base


class ProcessedCryptoBotPaymentWebhook(UUIDMixin, TimestampedMixin, Base):
    __tablename__ = "processed_crypto_bot_payment_webhooks"

    update_id = Column(BigInteger, unique=True, index=True)
    update_type = Column(String(50), nullable=False)
    request_date = Column(DateTime(timezone=True), nullable=False)
    payload = Column(mutable_json_type(dbtype=JSONB, nested=True), nullable=False)