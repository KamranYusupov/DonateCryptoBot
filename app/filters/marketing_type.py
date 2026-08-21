from typing import Sequence

from aiogram.filters import Filter
from aiogram.types import CallbackQuery

from app.models.matrix import MatrixMarketingType


class MarketingTypeFilter(Filter):
    def __init__(
            self,
            callback_data_startswith: str,
            marketing_types: Sequence[MatrixMarketingType] | None = None,
    ):
        self.callback_data_startswith = callback_data_startswith

        marketing_types = (
            marketing_types if marketing_types is not None
            else list(MatrixMarketingType)
        )
        self.prefixes = tuple(
            f"{marketing_type.value}_{callback_data_startswith}_"
            for marketing_type in marketing_types
        )

    async def __call__(self, callback: CallbackQuery) -> bool:
        return callback.data.startswith(self.prefixes)
