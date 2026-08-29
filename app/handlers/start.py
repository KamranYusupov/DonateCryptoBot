import loguru
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, CommandObject, Command
from dependency_injector.wiring import inject, Provide
from sqlalchemy import text

from app.core.container import Container
from app.keyboards.inline import get_confirm_inline_keyboard
from app.services.matrix_node_service import MatrixNodeService
from app.services.telegram_user_service import TelegramUserService
from app.schemas.matrix import MatrixEntity
from app.models.telegram_user import TelegramUser
from app.services.matrix_service import MatrixService
from app.models.telegram_user import DonateStatus
from app.keyboards.reply import get_reply_keyboard
from app.keyboards.donate import get_start_inline_keyboard
from app.utils.bot import get_schema_from_user
from app.models.matrix import MatrixEngineType, MatrixMarketingType
from app.models.telegram_user import GlobalMarketingDonateStatus
from app.schemas.marketing import StartMarketingScope, GlobalMarketingScope
from app.filters.marketing_type import MarketingTypeFilter
from app.keyboards.donate import get_donate_keyboard

start_router = Router()


@start_router.message(CommandStart())
@inject
async def command_start(
        message: Message,
        command: CommandObject,
        current_user: TelegramUser,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:
    if current_user:
        await message.answer(
            f"👋 Приветствую, {current_user.first_name}!\n\n",
            reply_markup=get_reply_keyboard(None)
        )
        if current_user.is_admin:
            return
        sponsor = await telegram_user_service.get_telegram_user(
            user_id=current_user.sponsor_user_id,
        )
        await message.answer(
            f"Я твой куратор — @{sponsor.username}\n\n"
            "📌 С чего начать:\n\n"
            "✅ Смотреть фильм\n"
            "✅ Изучить презентацию\n"
            "✅ Разобраться с ботом\n\n"
            "По всем вопросам — обращайся ко мне.\n\n"
            "Твои первые шаги — ниже ⤵️",
            reply_markup=get_start_inline_keyboard(),
        )
        return

    if not command.args:
        await message.answer(
            "Регистрация в боте происходит "
            "только по реферальной ссылке."
        )
        return

    if command.args.isdigit():
        sponsor_user_id = int(command.args)
        sponsor = await telegram_user_service.get_telegram_user(
            user_id=sponsor_user_id,
        )
        if sponsor:
            await message.answer(
                "🔗 Реферальная ссылка устарела\n\n"
                f"✅ Напишите {sponsor.full_username} — запросите новую"
            )
            return

    referral_link = await telegram_user_service.get_link_by_code(
        code=command.args,
    )

    if not referral_link:
        await message.answer("Неправильная ссылка")
        return

    sponsor = await telegram_user_service.get_telegram_user(
        id=referral_link.telegram_user_id,
    )

    if not referral_link.is_active:
        await message.answer(
            "🔗 Реферальная ссылка устарела\n\n"
            f"✅ Напишите {sponsor.full_username} — запросите новую"
        )
        return

    await message.answer(
        f"Вы регистрируетесь по рекомендации {sponsor.full_name}"
        f" - Продолжить регистрацию?",
        reply_markup=get_confirm_inline_keyboard(
            yes_button_data=f"yes_{referral_link.code}",
            no_button_data="delete_msg",
            sizes=(2, 1),
        ),
    )


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
        status=list(DonateStatus)[-1],
        global_marketing_status=list(GlobalMarketingDonateStatus)[-1],
        depth_level=0,
        is_admin=True,
    )
    admin_user = await telegram_user_service.create_telegram_user(user=user_schema)

    for status in list(DonateStatus):
        if status is DonateStatus.BRILLIANT:
            await matrix_node_service.create_matrix_with_root_node(
                owner_id=admin_user.id,
                marketing_type=MatrixMarketingType.START,
                matrix_status=status,
            )
            continue

        matrix_schema = MatrixEntity(
            owner_id=admin_user.id,
            engine_type=MatrixEngineType.JSON,
            status=status
        )
        await matrix_service.create_matrix(matrix_schema)

    await matrix_node_service.create_matrix_with_root_node(
        owner_id=admin_user.id,
        marketing_type=MatrixMarketingType.GLOBAL,
        global_marketing_status=list(GlobalMarketingDonateStatus)[-1]
    )

    await message.answer("Готово ✅")
