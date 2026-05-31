import uuid
from typing import Any, Callable, Optional
from aiogram import F, Router
from aiogram.types import CallbackQuery
from dependency_injector.wiring import Provide, inject

from app.core.config import settings
from app.core.container import Container
from app.keyboards.donate import get_donate_keyboard
from app.services.registration_contest_service import RegistrationContestService
from app.services.sponsors_contest_service import SponsorsContestService
from app.utils.pagination import Paginator, get_pagination_buttons
from app.utils.texts import get_period_message, get_contest_top_10_rating_message


class ContestCallbackController:
    def __init__(
            self,
            prefix: str,
            service: Any,
            results_text_formatter: Callable,
            archive_prefix: Optional[str] = None,
            period_days: int = 7,
            title: str = "🏆 Топ‑10",
    ):
        self.prefix = prefix
        self.service = service
        self.results_text_formatter = results_text_formatter
        self.period_days = period_days
        self.title = title

        if not archive_prefix:
            archive_prefix = f"archive_{prefix}"

        self.archive_prefix = archive_prefix

    async def current_contest_callback_handler(self, callback: CallbackQuery) -> None:
        buttons = {}
        sizes = tuple()

        try:
            previous_page_number, detail_page_number = map(
                int, callback.data.split("_")[-2:]
            )
            contests_ids = await self.service.get_ids(is_archived=True)

            paginator = Paginator(
                contests_ids,
                page_number=detail_page_number,
                per_page=1
            )
            contest_id = paginator.get_page()[0]
            contest = await self.service.get_contest(id=contest_id)

            pagination_buttons = get_pagination_buttons(
                paginator,
                f"{self.prefix}_{previous_page_number}",
            )
            buttons.update(pagination_buttons)
            if pagination_buttons:
                sizes += (len(pagination_buttons),)

            buttons["🔙 Назад"] = f"{self.archive_prefix}_{previous_page_number}"
            sizes += (1,)

            telegram_method = callback.message.edit_text

        except ValueError:
            contest, _ = await self.service.get_or_create_current_contest()
            archive_exists = await self.service.contest_exists(is_archived=True)
            if archive_exists:
                buttons.update({"АРХИВ 🗄": f"{self.archive_prefix}_1"})

            telegram_method = callback.message.answer
            await callback.message.delete()

        message_text = self.results_text_formatter(
            top_10_rating=contest.top_10_rating,
            start_date=contest.start_date,
            prize_fund=contest.prize_fund,
        )

        await telegram_method(
            text=message_text,
            reply_markup=get_donate_keyboard(
                buttons=buttons,
                sizes=sizes,
            ),
        )

    async def archive_contest_callback_handler(self, callback: CallbackQuery) -> None:
        callback_data = callback.data.split("_")
        base_callback_data = "_".join(callback_data[0:-1])
        page_number = int(callback_data[-1])
        per_page = 10
        default_buttons = {"🔙 Назад": self.prefix}
        buttons = {}
        sizes = tuple()

        contests = await self.service.get_contests_list(is_archived=True)
        paginator = Paginator(
            contests,
            page_number=page_number,
            per_page=per_page
        )
        page = paginator.get_page()

        if not page:
            buttons.update(default_buttons)
            sizes += (1,) * len(buttons)
            await callback.message.edit_text(
                "Список пуст.",
                reply_markup=get_donate_keyboard(buttons=buttons, sizes=sizes)
            )
            return

        detail_page_number = contests.index(page[0])
        for contest in page:
            button_text = get_period_message(
                contest.start_date,
                period_days=self.period_days
            )
            detail_page_number += 1
            buttons[button_text] = f"{self.prefix}_{page_number}_{detail_page_number}"

        sizes += (1,) * len(page)

        pagination_buttons = get_pagination_buttons(paginator, base_callback_data)
        buttons.update(pagination_buttons)
        if pagination_buttons:
            sizes += (len(pagination_buttons),)

        buttons.update(default_buttons)
        sizes += (1,) * len(default_buttons)

        await callback.message.edit_text(
            "Выберите конкурс.",
            reply_markup=get_donate_keyboard(buttons=buttons, sizes=sizes),
        )

    def register_to_router(self, router: Router) -> None:
        """Регистрирует методы класса в переданный aiogram роутер."""

        router.callback_query.register(
            self.current_contest_callback_handler,
            F.data.startswith(f"{self.prefix}_")
        )
        router.callback_query.register(
            self.current_contest_callback_handler,
            F.data == self.prefix
        )
        router.callback_query.register(
            self.archive_contest_callback_handler,
            F.data.startswith(f"{self.archive_prefix}_")
        )


@inject
def get_router(
    sponsors_contests_service: SponsorsContestService = Provide[
        Container.sponsors_contests_service
    ],
    registration_contests_service: RegistrationContestService = Provide[
        Container.registration_contests_service
    ],

) -> Router:
    router = Router()

    sponsors_contest_controller = ContestCallbackController(
        title="🏆 Топ‑10 кураторов",
        prefix=settings.sponsors_contest_callback_prefix,
        service=sponsors_contests_service,
        results_text_formatter=get_contest_top_10_rating_message
    )
    registration_contest_controller = ContestCallbackController(
        title="🏆 Топ‑10 пригласителей",
        prefix=settings.registration_contest_callback_prefix,
        service=registration_contests_service,
        results_text_formatter=get_contest_top_10_rating_message
    )

    sponsors_contest_controller.register_to_router(router)
    registration_contest_controller.register_to_router(router)

    return router
