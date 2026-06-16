from dependency_injector.wiring import inject, Provide

from app.core.config import settings
from app.core.taskiq import broker
from app.core.container import Container
from app.db.commit_decorator import commit_and_close_session
from app.services import TriumphBillService


@broker.task(name="Increase Triumph bills Task")
@inject
@commit_and_close_session
async def increase_triumph_bills_task(
        triumph_bill_service: TriumphBillService = Provide[
            Container.triumph_bill_service
        ]
) -> None:
    await triumph_bill_service.increase_bills_by_percent(
        percent=settings.triumph_bill_increase_percent,
    )