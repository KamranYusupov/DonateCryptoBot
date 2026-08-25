import operator
from typing import Any

from app.models.telegram_user import DonateStatus, GlobalMarketingDonateStatus


def is_status_triumph(status: Any) -> bool:
    return status in (DonateStatus.BRILLIANT, )

def is_status_higher(
        first_status: DonateStatus | GlobalMarketingDonateStatus | None,
        second_status: DonateStatus | GlobalMarketingDonateStatus,
        *,
        or_equal: bool = False
) -> bool:
    if first_status is None:
        return True

    operation = operator.le if or_equal else operator.lt
    return (
        first_status.__class__ is second_status.__class__
        and operation(first_status.index, second_status.index)
    )