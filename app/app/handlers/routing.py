from aiogram import Router

from .start import start_router
from .donate import donate_router
from .info import info_router
from .ban_user import ban_user_router
from .referral_message import referral_router
from .payments import payment_router
from .withdrawal_request import withdrawal_requests_router
from .transfer import transfer_router
from .bill_type import bill_type_router
from .aggregators import aggregators_router
from app.core.config import settings
from .controllers.contest import get_router as get_contest_router


def get_all_routers() -> Router:
    """Функция для регистрации всех router"""

    router = Router()

    contest_router = get_contest_router()
    router.include_routers(
        start_router,
        donate_router,
        info_router,
        ban_user_router,
        referral_router,
        payment_router,
        withdrawal_requests_router,
        transfer_router,
        bill_type_router,
        aggregators_router,
        contest_router
    )

    return router
