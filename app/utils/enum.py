import enum
from typing import Type, TypeVar, Sequence

from app.models.telegram_user import DonateStatus, GlobalMarketingDonateStatus


EnumT = TypeVar("EnumT", bound=enum.Enum)


def get_enum_type_by_obj(
        enum_obj: EnumT,
        enums_types: Sequence[Type[EnumT]] | None = None
) -> Type[EnumT] | None:
    if enums_types is None:
        enums_types = (DonateStatus, GlobalMarketingDonateStatus)

    for enum_type in enums_types:
        if enum_obj in list(enum_type):
            return enum_type

    return None
