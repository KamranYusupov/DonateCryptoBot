from aiogram import Router

from app.core.config import settings
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
from .admin import admin_router
from .triumph_bill import triumph_bill_router
from .triumph_bill_transaction import triumph_bill_transaction_router
from .sponsors_contest import sponsors_contest_router
from .registration_contest import registration_contest_router


def get_all_routers() -> Router:
    """Функция для регистрации всех router"""

    router = Router()

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
        sponsors_contest_router,
        registration_contest_router,
        admin_router,
        triumph_bill_router,
        triumph_bill_transaction_router,
    )

    return router
