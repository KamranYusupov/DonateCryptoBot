from typing import Callable, Optional, TypeVar, Type, Generic
from aiogram.types import CallbackQuery
from app.keyboards.donate import get_donate_keyboard
from app.utils.pagination import Paginator, get_pagination_buttons
from app.utils.texts import get_period_message, get_contest_top_10_rating_message

ContestServiceType = TypeVar("ContestServiceType")


class BaseContestUseCase(Generic[ContestServiceType,]):
    def __init__(
            self,
            prefix: str,
            service: Type[ContestServiceType],
            results_text_formatter: Callable = get_contest_top_10_rating_message,
            archive_prefix: Optional[str] = None,
            period_days: int = 7,
            title: str = "🏆 Топ‑10",
            show_time: bool = True,
    ):
        self.prefix = prefix
        self._service = service
        self.results_text_formatter = results_text_formatter
        self.period_days = period_days
        self.title = title
        self.show_time = show_time

        if not archive_prefix:
            archive_prefix = f"archive_{prefix}"

        self.archive_prefix = archive_prefix

    async def current_contest_callback_handler(
            self,
            callback: CallbackQuery,
    ) -> None:
        buttons = {}
        sizes = tuple()

        try:
            previous_page_number, detail_page_number = map(
                int, callback.data.split("_")[-2:]
            )
            contests_ids = await self._service.get_ids(is_archived=True)

            paginator = Paginator(
                contests_ids,
                page_number=detail_page_number,
                per_page=1
            )
            contest_id = paginator.get_page()[0]
            contest = await self._service.get_contest(id=contest_id)

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
            contest, _ = await self._service.get_or_create_current_contest()
            archive_exists = await self._service.contest_exists(is_archived=True)
            if archive_exists:
                buttons.update({"АРХИВ 🗄": f"{self.archive_prefix}_1"})

            telegram_method = callback.message.answer
            await callback.message.delete()

        message_text = self.results_text_formatter(
            top_10_rating=contest.top_10_rating,
            start_at=contest.start_at,
            prize_fund=contest.prize_fund,
            period_days=self.period_days,
            show_time=self.show_time,
        )

        await telegram_method(
            text=message_text,
            reply_markup=get_donate_keyboard(
                buttons=buttons,
                sizes=sizes,
            ),
        )

    async def archive_contest_callback_handler(
            self,
            callback: CallbackQuery,
    ) -> None:
        callback_data = callback.data.split("_")
        base_callback_data = "_".join(callback_data[0:-1])
        page_number = int(callback_data[-1])
        per_page = 10
        default_buttons = {"🔙 Назад": self.prefix}
        buttons = {}
        sizes = tuple()

        contests = await self._service.get_contests_list(is_archived=True)
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
                contest.start_at,
                period_days=self.period_days,
                show_time=self.show_time,
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