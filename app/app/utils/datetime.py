from datetime import date, timedelta, datetime, UTC

from app.core.config import settings


def to_main_tz(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    return dt.astimezone(settings.timezone_info)


def get_start_of_week(day: date | None = None) -> date:
    day = day or to_main_tz(datetime.now()).date()
    return day - timedelta(days=day.weekday())


def get_saturday_noon_period_start(dt_now: datetime | None = None) -> datetime:
    """
    Получаем прошлую субботу 12:00,
    если сейчас раньше чем суббота 12:00 этой недели,
    или получаем текущую субботу в 12:00,
    если сейчас позднее субботы 12:00 текущей недели.
    """

    now = to_main_tz(dt_now or datetime.now()) + timedelta(days=7)

    is_before_saturday_noon = now.weekday() < 5 or (now.weekday() == 5 and now.hour < 12)

    if is_before_saturday_noon:
        days_to_subtract = now.weekday() + 2
    else:
        days_to_subtract = now.weekday() - 5

    target_date = now - timedelta(days=days_to_subtract)
    return target_date.replace(hour=12, minute=0, second=0, microsecond=0)


