import asyncio
import os
from datetime import datetime
from decimal import Decimal

import loguru
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.types import CallbackQuery, FSInputFile
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from dependency_injector.wiring import inject, Provide

from app.core.container import Container
from app.services import MatrixActivationNotifierService
from app.services.donate_confirm_service import DonateConfirmService
from app.services.matrix_node_service import MatrixNodeService
from app.services.registration_contest_service import RegistrationContestService
from app.services.telegram_user_service import TelegramUserService
from app.services.donate_service import DonateService
from app.keyboards.donate import get_donate_keyboard
from app.core.config import settings
from app.services.matrix_service import MatrixService
from app.keyboards.reply import get_reply_keyboard
from app.tasks.taskiq.tasks.infra.telegram import (
    send_message_task,
    send_photo_task,
    mass_mailing_task,
    mass_mailing_task_by_batches_task,
)
from app.tasks.taskiq.tasks.business.contest import (
    update_registration_contest_task,
    update_sponsors_contest_task,
)
from app.tasks.taskiq.tasks.business.donations import send_donations_menu_task
from app.tasks.taskiq.tasks.business.matrix import apply_bot_matrix_tasks
from app.tasks.taskiq.tasks.business.triumph_bill import increase_triumph_bills_task
from app.utils.pagination import Paginator
from app.utils.excel import export_users_to_excel
from app.models.donate import DonateTransactionType
from app.loader import bot
from app.models.telegram_user import TelegramUser, BillType, GlobalMarketingDonateStatus
from app.models.matrix import MatrixEngineType
from app.keyboards.donate import get_start_inline_keyboard
from app.utils.datetime import to_main_tz
from app.services.sponsors_contest_service import SponsorsContestService
from app.models.telegram_user import DonateStatus
from app.utils.bot import send_message_or_pass, delete_message_or_pass
from app.utils.bot import get_schema_from_user
from app.services.statistic_service import StatisticService
from app.keyboards.inline import get_subscriptions_keyboard, get_confirm_inline_keyboard, get_bill_type_choice_buttons
from app.utils.bot import send_subscription_menu
from app.utils.texts import (
    format_decimal,
    increase_triumph_bills_message_text,
    registration_donate_triumph_bill_text,
    private_channel_invite_message,
)
from app.services import GlobalMarketingDonateService
from app.filters.marketing_type import MarketingTypeFilter
from app.models.matrix import MatrixMarketingType
from app.use_cases.donations import SendDonationsMenuUseCase
from app.schemas.marketing import MatrixMarketingScope, create_marketing_scope
from app.utils.status import is_status_higher, is_status_triumph

donate_router = Router()


@donate_router.callback_query(F.data.startswith("yes_"))
@inject
async def registration_confirm_handler(
        callback: CallbackQuery,
        current_user: TelegramUser,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        session: AsyncSession = Provide[
            Container.session
        ]
) -> None:
    if current_user:
        return

    referral_link_code = callback.data.split("_")[-1]
    referral_link = await telegram_user_service.get_link_by_code(
        code=referral_link_code
    )
    sponsor = await telegram_user_service.get_telegram_user(
        id=referral_link.telegram_user_id
    )
    if not referral_link.is_active:
        await callback.message.edit_text(
            "🔗 Реферальная ссылка устарела\n\n"
            f"✅ Напишите {sponsor.full_username} — запросите новую"
        )
        return

    sponsor_user_id = sponsor.user_id
    user_schema = get_schema_from_user(
        callback.from_user,
        depth_level=sponsor.depth_level + 1,
        sponsor_user_id=sponsor_user_id,
    )
    try:
        current_user = await telegram_user_service.create_telegram_user(
            user=user_schema,
            sponsor=sponsor,
        )
        await telegram_user_service.set_link_expired(
            referral_link_id=referral_link.id,
        )
        await session.commit()
    except:
        await session.rollback()
        raise
    finally:
        await session.close()

    await delete_message_or_pass(callback.message)
    await send_subscription_menu(callback, sponsor_user_id)
    await send_message_or_pass(
        bot=callback.bot,
        chat_id=sponsor_user_id,
        text=(
            f"🎉 Поздравляем! По вашей ссылке зарегистрировался {current_user.full_username}\n\n"
            "👥 Свяжитесь с ним, узнайте, всё ли понятно, и при необходимости окажите поддержку.\n\n"
            "🔥 Ваше внимание = его быстрый старт\n\n"
            "🌀 Состояние → Действие → Результат"
        )
    )


