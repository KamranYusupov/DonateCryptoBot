from typing import Literal, Annotated, ClassVar

from pydantic import BaseModel, Field

from app.models.matrix import MatrixMarketingType
from app.models.telegram_user import (
    DonateStatus,
    GlobalMarketingDonateStatus,
)
from app.core.config import (
    GlobalMarketingConfig,
    StartMarketingConfig,
    settings,
)


class StartMarketingScope(BaseModel):
    marketing_type: Literal[MatrixMarketingType.START] = MatrixMarketingType.START
    status: DonateStatus

    status_orm_attr: ClassVar[str] = "status"
    config: ClassVar[StartMarketingConfig] = settings.start_marketing

class GlobalMarketingScope(BaseModel):
    marketing_type: Literal[MatrixMarketingType.GLOBAL] = MatrixMarketingType.GLOBAL
    status: GlobalMarketingDonateStatus

    status_orm_attr: ClassVar[str] = "global_status"
    config: ClassVar[GlobalMarketingConfig] = settings.global_marketing


MatrixMarketingScope = Annotated[
    StartMarketingScope | GlobalMarketingScope,
    Field(discriminator="marketing_type"),
]