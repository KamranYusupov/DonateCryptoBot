from aiogram import Router, F
from aiogram.types import Message, FSInputFile, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from dependency_injector.wiring import inject, Provide

from app.core.container import Container
from app.loader import bot
from app.services.telegram_user_service import TelegramUserService
from app.keyboards.donate import get_donate_keyboard
from app.core.config import settings
from app.use_cases.file import SendFileFromLoadedFileIDOrSaveUseCase
from app.models.telegram_user import TelegramUser
from app.filters.user import UserExistsFilter
from app.exceptions.referral_link import ActiveLinkAlreadyExistsError

referral_link_router = Router()


@referral_link_router.message(
    F.text.lower() == "🚀 продвижение",
    UserExistsFilter()
)

@inject
async def referral_message_handler(
        message: Message,
        current_user: TelegramUser,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
):
    await message.answer_photo(
        photo=FSInputFile("app/media/base_photo.jpg"),
        caption=(
            "🎬 «Код Денег» — нейронаучный фильм. Никаких сложных техник. "
            "Просто берёшь бумагу, пишешь желаемую сумму. И смотришь видео.\n\n"
            "🧠 Без магии. Без усилий. Твой мозг сам переключается из дефицита в изобилие."
            " Ты начинаешь замечать деньги там, где раньше видел стены.\n\n"
            "📎 Всё, что нужно — фильм, инструкция и чат. Внутри бота."
        ),
    )
    await SendFileFromLoadedFileIDOrSaveUseCase.send_video(
        bot=bot,
        chat_id=message.chat.id,
        file_path=settings.kod_deneg_video_file_path,
        file_id_path=settings.kod_deneg_video_file_id_path,
        supports_streaming=True,
        width=1080,
        height=1920,
    )

    referral_link = await telegram_user_service.get_active_referral_link(
        current_user.id,
    )
    if referral_link:
        await message.answer(
            f"Ваша реферальная ссылка: {referral_link.url}",
        )
        return

    await message.answer(
        "Нет активной ссылки.",
        reply_markup=get_donate_keyboard(
            buttons={"🧬 СОЗДАТЬ ССЫЛКУ 🧬": "generate_referral_link"}
        )
    )


@referral_link_router.callback_query(
    F.data == "generate_referral_link",
    UserExistsFilter()
)
@inject
async def referral_message_handler(
        callback: CallbackQuery,
        current_user: TelegramUser,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
):
    referral_link = await telegram_user_service.get_active_referral_link(
        current_user.id,
    )
    if not referral_link:
        try:
            referral_link = await telegram_user_service.generate_referral_link(
                current_user.id,
            )
        except ActiveLinkAlreadyExistsError:
            await callback.message.edit_text("Реферальная ссылка уже сгенерирована.")
            return

    await callback.message.edit_text(
        f"Ваша реферальная ссылка: {referral_link.url}",
    )
    return