@donate_router.callback_query(F.data.startswith("menu_"))
@inject
async def subscription_checker(
        callback: CallbackQuery,
        current_user: TelegramUser,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        statistic_service: StatisticService = Provide[
            Container.statistic_service
        ],
        registration_contests_service: RegistrationContestService = Provide[
            Container.registration_contests_service
        ],
):
    sponsor_user_id = int(callback.data.split("_")[-1])
    reply_markup = await get_subscriptions_keyboard(
        bot=bot,
        user_id=current_user.user_id,
        sponsor_user_id=sponsor_user_id,
    )
    if reply_markup:
        await delete_message_or_pass(callback.message)
        await callback.message.answer(
            "🔑 Для доступа к основным ресурсам бота, подпишитесь на "
            "ЧАТ, КАНАЛ и KOD💵DENEG ⚡️ АКТИВАЦИИ ⤵️",
            reply_markup=reply_markup
        )
        return

    sponsor = await telegram_user_service.get_telegram_user(
        user_id=current_user.sponsor_user_id
    )

    await delete_message_or_pass(callback.message)
    await callback.message.answer(
        f"👋 Приветствую, {current_user.first_name}!\n\n",
        reply_markup=get_reply_keyboard(current_user)
    )
    await callback.message.answer(
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

    await registration_contests_service.create_contest_point(
        user_id=sponsor_user_id,
    )
    await update_registration_contest_task.kiq()
    if current_user.is_donate_for_registration_sent:
        return

    await telegram_user_service.update(
        obj_id=current_user.id,
        obj_in=dict(is_donate_for_registration_sent=True)
    )
    registration_count = await statistic_service.increment_registrations_count()
    is_increase_triumph_bills_step = (
        registration_count
        % settings.start_marketing.triumph_bills_increase_registration_interval == 0
    )
    if registration_count != 0 and is_increase_triumph_bills_step:
        await increase_triumph_bills_task.kiq()
        chat_ids = [settings.donates_channel_id]
        chat_ids.extend(
            await telegram_user_service
            .get_user_ids_by_active_triumph_bill()
        )
        await mass_mailing_task_by_batches_task.kiq(
            chat_ids=chat_ids,
            text=increase_triumph_bills_message_text,
        )

    if not settings.send_donate_for_registration:
        return

    await telegram_user_service.increment_bill(
        telegram_user_id=current_user.id,
        bill_type=BillType.TRIUMPH,
        amount=settings.donate_for_registration
    )
    is_sponsor_status_bronze_or_higher = (
        sponsor.status is not None and
        DonateStatus.BRONZE.amount
        <= sponsor.status.amount
    )
    if is_sponsor_status_bronze_or_higher and (
            sponsor.donates_sum_for_registration
            < settings.max_donates_sum_for_registration
    ):
        await telegram_user_service.increment_bill_for_registration(
            telegram_user_id=sponsor.id,
            bill_type=BillType.TRIUMPH,
            amount=settings.donate_for_registration_to_sponsor
        )
        admin_statistic = await statistic_service.get_admin_statistic()
        await statistic_service.update_admin_statistic(
            donates_sum_for_registration=(
                admin_statistic.donates_sum_for_registration
                + settings.donate_for_registration
            )
        )

        await asyncio.gather(
            send_message_task.kiq(
                chat_id=sponsor.user_id,
                text=registration_donate_triumph_bill_text.format(
                    settings.donate_for_registration_to_sponsor,
                    f"от {current_user.full_username}"
                ),
            ),
            send_message_task.kiq(
                chat_id=settings.donates_channel_id,
                text=registration_donate_triumph_bill_text.format(
                    settings.donate_for_registration,
                    ""
                ),
            )
        )

@donate_router.callback_query(
    MarketingTypeFilter("donations")
)
@donate_router.message(F.text.lower() == "⚡️ активация")
@inject
async def donations_menu_handler(
        event: Message | CallbackQuery,
        current_user: TelegramUser,
        marketing_scope: MatrixMarketingScope | None = None,
        send_donations_menu_use_case: SendDonationsMenuUseCase = Provide[
            Container.send_donations_menu_use_case
        ]
) -> None:
    if not current_user:
        return

    if isinstance(event, Message):
        telegram_method = bot.send_message
        marketing_scope = create_marketing_scope(
            MatrixMarketingType.GLOBAL,
            current_user,
        )
    elif isinstance(event, CallbackQuery):
        telegram_method = event.message.edit_text
    else:
        return

    await send_donations_menu_use_case.execute(
        marketing_scope=marketing_scope,
        from_user_id=event.from_user.id,
        current_user_id=current_user.id,
        telegram_method=telegram_method,
        callback_suffix="donations",
    )


@donate_router.callback_query(F.data == 'excel_users')
async def export_users_to_excel_callback_handler(
        callback: CallbackQuery,
):
    await callback.message.edit_text(
        "<em>Подождите немного ...</em>",
        parse_mode='HTML',
    )

    file_name = "app/telegram_users.xlsx"
    await export_users_to_excel(file_name)
    file_input = FSInputFile(file_name)

    await callback.message.delete()
    await callback.message.answer_document(file_input)

    os.remove(file_name)



@donate_router.callback_query(
    MarketingTypeFilter("confirm_donate"),
)
@inject
async def confirm_donate_handler(
        callback: CallbackQuery,
        current_user: TelegramUser,
        marketing_scope: MatrixMarketingScope
) -> None:
    triumph_bill = None

    callback_prefix = callback.data.replace("confirm", "send")
    callback_data = callback.data.split("_")
    status_name = callback_data[-1]
    try:
        status = marketing_scope.marketing_type.status_enum[status_name]
    except KeyError:
        loguru.logger.warning(f"Unknown status {status_name}")
        await callback.message.delete()
        return

    if marketing_scope.marketing_type is MatrixMarketingType.START:
        supported_statuses_for_triumph_bill = (
            DonateStatus.SILVER,
            DonateStatus.GOLD,
            DonateStatus.PLATINUM,
            DonateStatus.BRILLIANT
        )

        if status in supported_statuses_for_triumph_bill:
            triumph_bill = current_user.triumph_bill
    elif marketing_scope.marketing_type is MatrixMarketingType.GLOBAL:
        current_user_status = getattr(current_user, marketing_scope.status_orm_attr)
        if is_status_higher(
            status,
            current_user_status,
            or_equal=True,
        ):
            await callback.message.edit_text(
                f"Пакет <b>\"{status.presentation_str}\"</b> уже активирован."
            )
            return

    buttons = get_bill_type_choice_buttons(
        bill_for_withdraw=current_user.bill_for_withdraw,
        bill_for_activation=current_user.bill_for_activation,
        callback_prefix=callback_prefix,
        triumph_bill=triumph_bill,
    )
    buttons["🔙 Назад"] = f"{marketing_scope.marketing_type.label}_donations"

    await callback.message.edit_text(
        "Выберите баланс:",
        reply_markup=get_donate_keyboard(
            buttons=buttons,
            sizes=(1, 1, 1),
        )
    )


@donate_router.callback_query(
    MarketingTypeFilter("send_donate")
)
@inject
async def send_donate_handler(
        callback: CallbackQuery,
        current_user: TelegramUser,
        marketing_type: MatrixMarketingType,
) -> None:
    callback_data = callback.data.split("_")
    status_name, bill_type_value = callback_data[-2:]
    try:
        status = marketing_type.status_enum[status_name]
    except KeyError:
        loguru.logger.warning(f"Unknown status {status_name}")
        await callback.message.delete()
        return

    bill_type = BillType(bill_type_value)
    bill = current_user.get_bill_by_type(bill_type)
    need_to_buy_tokens = bill - status.amount

    if need_to_buy_tokens < 0:
        need_to_buy_tokens = int(abs(need_to_buy_tokens))
        await callback.message.edit_text(
            f"Для активации уровня нехватает {need_to_buy_tokens} USDT.",
            reply_markup=get_donate_keyboard(
                buttons={
                    "Преобрести 💳": f"buy_tokens_{need_to_buy_tokens}",
                    "🔙 Назад": f"{marketing_type.label}_donations",
                },
                sizes=(1, 1),
            ),
        )

        return

    yes_button_data = callback.data.replace("send_", "")
    reply_markup = get_confirm_inline_keyboard(
        yes_button_data=yes_button_data,
        no_button_data=f"{marketing_type}_donations",
        sizes=(2, 1),
    )

    manifest_str = f"<a href='{settings.manifest_link}'>манифестом</a>"
    await callback.message.edit_text(
        text=(
            f"Продолжая, вы соглашаетесь с {manifest_str}.\n\n"
            f"Для активации площадки с вашего баланса будет списано "
            f"{format_decimal(status.amount)} USDT.\n\n"
            "Продолжить?"
        ),
        disable_web_page_preview=True,
        reply_markup=reply_markup,
    )



@donate_router.callback_query(
    MarketingTypeFilter("donate_")
)
@inject
async def donate_handler(
        callback: CallbackQuery,
        current_user: TelegramUser,
        marketing_type: MatrixMarketingType,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        matrix_node_service: MatrixNodeService = Provide[
            Container.matrix_node_service
        ],
        donate_service: DonateService = Provide[Container.donate_service],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
        sponsors_contests_service: SponsorsContestService = Provide[
            Container.sponsors_contests_service
        ],
        matrix_activation_notifier_service: MatrixActivationNotifierService = Provide[
            Container.matrix_activation_notifier_service
        ],
        statistic_service: StatisticService = Provide[
            Container.statistic_service
        ],
        global_marketing_donate_service: GlobalMarketingDonateService = Provide[
            Container.global_marketing_donate_service
        ],
        session: AsyncSession = Provide[Container.session],
) -> None:
    callback_data = callback.data.split("_")
    status_name, bill_type_value = callback_data[-2:]
    try:
        status = marketing_type.status_enum[status_name]
    except KeyError:
        loguru.logger.warning(f"Unknown status {status_name}")
        await callback.message.delete()
        return

    marketing_scope = create_marketing_scope(
        marketing_type=marketing_type,
        status=status,
    )

    bill_type = BillType(bill_type_value)
    bill = current_user.get_bill_by_type(bill_type)
    updated_bill = bill - status.amount

    if updated_bill < 0:
        need_to_buy_tokens = int(abs(updated_bill))
        await callback.message.edit_text(
            f"Для активации уровня нехватает {need_to_buy_tokens} USDT.",
            reply_markup=get_donate_keyboard(
                buttons={
                    "Преобрести 💳": f"buy_tokens_{need_to_buy_tokens}",
                    "🔙 Назад": f"donations",
                },
                sizes=(1, 1),
            ),
        )
        return

    if not status:
        return

    if not callback.from_user.username:
        await callback.message.edit_text(
            "Перед отправкой подарка, "
            "добавьте пожалуйста <em>username</em> в свой телеграм аккаунт"
        )
        return

    send_private_channel_link = False

    sponsors = await telegram_user_service.get_sponsors(
        sponsor_user_id=current_user.sponsor_user_id,
    )

    current_user_status = getattr(current_user, marketing_scope.status_orm_attr)

    exc_user_message = (
        "Непредвиденная ошибка. "
        "Пожалуйста, обратитесь в службу поддержки "
        f"@{settings.support_username}"
    )

    try:
        first_sponsor = sponsors[0]
        is_triumph = is_status_triumph(status)

        transactions_data = []
        sponsors_transactions_data = donate_service.update_transactions_data_with_sponsors(
            current_user,
            *sponsors,
            status=status,
            marketing_scope=marketing_scope,
        )
        transactions_data.extend(sponsors_transactions_data)

        if marketing_type is MatrixMarketingType.START:
            create_tasks_data = {"donate_sum": status.amount}

            if is_triumph:
                inserted_node, upline_nodes = await matrix_node_service.activate_matrix_node(
                    current_user_id=current_user.id,
                    sponsor_id=first_sponsor.id,
                    matrix_status=status,
                    marketing_type=MatrixMarketingType.START,
                    max_upline_depth=marketing_scope.config.triumph_matrix_max_level
                )

                matrix_transactions_data = await donate_service.update_transactions_data_with_nodes(
                    upline_nodes,
                    donate_sum=status.amount,
                    status=status,
                    transaction_percent=marketing_scope.config.triumph_matrix_transaction_percent,
                    triumph=is_triumph,
                    matrix_max_length=marketing_scope.config.triumph_matrix_max_length,
                )
                transactions_data.extend(matrix_transactions_data)

                create_tasks_data.update({
                    "obj_id": inserted_node.id,
                    "engine_type": MatrixEngineType.NODES,
                })
                matrix_id = inserted_node.matrix_id
            else:
                result = await donate_service.handle_matrix_activation(
                    current_user=current_user,
                    sponsor=first_sponsor,
                    transactions_data=transactions_data,
                    status=status,
                    matrix_max_length=marketing_scope.config.matrix_max_length,
                )
                if not result:
                    await callback.message.delete()
                    await callback.message.answer(exc_user_message)

                    internal_exc_message = (
                        "DonateService.handle_matrix_activation failed. "
                        f"result: {result}"
                    )
                    loguru.logger.error(internal_exc_message)
                    raise ValueError(internal_exc_message)

                matrix, created_matrix = result
                create_tasks_data.update({
                    "obj_id": created_matrix.id,
                    "engine_type": MatrixEngineType.JSON,
                })
                matrix_id = matrix.id

            # region contest context point FIXME: move to service

            if status != DonateStatus.TEST:
                contest_point_user_id = None
                last_sponsor = None

                for sponsor in sponsors:
                    if not sponsor:
                        break

                    last_sponsor = sponsor
                    if sponsor.status not in (None, DonateStatus.TEST):
                        contest_point_user_id = sponsor.user_id
                        break

                if not contest_point_user_id and last_sponsor:
                    contest_point_user = await telegram_user_service.get_sponsor_recursively(
                        TelegramUser.status != None,
                        TelegramUser.status != DonateStatus.TEST,
                        sponsor_user_id=last_sponsor.user_id,
                    )

                    if contest_point_user:
                        contest_point_user_id = contest_point_user.user_id

                if contest_point_user_id:
                    await sponsors_contests_service.create_contest_point(
                        user_id=contest_point_user_id,
                        status=status
                    )
                    await update_sponsors_contest_task.kiq()

            # endregion

            if is_status_higher(
                    DonateStatus.GOLD,
                    status,
                    or_equal=True,
            ) and not current_user.private_channel_link_sent:
                current_user.private_channel_link_sent = True
                send_private_channel_link = True

            await apply_bot_matrix_tasks(**create_tasks_data)


        elif marketing_type is MatrixMarketingType.GLOBAL:
            inserted_node, matrix_transactions_data = await global_marketing_donate_service.execute(
                current_user_id=current_user.id,
                first_sponsor_id=first_sponsor.id,
                status=status,
                max_upline_depth=marketing_scope.config.matrix_max_level
            )
            transactions_data.extend(matrix_transactions_data)

            matrix_id = inserted_node.matrix_id
        else:
            internal_exc_message = f"Unsupported marketing type \"{marketing_type.name}\"."
            loguru.logger.error(internal_exc_message)
            raise ValueError(internal_exc_message)


        if not matrix_id:
            internal_exc_message = "matrix_id is not set."
            loguru.logger.error(internal_exc_message)
            raise ValueError(internal_exc_message)

        await donate_service.update_transactions_data_with_system_transaction(
            transactions_data,
            donate_sum=status.amount,
        )

        donate = await donate_confirm_service.create_donate(
            telegram_user_id=current_user.id,
            transactions=transactions_data,
            matrix_id=matrix_id,
            quantity=status.amount,
        )

        await telegram_user_service.increment_bill(
            telegram_user_id=current_user.id,
            bill_type=bill_type,
            amount=-status.amount,
        )
        await donate_confirm_service.update_bills_by_donate_id(
            donate_id=donate.id,
            is_triumph=is_triumph,
        )

        if is_status_higher(
            current_user_status,
            status,
        ):
            setattr(current_user, marketing_scope.status_orm_attr, status)

        matrix_activations_count = await statistic_service.increment_matrix_activations_count()
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()

    await callback.message.delete()
    await callback.message.answer("🎉")
    await callback.message.answer(
        "<b>Площадка успешно активирована, бот начал свою работу ✅</b>"
    )
    await send_donations_menu_task.kiq(
        callback.from_user.id,
        marketing_type_name=marketing_type.name,
        status_name=status.name,
        current_user_id=current_user.id,
    )

    if send_private_channel_link:
        limited_link_obj = await bot.create_chat_invite_link(
            chat_id=settings.private_channel_id,
            member_limit=1,
        )
        inline_keyboard = InlineKeyboardBuilder()
        inline_keyboard.add(InlineKeyboardButton(
            text="VIP Клуб KOD💵DENEG",
            url=limited_link_obj.invite_link
        ))
        await send_photo_task.kiq(
            chat_id=callback.from_user.id,
            file_path=settings.private_channel_invite_image_file_path,
            file_id_path=settings.private_channel_invite_image_file_id_path,
            caption=private_channel_invite_message.format(limited_link_obj.invite_link),
            reply_markup=inline_keyboard.as_markup(),
            delay=0.2,
        )

    if marketing_type is MatrixMarketingType.START:
        is_increase_triumph_bills_step = (
                matrix_activations_count
                % settings.start_marketing.triumph_bills_increase_activation_interval == 0
        )
        if matrix_activations_count != 0 and is_increase_triumph_bills_step:
            await increase_triumph_bills_task.kiq()
            chat_ids = [settings.donates_channel_id]
            chat_ids.extend(
                await telegram_user_service
                .get_user_ids_by_active_triumph_bill()
            )
            await mass_mailing_task_by_batches_task.kiq(
                chat_ids=chat_ids,
                text=increase_triumph_bills_message_text,
            )

    await matrix_activation_notifier_service.notify_invited_users(
        sponsor_user_id=current_user.user_id,
        status=status,
    )
    await asyncio.gather(*[
        matrix_activation_notifier_service
        .send_transaction_message(transaction)
        for transaction in transactions_data
    ])


@donate_router.callback_query(
    MarketingTypeFilter("transactions")
)
@inject
async def get_transactions_menu(
        callback: CallbackQuery,
        current_user: TelegramUser,
        marketing_type: MatrixMarketingType,
) -> None:
    buttons = {
        "Транзакции мне 📈": f"{marketing_type.label}_transactions_to_me_1",
        "Транзакции от меня 📉": f"{marketing_type.label}_transactions_from_me_1",
    }
    if current_user.is_admin:
        buttons.update({
            "Все транзакции 📊": f"{marketing_type.label}_all_transactions_1",
            "Транзакции в Сейф Триумф": "triumph_bill_transactions_1",
        })

    buttons["🔙 Назад"] = f"{marketing_type.label}_donations"

    await callback.message.edit_text(
        "В этом разделе вы можете посмотреть информацию о подтверждении транзакций по подаркам.\n"
        "Выберете раздел:",
        reply_markup=get_donate_keyboard(buttons=buttons),
    )


@donate_router.callback_query(MarketingTypeFilter("transactions_to_me"))
@inject
async def get_transactions_list_to_me(
        callback: CallbackQuery,
        current_user: TelegramUser,
        marketing_scope: MatrixMarketingScope,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
        donate_service: DonateService = Provide[Container.donate_service],
) -> None:
    page_number = int(callback.data.split("_")[-1])

    transactions = await donate_confirm_service.get_donate_transaction_by_sponsor_id(
        sponsor_id=current_user.id,
    )

    paginator = Paginator(transactions, page_number=page_number, per_page=5)
    buttons = {}
    sizes = (1, 1)

    if paginator.has_previous():
        buttons |= {"◀ Пред.": f"transactions_to_me_{page_number - 1}"}
    if paginator.has_next():
        buttons |= {"След. ▶": f"transactions_to_me_{page_number + 1}"}

    if len(buttons) == 2:
        sizes = (2, 1)

    message = "Транзакции от Вам.\n\n"
    transactions = paginator.get_page()

    if transactions:
        for transaction in transactions:
            created_at_format = \
                to_main_tz(transaction.created_at).strftime("%d.%m.%Y %H:%M")
            quantity_str = format_decimal(transaction.quantity)
            message += (
                f"ID: {transaction.id}\n"
                f"Сумма: ${quantity_str}\n"
                f"Дата и время: {created_at_format}\n"
            )
            if transaction.type_ == DonateTransactionType.SYSTEM:
                message += "<b>СИСТЕМНЫЙ АККАУНТ.</b>\n\n"
                continue

            donate = await donate_confirm_service.get_donate_by_id(
                donate_id=transaction.donate_id
            )
            if transaction.type_ == DonateTransactionType.SPONSOR:
                sender = await telegram_user_service.get_telegram_user(
                    id=donate.telegram_user_id
                )
                sponsor_depth = donate_service.get_sponsor_depth(
                    transaction.quantity,
                    donate.quantity,
                    marketing_scope=marketing_scope,
                )
                message += f"<b>От партнера {sponsor_depth} линии @{sender.username}.</b>\n\n"
            elif transaction.type_ == DonateTransactionType.MATRIX:
                status = donate_confirm_service.get_donate_status(donate.quantity)
                message += f"<b>Площадка {status.label}.</b>\n\n"

            else:
                continue
    else:
        message = "У вас нет транзакций"

    buttons["🔙 Назад"] = f"transactions"
    await callback.message.edit_text(
        message,
        reply_markup=get_donate_keyboard(
            buttons=buttons,
            sizes=sizes,
        ),
    )


@donate_router.callback_query(F.data.startswith("transactions_from_me_"))
@inject
async def get_transactions_list_from_me(
        callback: CallbackQuery,
        current_user: TelegramUser,
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
) -> None:
    page_number = int(callback.data.split("_")[-1])

    donates = await donate_confirm_service.get_all_my_donates_and_transactions(
        telegram_user_id=current_user.id,
    )

    paginator = Paginator(list(donates.items()), page_number=page_number, per_page=3)
    buttons = {}
    sizes = (1, 1)
    message = "<b><u>Ваши транзакции</u></b>\n\n"

    donates = paginator.get_page()
    if donates:
        for donate, transactions in donates:
            created_at_format = \
                to_main_tz(donate.created_at).strftime("%d.%m.%Y %H:%M")
            quantity_str = format_decimal(donate.quantity)
            message += (
                f"<b><u>Подарок на сумму: "
                f"${quantity_str}</u></b>\n"
                f"ID: {donate.id}\n"
                f"Дата и время: {created_at_format}\n\n"
            )
    else:
        message = "У Вас нет подарков"

    if paginator.has_previous():
        buttons |= {"◀ Пред.": f"transactions_from_me_{page_number - 1}"}
    if paginator.has_next():
        buttons |= {"След. ▶": f"transactions_from_me_{page_number + 1}"}

    if len(buttons) == 2:
        sizes = (2, 1)

    buttons["🔙 Назад"] = f"transactions"

    await callback.message.edit_text(
        message,
        parse_mode="HTML",
        reply_markup=get_donate_keyboard(buttons=buttons, sizes=sizes),
    )


@donate_router.callback_query(F.data.startswith("all_transactions_"))
@inject
async def get_all_transactions(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
) -> None:
    page_number = int(callback.data.split("_")[-1])
    donates_and_transactions = (
        await donate_confirm_service.get_all_donates_and_transactions()
    )

    paginator = Paginator(
        list(donates_and_transactions.items()), page_number=page_number, per_page=3
    )
    buttons = {}
    sizes = (1, 1)
    message = "Все подарки и транзакции\n\n"
    donates_and_transactions = paginator.get_page()

    if paginator.has_previous():
        buttons |= {"◀ Пред.": f"all_transactions_{page_number - 1}"}
    if paginator.has_next():
        buttons |= {"След. ▶": f"all_transactions_{page_number + 1}"}

    if len(buttons) == 2:
        sizes = (2, 1)

    if donates_and_transactions:
        for donate, transactions in paginator.get_page():
            user = await telegram_user_service.get_telegram_user(
                id=donate.telegram_user_id
            )
            created_at_format = \
                to_main_tz(donate.created_at).strftime("%d.%m.%Y %H:%M")
            donate_quantity_str = format_decimal(donate.quantity)

            message += (
                f"<b><u>Подарок на сумму: "
                f"${donate_quantity_str}</u></b>\n"
                f"ID: {donate.id}\n"
                f"Дата и время: {created_at_format}\n"
            )
            message += "Транзакции по подарку: \n\n"
            if transactions:
                for transaction in transactions:
                    sponsor = await telegram_user_service.get_telegram_user(
                        id=transaction.sponsor_id
                    )
                    transaction_quantity_str = format_decimal(transaction.quantity)
                    message += (
                        f"ID: {transaction.id}\n"
                        f"Сумма: ${transaction_quantity_str}\n"
                        f"От кого: @{user.username}\n"
                        f"Кому: @{sponsor.username}\n"
                        f"Тип: <b>{transaction.type_.value.upper()}</b>\n"
                    )
                    if user.is_bot:
                        message += \
                            f"<b><em>-{transaction_quantity_str} от системного баланса.</em></b>\n"

                    message += "\n"

    buttons["🔙 Назад"] = f"transactions"
    await callback.message.edit_text(
        message,
        parse_mode="HTML",
        reply_markup=get_donate_keyboard(
            buttons=buttons,
            sizes=sizes,
        ),
    )

