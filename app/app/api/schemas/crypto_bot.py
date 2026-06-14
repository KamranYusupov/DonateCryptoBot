from decimal import Decimal
from pydantic import BaseModel, field_validator
from typing import Optional, Any, Dict
from datetime import datetime


class UpdateWebhookSchema(BaseModel):
    update_id: int
    update_type: str
    request_date: datetime

    payload: dict

class InvoicePayloadSchema(BaseModel):
    telegram_id: int
    tokens_count: int
    messages_to_delete_ids: list[int]

class CryptoInvoiceSchema(BaseModel):
    invoice_id: int
    hash: str

    currency_type: str
    asset: str

    amount: Decimal
    paid_asset: str
    paid_amount: Decimal

    description: str
    status: str

    created_at: datetime
    paid_at: datetime

    paid_usd_rate: Decimal
    usd_rate: Decimal

    payload: InvoicePayloadSchema

    @field_validator('payload', mode='before')
    @classmethod
    def ensure_list(cls, value: Any) -> InvoicePayloadSchema:
        if isinstance(value, str):
            return InvoicePayloadSchema.model_validate_json(value)
        return InvoicePayloadSchema.model_validate(value)
