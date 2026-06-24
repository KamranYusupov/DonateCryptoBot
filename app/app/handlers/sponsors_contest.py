from aiogram.types import CallbackQuery
from dependency_injector.wiring import inject, Provide
from aiogram import Router, F

from app.core.config import settings
from app.core.container import Container
from app.use_cases import SponsorsContestUseCase


sponsors_contest_router = Router()
contest_callback_prefix = settings.sponsors_contest_callback_prefix
archived_contest_callback_prefix = f"archive_{contest_callback_prefix}"

@sponsors_contest_router.callback_query(
    F.data.startswith(contest_callback_prefix)
)
@inject
async def contest_callback_1handler(
        callback: CallbackQuery,
        use_case: SponsorsContestUseCase = Provide[
            Container.sponsors_contest_use_case,
        ]
) -> None:
    return await use_case.current_contest_callback_handler(
        callback=callback,
    )


@sponsors_contest_router.callback_query(
    F.data.startswith(archived_contest_callback_prefix)
)
@inject
async def archived_contest_callback_1handler(
        callback: CallbackQuery,
        use_case: SponsorsContestUseCase = Provide[
            Container.sponsors_contest_use_case,
        ]
) -> None:
    return await use_case.archive_contest_callback_handler(
        callback=callback,
    )