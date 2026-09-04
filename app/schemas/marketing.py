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

def create_marketing_scope(
        marketing_type: MatrixMarketingType,
        telegram_user: Optional[TelegramUser] = None,
        status: Optional[DonateStatus | GlobalMarketingDonateStatus] = None,
) -> MatrixMarketingScope:

    if status is not None and telegram_user is not None:
        raise ValueError(
            "Only one of status or telegram_user must be provided"
        )

    scope_class = MARKETING_SCOPE_BY_TYPE[marketing_type]

    if status is None and telegram_user is None:
        return scope_class(status=status)

    if status is None:
        status = getattr(telegram_user, scope_class.status_orm_attr)
        return scope_class(status=status)

    if not isinstance(status, marketing_type.status_enum):
        raise ValueError(
            f"\"{status.name}\" is not bound to "
            f"marketing type status enum \"{marketing_type.status_enum.__name__}\""
        )

    return scope_class(status=status)