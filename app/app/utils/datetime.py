from datetime import date, timedelta, datetime, UTC, timezone

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
    now = to_main_tz(dt_now or datetime.now())

    current_week_saturday = now - timedelta(days=(now.weekday() - 5))
    current_saturday_noon = current_week_saturday.replace(
        hour=12, minute=0, second=0, microsecond=0
    )

    if now < current_saturday_noon:
        target_dt = current_saturday_noon - timedelta(days=7)
    else:
        target_dt = current_saturday_noon

    return target_dt


