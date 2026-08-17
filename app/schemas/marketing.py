from typing import Optional, Literal, Annotated

from pydantic import BaseModel, Field, model_validator

from app.models.matrix import MatrixEngineType, MatrixMarketingType
from app.models.telegram_user import (
    DonateStatus,
    GlobalMarketingDonateStatus,
)


class StartMarketingScope(BaseModel):
    marketing_type: Literal[MatrixMarketingType.START] = MatrixMarketingType.START
    status: DonateStatus


class GlobalMarketingScope(BaseModel):
    marketing_type: Literal[MatrixMarketingType.GLOBAL] = MatrixMarketingType.GLOBAL
    status: GlobalMarketingDonateStatus


MatrixMarketingScope = Annotated[
    StartMarketingScope | GlobalMarketingScope,
    Field(discriminator="marketing_type"),
]