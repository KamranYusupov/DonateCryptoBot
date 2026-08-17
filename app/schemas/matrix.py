import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.models.matrix import MatrixEngineType, MatrixMarketingType
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
    global_marketing_status: GlobalMarketingDonateStatus | None = Field(
        title="Статус доната Global маркетинга",
        default=None
    )
    marketing_type: MatrixMarketingType = MatrixMarketingType.START
    engine_type: MatrixEngineType = MatrixEngineType.JSON
    root_node_id: Optional[uuid.UUID] = None

    @model_validator(mode="after")
    def validate_marketing_status(self) -> "MatrixEntity":
        if self.marketing_type is MatrixMarketingType.START:
            if self.status is None:
                raise ValueError(
                    "START matrix requires status"
                )
            if self.global_marketing_status is not None:
                raise ValueError(
                    "START matrix cannot have global_marketing_status"
                )

        elif self.marketing_type is MatrixMarketingType.GLOBAL:
            if self.global_marketing_status is None:
                raise ValueError(
                    "GLOBAL matrix requires global_marketing_status"
                )
            if self.status is not None:
                raise ValueError(
                    "GLOBAL matrix cannot have status"
                )

        return self

    @classmethod
    def from_marketing_scope(
            cls,
            owner_id: uuid.UUID,
            marketing_scope: MatrixMarketingScope,
            engine_type: MatrixEngineType,
            root_node_id: uuid.UUID | None = None,
    ) -> "MatrixEntity":
        if marketing_scope.marketing_type is MatrixMarketingType.START:
            return cls(
                owner_id=owner_id,
                marketing_type=marketing_scope.marketing_type,
                status=marketing_scope.status,
                global_marketing_status=None,
                engine_type=engine_type,
                root_node_id=root_node_id,
            )

        return cls(
            owner_id=owner_id,
            marketing_type=marketing_scope.marketing_type,
            status=None,
            global_marketing_status=marketing_scope.status,
            engine_type=engine_type,
            root_node_id=root_node_id,
        )


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