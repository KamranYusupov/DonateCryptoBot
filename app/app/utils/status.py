from app.models.telegram_user import DonateStatus


def get_is_status_triumph(status: DonateStatus) -> bool:
    return status in (DonateStatus.BRILLIANT, )