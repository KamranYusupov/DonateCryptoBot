import math

from typing import Sequence, Optional, TypeVar


class BasePaginator:
    def __init__(
        self,
        pages_count: int,
        page_number: int = 1,
        per_page: int = 1,
    ):
        self.pages_count = pages_count
        self.page_number = page_number
        self.per_page = per_page

    def has_next(self):
        return self.page_number < self.pages_count

    def has_previous(self):
        return self.page_number > 1

class Paginator(BasePaginator):
    def __init__(
            self,
            array: Sequence,
            page_number: int = 1,
            per_page: int = 1,
    ):
        pages_count = math.ceil(len(array) / per_page)
        super().__init__(pages_count, page_number, per_page)
        self.array = array

    def get_page(self):
        begin = (self.page_number - 1) * self.per_page
        end = begin + self.per_page
        return self.array[begin:end]


class OuterPaginator(BasePaginator):
    def __init__(
            self,
            objects_count: int,
            page_number: int = 1,
            per_page: int = 1
    ):
        self.objects_count = objects_count
        self.pages_count = math.ceil(objects_count / per_page)
        super().__init__(self.pages_count, page_number, per_page)


PaginatorType = TypeVar("PaginatorType", bound=BasePaginator)

def get_pagination_buttons(
        paginator: PaginatorType,
        base_callback_data: str,
):
    buttons = {}
    if paginator.has_previous():
        buttons["⏪"] = f"{base_callback_data}_1"
        buttons["◀ Пред."] = (
            f"{base_callback_data}_{paginator.page_number - 1}"
        )

    if paginator.has_next():
        buttons["След. ▶"] = (
            f"{base_callback_data}_{paginator.page_number + 1}"
        )
        buttons["⏩"] = (
            f"{base_callback_data}_{paginator.pages_count}"
        )

    return buttons