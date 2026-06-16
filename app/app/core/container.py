from dependency_injector import containers, providers

from app.core.config import Settings
from app.db.session import SyncSession

from app.models import (
    AdminUser,
    TelegramUser,
    Matrix,
    MatrixNode,
    AddBotToMatrixTaskModel,
    Donate,
    DonateTransaction,
    WithdrawalRequest,
    SponsorsContest,
    SponsorsContestPoint,
    RegistrationContest,
    RegistrationContestPoint,
    Transfer,
    AdminStatistic,
    MatrixStatistic,
    ProcessedCryptoBotPaymentWebhook,
)
from app.repositories import (
    RepositoryDonate,
    RepositoryDonateTransaction,
    RepositoryProcessedCryptoBotPaymentWebhook,
    RepositoryRegistrationContest,
    RepositoryRegistrationContestPoint,
    RepositoryTelegramUser,
    RepositoryAdminUser,
    RepositoryMatrix,
    RepositoryMatrixNode,
    RepositoryWithdrawalRequest,
    RepositorySponsorsContest,
    RepositorySponsorsContestPoint,
    RepositoryTransfer,
    RepositoryAdminStatistic,
    RepositoryMatrixStatistic,
    RepositoryAddBotToMatrixTaskModel, RepositoryRegistrationStatistic,
)
from app.services import (
    TelegramUserService,
    DonateService,
    DonateConfirmService,
    RegistrationContestService,
    SponsorsContestService,
    CryptoBotProcessedWebhookService,
    CryptoBotAPIService,
    WithdrawalRequestService,
    AddBotToMatrixTaskService,
    TransferService,
    StatisticService,
    MatrixService,
    MatrixNodeService,
    MatrixActivationNotifierService,
    TriumphBillService,
)


class Container(containers.DeclarativeContainer):
    settings = providers.Factory(Settings)
    db = providers.Singleton(SyncSession, db_url=settings.provided.postgres_url)
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
    repository_matrix_statistic = providers.Factory(
        RepositoryMatrixStatistic, model=MatrixStatistic, session=session
    )
    repository_registration_statistic = providers.Factory(
        RepositoryRegistrationStatistic,
        model=RepositoryRegistrationStatistic,
        session=session
    )
    repository_processed_webhook = providers.Factory(
        RepositoryProcessedCryptoBotPaymentWebhook,
        model=ProcessedCryptoBotPaymentWebhook,
        session=session,
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
        base_url=settings.provided.crypto_bot_api_base_url,
        api_token=settings.provided.crypto_bot_api_token,
    )
    withdrawal_request_service = providers.Factory(
        WithdrawalRequestService,
        repository_withdrawal_request=repository_withdrawal_request,
    )
    add_bot_to_matrix_task_service = providers.Factory(
        AddBotToMatrixTaskService,
        repository_matrix_task=repository_matrix_task,
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
    statistic_service = providers.Factory(
        StatisticService,
        repository_admin_statistic=repository_admin_statistic,
        repository_matrix_statistic=repository_matrix_statistic,
        repository_registration_statistic=repository_registration_statistic,
    )
    crypto_bot_processed_webhook_service = providers.Factory(
        CryptoBotProcessedWebhookService,
        repository_processed_webhook=repository_processed_webhook,
    )
    matrix_activation_notifier_service = providers.Factory(
        MatrixActivationNotifierService,
        repository_telegram_user=repository_telegram_user,
    )
    triumph_bill_service = providers.Factory(
        TriumphBillService,
        repository_telegram_user=repository_telegram_user,
    )
    # endregion

    wiring_modules = [
        "app.api.endpoints.crypto_bot",

        "app.handlers.routing",
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
        "app.handlers.admin",
        "app.handlers.triumph_bill",
        "app.handlers.controllers.contest",

        "app.use_cases.donations",

        "app.middlewares.ban_user",
        "app.middlewares.subscriptions",

        "app.tasks.matrix",
        "app.tasks.taskiq.business.triumph_bill",

        "app.utils.excel",
    ]

    wiring_config = containers.WiringConfiguration(
        modules=wiring_modules
    )

