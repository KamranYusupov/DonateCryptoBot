from taskiq import TaskiqDepends

from app.db.commit_decorator import commit_and_close_session
from app.tasks.taskiq.dependencies.container import ContainerDependency


@commit_and_close_session
async def update_sponsors_contest_task(
    container: ContainerDependency,
) -> None:
    sponsors_contests_service = container.sponsors_contests_service()
    await sponsors_contests_service.process_periodic_update()


@commit_and_close_session
async def update_registration_contest_task(
    container: ContainerDependency,
) -> None:
    registration_contests_service = container.registration_contests_service()
    await registration_contests_service.process_periodic_update()
