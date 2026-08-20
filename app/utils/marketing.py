from typing import Type

from app.models.telegram_user import (
    GlobalMarketingDonateStatus,
    DonateStatus,
)


def get_status_list_by_status(
        status: DonateStatus | None,
        global_marketing_donate_status: GlobalMarketingDonateStatus | None,
) -> Type[DonateStatus | GlobalMarketingDonateStatus]:
    if status is not None and global_marketing_donate_status is not None:
        raise ValueError("One status argument should be None")

    if status is None and global_marketing_donate_status is None:
        raise ValueError("One status argument should not be None")

    if status is not None:
        return DonateStatus

    if global_marketing_donate_status is not None:
        return GlobalMarketingDonateStatus