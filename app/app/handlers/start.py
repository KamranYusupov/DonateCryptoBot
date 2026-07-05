import loguru
from aiogram import Router, F
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, CommandObject, Command
from dependency_injector.wiring import inject, Provide

from app.core.container import Container
from app.keyboards.inline import get_confirm_inline_keyboard
from app.services.matrix_node_service import MatrixNodeService
from app.services.telegram_user_service import TelegramUserService
from app.schemas.telegram_user import TelegramUserEntity, generate_random_user
from app.schemas.matrix import MatrixEntity
from app.keyboards.donate import get_donate_keyboard
from app.core.config import settings
from app.models.telegram_user import status_list, TelegramUser
from app.services.matrix_service import MatrixService
from app.utils.sponsor import get_callback_value
from app.services.donate_service import DonateService
from app.models.telegram_user import DonateStatus
from app.keyboards.reply import get_reply_keyboard
from app.utils.matrix import get_matrices_length
from app.services.donate_confirm_service import DonateConfirmService
from app.keyboards.donate import get_start_inline_keyboard
from app.utils.bot import get_schema_from_user, send_captcha
from app.states.captcha import CaptchaState

start_router = Router()


@start_router.message(CommandStart())
@inject
async def command_start(
        message: Message,
        command: CommandObject,
        state: FSMContext,
        current_user: TelegramUser,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:
    sponsor_user_id = current_user.sponsor_user_id if current_user else command.args
    sponsor = await telegram_user_service.get_telegram_user(user_id=sponsor_user_id)
    if (not sponsor or sponsor.is_bot) and not current_user:
        await message.answer("Неправильная ссылка")
        return

    if not current_user:
        await message.answer(
            f"Вы регистрируетесь по рекомендации {sponsor.first_name}"
            f" {sponsor.last_name if sponsor.last_name else ''}"
            f" - Продолжить регистрацию?",
            reply_markup=get_confirm_inline_keyboard(
                yes_button_data=f"yes_{sponsor_user_id}",
                no_button_data="delete_msg",
                sizes=(2, 1),
            ),
        )
        return

    if not current_user.captcha_verified:
        await send_captcha(
            message=message,
            state=state,
            sponsor_user_id=sponsor_user_id,
        )
        await state.set_state(CaptchaState.option)
        return

    if current_user and current_user.captcha_verified:
        await message.answer(
            f"👋 Приветствую, {current_user.first_name}!\n\n",
            reply_markup=get_reply_keyboard(None)
        )
        if not current_user.is_admin:
            await message.answer(
                f"Я твой куратор — @{sponsor.username}\n\n"
                "📌 С чего начать:\n\n"
                "✅ Смотреть фильм\n"
                "✅ Изучить презентацию\n"
                "✅ Разобраться с ботом\n\n"
                "По всем вопросам — обращайся ко мне.\n\n"
                "Твои первые шаги — ниже ⤵️"
                ,
                reply_markup=get_start_inline_keyboard(),
            )
        return


@start_router.callback_query(F.data == "delete_msg")
@inject
async def delete_msg_handler(
        callback: CallbackQuery,
) -> None:
    await callback.message.delete()


@start_router.message(F.text.lower() == "отмена ❌")
@inject
async def cancel_handler(
        message: Message,
        state: FSMContext,
        current_user: TelegramUser,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
):
    await message.answer(
        text="Действие отменено",
        reply_markup=get_reply_keyboard(current_user)
    )

    await state.clear()

@start_router.callback_query(F.data == "cancel")
async def cancel_callback_handler(
        callback: CallbackQuery,
        state: FSMContext
):
    await callback.message.delete()
    await callback.message.answer(text="Действие отменено", reply_markup=get_reply_keyboard(None))
    await state.clear()


@start_router.message(Command("admin"))
@inject
async def admin(
        message: Message,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        matrix_service: MatrixService = Provide[Container.matrix_service],
        matrix_node_service: MatrixNodeService = Provide[
            Container.matrix_node_service
        ],
):
    """Создание системного аккаунта для тестов"""
    admin_user = await telegram_user_service.get_telegram_user(is_admin=True)
    if admin_user:
        return

    user_schema = get_schema_from_user(
        message.from_user,
        status=DonateStatus.get_status_list()[-1],
        depth_level=0,
        is_admin=True,
        captcha_verified=True,
    )
    admin_user = await telegram_user_service.create_telegram_user(user=user_schema)

    for status in status_list:
        matrix_dict = {"owner_id": admin_user.id, "status": status}

        if status == DonateStatus.BRILLIANT:
            matrix_node_service.create_matrix_with_root_node(
                **matrix_dict
            )
            continue


        await matrix_service.create_matrix(
            matrix=MatrixEntity(
                **matrix_dict,
            )
        )

    await message.answer(
        f"✅ Готово - {admin_user.referral_url}",
        reply_markup=get_reply_keyboard(admin_user),
    )
