from app.models.telegram_user import DonateStatus
from models.telegram_user import GlobalMarketingDonateStatus


def get_is_status_triumph(status: DonateStatus) -> bool:
    return status in (DonateStatus.BRILLIANT, )

def check_is_status_higher(
        obj_status: DonateStatus | GlobalMarketingDonateStatus | None,
        status: DonateStatus | GlobalMarketingDonateStatus,
) -> bool:
    return (
        obj_status is not None
        and obj_status.index < status.index
        and obj_status.__class__ is status.__class__
    )