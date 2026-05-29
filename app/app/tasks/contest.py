from dependency_injector.wiring import inject, Provide

from app.core.container import Container
from app.db.commit_decorator import commit_and_close_session
from app.services.sponsors_contest_service import SponsorsContestService
from app.services.registration_contest_service import RegistrationContestService


@inject
@commit_and_close_session
async def update_sponsors_contest_task(
    sponsors_contests_service: SponsorsContestService = Provide[
        Container.sponsors_contests_service
    ],
) -> None:
    await sponsors_contests_service.process_periodic_update()


@inject
@commit_and_close_session
async def update_registration_contest_task(
    registration_contests_service: RegistrationContestService = Provide[
        Container.registration_contests_service
    ],
) -> None:
    await registration_contests_service.process_periodic_update()