from aiogram.filters import Filter
from aiogram.types import CallbackQuery

from app.models.matrix import MatrixMarketingType


class MarketingTypeFilter(Filter):
    def __init__(self, callback_data_startswith: str):
        self.callback_data_startswith = callback_data_startswith
        self.prefixes = tuple(
            f"{marketing_type.value}_{callback_data_startswith}"
            for marketing_type in MatrixMarketingType
        )

    async def __call__(self, callback: CallbackQuery) -> bool:
        from loguru import logger

        logger.info(callback.data)
        logger.info(str(self.prefixes))
        return callback.data.startswith(self.prefixes)
