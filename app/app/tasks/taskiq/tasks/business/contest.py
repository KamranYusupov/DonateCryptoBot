from app.core.config import settings
from app.core.taskiq import broker

from app.db.commit_decorator import commit_and_close_session
from app.tasks.taskiq.dependencies.container import ContainerDependency


@broker.task(
    name="Update Sponsors Contest",
    schedule=[{
        "cron": \
             f"*/{settings.update_sponsors_contest_task_cron_minutes} * * * *",
    }]
)
@commit_and_close_session
async def update_sponsors_contest_task(
    container: ContainerDependency,
) -> None:
    sponsors_contests_service = container.sponsors_contests_service()
    await sponsors_contests_service.process_periodic_update()


@broker.task(
    name="Update Registration Contest",
    schedule=[{
        "cron": \
             f"*/{settings.update_registration_contest_task_cron_minutes} * * * *",
    }]
)
@commit_and_close_session
async def update_registration_contest_task(
    container: ContainerDependency,
) -> None:
    registration_contests_service = container.registration_contests_service()
    await registration_contests_service.process_periodic_update()
