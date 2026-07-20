import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.models.matrix import MatrixEngineType
from app.models.telegram_user import DonateStatus


class MatrixEntity(BaseModel):
    """Модель пользователя"""

    owner_id: uuid.UUID = Field(title="ID владельца")
    status: DonateStatus | str = Field(title="Статус доната")
    engine_type: MatrixEngineType = MatrixEngineType.JSON
    root_node_id: Optional[uuid.UUID] = None


class MatrixNodeSchema(BaseModel):
    matrix_id: uuid.UUID
    owner_id: uuid.UUID
    level: int
    position: int
    children_count: int = 0


class AddBotToMatrixTaskSchema(BaseModel):
    execute_at: datetime
    is_executed: bool = False
    donate_sum: Decimal
    engine_type: MatrixEngineType = MatrixEngineType.JSON
    obj_id: uuid.UUID # Matrix.id or MatrixNode.id
    create_donates: bool = True