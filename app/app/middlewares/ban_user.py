from aiogram.types import Message, CallbackQuery
from dependency_injector.wiring import inject, Provide

from app.services import telegram_user_service
from app.core.container import Container
from app.services.telegram_user_service import TelegramUserService
from app.core.config import settings


@inject
async def ban_user_middleware(
        handler,
        event: Message | CallbackQuery,
        data: dict,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
):
    """
    Middleware, для обработки действий от забаненного пользователя.
    """
    import loguru

    current_user = await telegram_user_service.get_telegram_user(
        user_id=event.from_user.id
    )
    if not isinstance(event, CallbackQuery):
        pass
    else:
        loguru.logger.info(event.data)
        if (event.data.startswith("ref_msg_")
                or event.data == "skip_referrals_msg_state"
                or event.data == "send_complete_message"
                or event.data in ("confirm_referrals_send", "create_message")
        ):
            # Если нажал НЕ админ — выходим
            if not current_user or not current_user.is_admin:
                return

        # Если кнопка НЕ админская, она идет на общую проверку для всех
        elif not (
                (event.data in ("confirm_donate_🟢_500", "donate_🟢_500", "donations", "excel_users", "cancel",
                                "confirm_transfer", "start_transfer"))
                or
                (event.data.startswith("transfer"))
                or
                (event.data.startswith("send_donate_🟢_500_"))
                or
                (event.data.startswith("donate_🟢_500_"))
                or
                (event.data.startswith("transfer"))
                or
                (event.data.startswith("referrals_"))
                or
                (event.data.startswith("register_"))
                or
                (event.data.startswith("yes_"))
                or
                (event.data.startswith("menu_"))
                or
                (event.data.startswith("team_"))
                or
                (event.data.startswith("archive_team_"))
        ):
            return

    if not current_user:
        return await handler(event, data)
    if current_user.is_banned:
        await event.bot.send_message(
            chat_id=event.from_user.id,
            text=(
                "Ваш аккаунт заблокирован. Для уточнения причины блокировки, "
                f"свяжитесь со службой поддержки. @{settings.support_username}"
            )
        )
        return

    return await handler(event, data)