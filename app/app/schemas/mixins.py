import datetime

from pydantic import BaseModel
import uuid


class UUIDSchemaMixin(BaseModel):
    id: uuid.UUID


class TimestampSchemaMixin(BaseModel):
    created_at: datetime.datetime
    updated_at: datetime.datetime

