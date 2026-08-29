import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, model_validator, ConfigDict

from app.models.matrix import MatrixEngineType, MatrixMarketingType, MatrixNode
from app.models.telegram_user import (
    DonateStatus,
    GlobalMarketingDonateStatus,
)
from app.schemas.marketing import MatrixMarketingScope


class MatrixEntity(BaseModel):
    """Модель пользователя"""

    owner_id: uuid.UUID = Field(title="ID владельца")
    status: DonateStatus | None = Field(
        title="Статус доната",
        default=None,
    )
    marketing_type: MatrixMarketingType = MatrixMarketingType.START
    engine_type: MatrixEngineType = MatrixEngineType.JSON
    root_node_id: Optional[uuid.UUID] = None


class MatrixNodeSchema(BaseModel):
    matrix_id: uuid.UUID
    owner_id: uuid.UUID
    level: int
    position: int
    children_count: int = 0
    marketing_type: MatrixMarketingType


class AddBotToMatrixTaskSchema(BaseModel):
    execute_at: datetime
    is_executed: bool = False
    donate_sum: Decimal
    engine_type: MatrixEngineType = MatrixEngineType.JSON
    obj_id: uuid.UUID # Matrix.id or MatrixNode.id
    create_donates: bool = True





