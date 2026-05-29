from dependency_injector import containers, providers

from app.core.config import Settings
from app.db.session import SyncSession
from app.repositories.donate import RepositoryDonate, RepositoryDonateTransaction
from app.repositories.registration_contest import RepositoryRegistrationContest, RepositoryRegistrationContestPoint

from app.repositories.telegram_user import RepositoryTelegramUser
from app.repositories.admin_user import RepositoryAdminUser
from app.repositories.matrix import (
    RepositoryMatrix,
    RepositoryMatrixNode,
)
from app.repositories.transaction import RepositoryTransaction
from app.repositories.withdrawal_request import RepositoryWithdrawalRequest
from app.repositories.sponsors_contest import RepositorySponsorsContest, RepositorySponsorsContestPoint
from app.repositories.transfer import RepositoryTransfer
from app.repositories.statistic import RepositoryAdminStatistic

from app.models.telegram_user import TelegramUser
from app.models.admin_user import AdminUser
from app.models.donate import Donate, DonateTransaction
from app.models.matrix import Matrix, MatrixNode
from app.models.transaction import Transaction
from app.models.withdrawal_request import WithdrawalRequest
from app.models.contest import (
    SponsorsContest,
    SponsorsContestPoint,
    RegistrationContest,
    RegistrationContestPoint,
)
from app.models.transfer import Transfer
from app.models.statistic import AdminStatistic

from app.services.donate_confirm_service import DonateConfirmService
from app.services.registration_contest_service import RegistrationContestService
from app.services.telegram_user_service import TelegramUserService
from app.services.matrix_service import MatrixService
from app.services.donate_service import DonateService
from app.services.crypto_bot_api_service import CryptoBotAPIService
from app.services.withdrawal_request import WithdrawalRequestService
from app.models.matrix import AddBotToMatrixTaskModel
from app.repositories.matrix import RepositoryAddBotToMatrixTaskModel
from app.services.matrix_service import AddBotToMatrixTaskModelService
from app.services.sponsors_contest_service import SponsorsContestService
from app.services.transfer_service import TransferService
from app.services.statistic_service import AdminStatisticService
from app.services.matrix_node_service import MatrixNodeService


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "app.api.endpoints.crypto_bot",

            "app.handlers.donate",
            "app.handlers.start",
            "app.handlers.info",
            "app.handlers.ban_user",
            "app.handlers.referral_message",
            "app.handlers.payments",
            "app.handlers.withdrawal_request",
            "app.handlers.transfer",
            "app.handlers.worker",
            "app.handlers.bill_type",
            "app.handlers.aggregators",
            "app.handlers.sponsors_contest",

            "app.middlewares.ban_user",
            "app.middlewares.subscriptions",
            "app.tasks.donate",
            "app.tasks.matrix",

            "app.utils.excel",
            "app.utils.texts",
        ]
    )

    config = providers.Factory(Settings)
    db = providers.Singleton(SyncSession, db_url=config.provided.postgres_url)
    session = providers.Factory(db().create_session)

    # region repository
    repository_telegram_user = providers.Factory(
        RepositoryTelegramUser, model=TelegramUser, session=session
    )
    repository_admin_user = providers.Factory(
        RepositoryAdminUser, model=AdminUser, session=session
    )
    repository_matrix = providers.Factory(
        RepositoryMatrix, model=Matrix, session=session
    )
    repository_matrix_node = providers.Factory(
        RepositoryMatrixNode, model=MatrixNode, session=session
    )
    repository_donate = providers.Factory(
        RepositoryDonate,
        model=Donate,
        session=session,
    )
    repository_donate_transaction = providers.Factory(
        RepositoryDonateTransaction,
        model=DonateTransaction,
        session=session,
    )
    repository_withdrawal_request = providers.Factory(
        RepositoryWithdrawalRequest, model=WithdrawalRequest, session=session
    )
    repository_matrix_task = providers.Factory(
        RepositoryAddBotToMatrixTaskModel, model=AddBotToMatrixTaskModel, session=session
    )
    repository_sponsors_contest = providers.Factory(
        RepositorySponsorsContest, model=SponsorsContest, session=session
    )
    repository_sponsors_contest_point = providers.Factory(
        RepositorySponsorsContestPoint, model=SponsorsContestPoint, session=session
    )
    repository_registration_contest = providers.Factory(
        RepositoryRegistrationContest, model=RegistrationContest, session=session
    )
    repository_registration_contest_point = providers.Factory(
        RepositoryRegistrationContestPoint, model=RegistrationContestPoint, session=session
    )
    repository_transfer = providers.Factory(
        RepositoryTransfer, model=Transfer, session=session
    )
    repository_admin_statistic = providers.Factory(
        RepositoryAdminStatistic, model=AdminStatistic, session=session
    )
    # endregion

    # region services
    telegram_user_service = providers.Factory(
        TelegramUserService, repository_telegram_user=repository_telegram_user
    )
    matrix_service = providers.Factory(
        MatrixService,
        repository_matrix=repository_matrix,
        repository_telegram_user=repository_telegram_user,
    )
    matrix_node_service = providers.Factory(
        MatrixNodeService,
        repository_matrix_node=repository_matrix_node,
        repository_matrix=repository_matrix,
        repository_telegram_user=repository_telegram_user,
        repository_matrix_task=repository_matrix_task,
    )
    donate_service = providers.Factory(
        DonateService,
        repository_telegram_user=repository_telegram_user,
        repository_matrix=repository_matrix,
        repository_donate=repository_donate,
        repository_matrix_task=repository_matrix_task,
    )
    donate_confirm_service = providers.Factory(
        DonateConfirmService,
        repository_donate=repository_donate,
        repository_donate_transaction=repository_donate_transaction,
        repository_telegram_user=repository_telegram_user,
        repository_admin_statistic=repository_admin_statistic,
    )
    crypto_bot_api_service = providers.Factory(
        CryptoBotAPIService,
        base_url=config.provided.crypto_bot_api_base_url,
        api_token=config.provided.crypto_bot_api_token,
    )
    withdrawal_request_service = providers.Factory(
        WithdrawalRequestService,
        repository_withdrawal_request=repository_withdrawal_request,
    )
    add_bot_to_matrix_task_service = providers.Factory(
        AddBotToMatrixTaskModelService,
        repository_add_bot_to_matrix_task=repository_matrix_task,
    )
    sponsors_contests_service = providers.Factory(
        SponsorsContestService,
        repository_contest=repository_sponsors_contest,
        repository_contest_point=repository_sponsors_contest_point,
        repository_telegram_user=repository_telegram_user,
    )
    registration_contests_service = providers.Factory(
        RegistrationContestService,
        repository_contest=repository_registration_contest,
        repository_contest_point=repository_registration_contest_point,
        repository_telegram_user=repository_telegram_user,
    )

    transfer_service = providers.Factory(
        TransferService,
        repository_transfer=repository_transfer,
        repository_telegram_user=repository_telegram_user,
    )
    admin_statistic_service = providers.Factory(
        AdminStatisticService,
        repository_admin_statistic=repository_admin_statistic,
    )
    # endregion
