from datetime import datetime
from decimal import Decimal
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict

from app.models import TriumphBillTransactionType


class TriumphBillTransactionBaseSchema(BaseModel):
    amount: Decimal
    type_: TriumphBillTransactionType


class CreateTriumphBillTransactionSchema(TriumphBillTransactionBaseSchema):
    telegram_user_id: uuid.UUID


class TriumphBillTransactionMessageSchema(TriumphBillTransactionBaseSchema):
    id: uuid.UUID
    telegram_user_username: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

