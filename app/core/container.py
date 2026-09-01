from dependency_injector import containers, providers
from redis.asyncio import Redis

from app import loader
from app.core.config import Settings
from app.db.session import init_db_pool

from app.models import (
    AdminUser,
    TelegramUser,
    Matrix,
    MatrixNode,
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
    RegistrationStatistic,
    TriumphBillTransaction,
    ReferralLink,
)
from app.orchestrators.crypto_bot_payment import CryptoBotPaymentOrchestrator
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
    RepositoryRegistrationStatistic,
    RepositoryTriumphBillTransaction,
    RepositoryReferralLink,
)
from app.services import (
    TelegramUserService,
    TelegramBotService,
    DonateService,
    DonateConfirmService,
    RegistrationContestService,
    SponsorsContestService,
    CryptoBotProcessedWebhookService,
    CryptoBotAPIService,
    WithdrawalRequestService,
    TransferService,
    StatisticService,
    MatrixService,
    MatrixNodeService,
    MatrixActivationNotifierService,
    TriumphBillService,
    TriumphBillTransactionService,
    AdminImpersonationService,
    GlobalMarketingDonateService,
)
from app.infrastructure.adapters import (
    TelegramBotTaskIQAdapter,
    MatrixNotifierTaskIQAdapter,
)
from app.use_cases import (
    RegistrationContestUseCase,
    SponsorsContestUseCase,
)
from app.core.redis import init_redis_pool
from app.use_cases.donations import SendDonationsMenuUseCase


class Container(containers.DeclarativeContainer):
    settings = providers.Factory(Settings)

    db_manager = providers.Resource(
        init_db_pool,
        db_url=settings.provided.postgres_url
    )
    session = providers.Factory(db_manager.provided.create_session.call())

    redis_client = providers.Resource(
        init_redis_pool,
        redis_url=settings.provided.redis_url,
        decode_responses=settings.provided.redis_decode_responses,
        health_check_interval=settings.provided.redis_health_check_interval
    )

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
        model=RegistrationStatistic,
        session=session
    )
    repository_processed_webhook = providers.Factory(
        RepositoryProcessedCryptoBotPaymentWebhook,
        model=ProcessedCryptoBotPaymentWebhook,
        session=session,
    )
    repository_triumph_bill_transaction = providers.Factory(
        RepositoryTriumphBillTransaction,
        model=TriumphBillTransaction,
        session=session,
    )
    repository_referral_link = providers.Factory(
        RepositoryReferralLink,
        model=ReferralLink,
        session=session,
    )
    # endregion

    # region infra adapters
    telegram_bot_taskiq_adapter = providers.Factory(
        TelegramBotTaskIQAdapter
    )
    matrix_notifier_taskiq_adapter = providers.Factory(
        MatrixNotifierTaskIQAdapter
    )
    # endregion

    # region infra services
    telegram_bot_service = providers.Factory(
        TelegramBotService,
        bot=providers.Object(loader.bot),
    )
    crypto_bot_api_service = providers.Factory(
        CryptoBotAPIService,
        base_url=settings.provided.crypto_bot_api_base_url,
        api_token=settings.provided.crypto_bot_api_token,
    )
    # endregion

    # region services
    telegram_user_service = providers.Factory(
        TelegramUserService,
        repository_telegram_user=repository_telegram_user,
        repository_referral_link=repository_referral_link,
    )

    matrix_service = providers.Factory(
        MatrixService,
        repository_matrix=repository_matrix,
        repository_matrix_node=repository_matrix_node,
        repository_telegram_user=repository_telegram_user,
    )
    matrix_node_service = providers.Factory(
        MatrixNodeService,
        repository_matrix_node=repository_matrix_node,
        repository_matrix=repository_matrix,
        repository_telegram_user=repository_telegram_user,
    )
    donate_service = providers.Factory(
        DonateService,
        repository_telegram_user=repository_telegram_user,
        repository_matrix=repository_matrix,
        repository_donate=repository_donate,
    )
    donate_confirm_service = providers.Factory(
        DonateConfirmService,
        repository_donate=repository_donate,
        repository_donate_transaction=repository_donate_transaction,
        repository_telegram_user=repository_telegram_user,
        repository_admin_statistic=repository_admin_statistic,
    )
    withdrawal_request_service = providers.Factory(
        WithdrawalRequestService,
        repository_withdrawal_request=repository_withdrawal_request,
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
        telegram_bot_adapter=telegram_bot_taskiq_adapter,
        matrix_notifier_adapter=matrix_notifier_taskiq_adapter,
    )
    triumph_bill_service = providers.Factory(
        TriumphBillService,
        repository_telegram_user=repository_telegram_user,
    )
    triumph_bill_transaction_service = providers.Factory(
        TriumphBillTransactionService,
        repository_triumph_bill_transaction=repository_triumph_bill_transaction,
    )
    impersonation_service = providers.Factory(
        AdminImpersonationService,
        redis_client=redis_client,
        impersonation_user_id_key=settings.provided.impersonation_user_id_key,
    )
    # endregion

    # region application services
    global_marketing_donate_service = providers.Factory(
        GlobalMarketingDonateService,
        donate_service=donate_service,
        matrix_node_service=matrix_node_service,
        repository_telegram_user=repository_telegram_user,
        repository_matrix_node=repository_matrix_node,
    )
    # endregion

    # region orchestrators
    crypto_bot_payment_orchestrator = providers.Factory(
        CryptoBotPaymentOrchestrator,
        telegram_user_service=telegram_user_service,
        processed_webhook_service=crypto_bot_processed_webhook_service,
    )
    # endregion

    # region use cases
    sponsors_contest_use_case = providers.Factory(
        SponsorsContestUseCase,
        title="🏆 Топ‑10 кураторов",
        prefix=settings.provided.sponsors_contest_callback_prefix,
        service=sponsors_contests_service,
    )
    registration_contest_use_case = providers.Factory(
        RegistrationContestUseCase,
        title="🏆 Топ‑10 пригласителей",
        prefix=settings.provided.registration_contest_callback_prefix,
        service=registration_contests_service,
    )
    send_donations_menu_use_case = providers.Factory(
        SendDonationsMenuUseCase,
        telegram_user_service=telegram_user_service,
        matrix_service=matrix_service,
        matrix_node_service=matrix_node_service,
        sponsors_contests_service=sponsors_contests_service,
        statistic_service=statistic_service,
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
        "app.handlers.bill_type",
        "app.handlers.aggregators",
        "app.handlers.admin",
        "app.handlers.safe",
        "app.handlers.registration_contest",
        "app.handlers.sponsors_contest",
        "app.handlers.triumph_bill_transaction",
        "app.handlers.referral_link",

        "app.use_cases.donations",

        "app.middlewares.ban_user",
        "app.middlewares.current_user",
        "app.middlewares.subscriptions",

        "app.utils.excel",
    ]
    wiring_config = containers.WiringConfiguration(
        modules=wiring_modules
    )

