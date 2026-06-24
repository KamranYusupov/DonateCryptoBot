from taskiq import TaskiqDepends

from app.core.config import settings
from app.core.taskiq import broker
from app.db.commit_decorator import commit_and_close_session
from app.tasks.taskiq.dependencies.container import ContainerDependency


@broker.task(name="Increase Triumph bills")
@commit_and_close_session
async def increase_triumph_bills_task(
        *,
        container: ContainerDependency,
) -> None:
    triumph_bill_service = container.triumph_bill_service()
    await triumph_bill_service.increase_bills_by_percent(
        percent=settings.triumph_bill_increase_percent,
    )
