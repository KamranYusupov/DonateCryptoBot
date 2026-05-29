from aiogram import Router
from dependency_injector.wiring import inject, Provide

from .controllers.contest import ContestCallbackController
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
from app.core.container import Container


@inject
def get_all_routers(
        sponsors_contest_controller: ContestCallbackController = Provide[
            Container.sponsors_contest_controller
        ],
        registration_contest_controller: ContestCallbackController = Provide[
            Container.registration_contest_controller
        ],
) -> Router:
    """Функция для регистрации всех router"""

    router = Router()
    router.include_router(start_router)
    router.include_router(donate_router)
    router.include_router(info_router)
    router.include_router(ban_user_router)
    router.include_router(referral_router)
    router.include_router(payment_router)
    router.include_router(withdrawal_requests_router)
    router.include_router(transfer_router)
    router.include_router(worker_router)
    router.include_router(bill_type_router)
    router.include_router(aggregators_router)
    router.include_router(sponsors_contest_router)
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
    )
    sponsors_contest_controller.register_to_router(router)
    registration_contest_controller.register_to_router(router)


    return router
