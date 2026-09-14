from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from dependency_injector.wiring import inject

from app.loader import bot
from app.core.config import settings
from app.use_cases.file import SendFileFromLoadedFileIDOrSaveUseCase
from app.models.telegram_user import TelegramUser
from app.filters.user import UserExistsFilter

referral_link_router = Router()


@referral_link_router.message(
    F.text.lower() == "🚀 продвижение",
    UserExistsFilter()
)

@inject
async def referral_message_handler(
        message: Message,
        current_user: TelegramUser,
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

    await message.answer(
        f"Ваша реферальная ссылка: {current_user.referral_url}",
    )

