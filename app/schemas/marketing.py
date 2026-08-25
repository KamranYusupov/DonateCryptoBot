from typing import Literal, Annotated, ClassVar, TypeVar, Optional, Type

from pydantic import BaseModel, Field

from app.models.matrix import MatrixMarketingType, Matrix
from app.models.telegram_user import (
    DonateStatus,
    GlobalMarketingDonateStatus, TelegramUser,
)
from app.core.config import (
    GlobalMarketingConfig,
    StartMarketingConfig,
    settings,
)


class StartMarketingScope(BaseModel):
    marketing_type: Literal[MatrixMarketingType.START] = MatrixMarketingType.START
    status: Optional[DonateStatus]

    status_orm_attr: ClassVar[str] = "status"
    user_safe_orm_attr: ClassVar[str] = "triumph_bill"
    config: ClassVar[StartMarketingConfig] = settings.start_marketing

class GlobalMarketingScope(BaseModel):
    marketing_type: Literal[MatrixMarketingType.GLOBAL] = MatrixMarketingType.GLOBAL
    status: Optional[GlobalMarketingDonateStatus]

    status_orm_attr: ClassVar[str] = "global_marketing_status"
    user_safe_orm_attr: ClassVar[str] = "global_safe"
    config: ClassVar[GlobalMarketingConfig] = settings.global_marketing


MatrixMarketingScope = Annotated[
    StartMarketingScope | GlobalMarketingScope,
    Field(discriminator="marketing_type"),
]

MARKETING_SCOPE_BY_TYPE = {
    MatrixMarketingType.START: StartMarketingScope,
    MatrixMarketingType.GLOBAL: GlobalMarketingScope,
}

MarketingModel = TelegramUser | Matrix

def create_marketing_scope(
        marketing_type: MatrixMarketingType,
        marketing_orm_obj: Optional[MarketingModel] = None,
        status: Optional[DonateStatus | GlobalMarketingDonateStatus] = None,
) -> MatrixMarketingScope:
    scope_class = MARKETING_SCOPE_BY_TYPE[marketing_type]

    if status is None and marketing_orm_obj is None:
        raise ValueError("status or marketing_orm_obj must be provided")

    if status is not None and marketing_orm_obj is not None:
        raise ValueError(
            "Only one of status or marketing_orm_obj must be provided"
        )

    if status is None:
        status = getattr(marketing_orm_obj, scope_class.status_orm_attr)
        return scope_class(status=status)

    if not isinstance(status, marketing_type.status_enum):
        raise ValueError(
            f"\"{status.name}\" is not bound to "
            f"marketing type status enum \"{marketing_type.status_enum.__name__}\""
        )

    return scope_class(status=status)