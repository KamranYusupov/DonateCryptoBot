from aiogram.types import CallbackQuery
from dependency_injector.wiring import inject, Provide

from app.core.config import settings
from app.core.container import Container
from app.use_cases import RegistrationContestUseCase

from aiogram import Router, F

registration_contest_router = Router()
contest_callback_prefix = settings.registration_contest_callback_prefix
archived_contest_callback_prefix = f"archive_{contest_callback_prefix}"

@registration_contest_router.callback_query(
    F.data.startswith(contest_callback_prefix)
)
@inject
async def contest_callback_handler(
        callback: CallbackQuery,
        use_case: RegistrationContestUseCase = Provide[
            Container.registration_contest_use_case,
        ]
) -> None:
    return await use_case.current_contest_callback_handler(
        callback=callback,
    )


@registration_contest_router.callback_query(
    F.data.startswith(archived_contest_callback_prefix)
)
@inject
async def archived_contest_callback_handler(
        callback: CallbackQuery,
        use_case: RegistrationContestUseCase = Provide[
            Container.registration_contest_use_case,
        ]
) -> None:
    return await use_case.archive_contest_callback_handler(
        callback=callback,
    )