import asyncio
import os
from datetime import datetime
from decimal import Decimal

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile
from aiogram.types import Message
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
    mass_mailing_task,
)
from app.tasks.taskiq.tasks.business.donations import send_donations_menu_task
from app.tasks.taskiq.tasks.business.matrix import apply_bot_matrix_tasks
from app.tasks.taskiq.tasks.business.triumph_bill import increase_triumph_bills_task
from app.utils.pagination import Paginator
from app.utils.excel import export_users_to_excel
from app.models.donate import DonateTransactionType
from app.loader import bot
from app.utils.bot import send_captcha
from app.models.telegram_user import TelegramUser, BillType
from app.models.matrix import MatrixEngineType
from app.keyboards.donate import get_start_inline_keyboard
from app.utils.datetime import to_main_tz
from app.services.sponsors_contest_service import SponsorsContestService
from app.models.telegram_user import DonateStatus
from app.utils.bot import send_message_or_pass, delete_message_or_pass
from app.utils.bot import get_schema_from_user
from app.services.statistic_service import StatisticService
from app.keyboards.inline import get_subscriptions_keyboard, get_confirm_inline_keyboard
from app.utils.bot import send_subscription_menu
from app.states.captcha import CaptchaState
from app.use_cases.donations import send_donations_menu
from app.utils.texts import (
    format_decimal,
    increase_triumph_bills_message_text,
    registration_donate_triumph_bill_text,
)

donate_router = Router()


@donate_router.callback_query(F.data.startswith("yes_"))
@inject
async def captcha_handler(
        callback: CallbackQuery,
        state: FSMContext,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        session: Session = Provide[
            Container.session
        ]
) -> None:
    current_user_exists = await telegram_user_service.exists(
        user_id=callback.from_user.id,
    )
    if current_user_exists:
        return

    await state.clear()
    if not callback.from_user.username:
        await callback.message.answer(
            "Для регистрации добавьте пожалуйста <em>username</em> в свой telegram аккаунт",
            reply_markup=get_donate_keyboard(
                buttons={"Попробовать ещё раз": callback.data}
            )
        )
        return

    try:
        sponsor_user_id = int(callback.data.split("_")[-1])
        sponsor = await telegram_user_service.get_telegram_user(
            user_id=sponsor_user_id
        )
        user_schema = get_schema_from_user(
            callback.from_user,
            depth_level=sponsor.depth_level + 1,
            sponsor_user_id=sponsor_user_id,
        )

        current_user = await telegram_user_service.create_telegram_user(
            user=user_schema,
            sponsor=sponsor,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    await send_captcha(
        message=callback.message,
        state=state,
        sponsor_user_id=sponsor_user_id,
    )
    await state.set_state(CaptchaState.option)
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


@donate_router.callback_query(F.data.startswith("register_"))
@inject
async def register_handler(
        callback: CallbackQuery,
        state: FSMContext,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        matrix_service: MatrixService = Provide[Container.matrix_service],
        matrix_node_service: MatrixNodeService = Provide[
            Container.matrix_node_service
        ],
        sponsors_contests_service: SponsorsContestService = Provide[
            Container.sponsors_contests_service
        ],
        statistic_service: StatisticService = Provide[
            Container.statistic_service
        ],
        session: Session = Provide[
            Container.session
        ],
) -> None:
    current_user = await telegram_user_service.get_telegram_user(
        user_id=callback.from_user.id
    )
    captcha_id = callback.data.split("_")[-4]
    option, attempt, sponsor_user_id = map(int, callback.data.split("_")[-3:])

    if current_user.captcha_verified:
        await state.clear()
        await send_donations_menu(
            from_user_id=current_user.user_id,
            telegram_method=bot.send_message,
            telegram_user_service=telegram_user_service,
            matrix_service=matrix_service,
            matrix_node_service=matrix_node_service,
            sponsors_contests_service=sponsors_contests_service,
            statistic_service=statistic_service,
        )
        return

    now = datetime.now()
    state_data = await state.get_data()

    if captcha_id != state_data.get("captcha_id"):
        await callback.message.edit_text("Проверка устарела.")
        return

    captcha_expires_at = datetime.fromtimestamp(
        state_data["expires_at"]
    )

    if captcha_expires_at <= now:
        await send_captcha(
            message=callback.message,
            state=state,
            sponsor_user_id=sponsor_user_id,
            attempt=attempt,
            exception_text=(
                "❌⌛️ Время на решение вышло. "
                "Попробуйте еще раз."
            ),
        )
        return

    answer = int(state_data["answer"])
    if option != answer and attempt >= settings.math_captcha_max_attempts_count:
        await telegram_user_service.update(
            obj_id=current_user.id,
            obj_in=dict(is_banned=True),
        )
        session.commit()
        session.close()

        await delete_message_or_pass(callback.message)
        await callback.message.answer(
            "❌ Проверка не пройдена. \n\nВаш аккаунт заблокирован. "
            "Для снятия блокировки, свяжитесь со службой поддержки. "
            f"@{settings.support_username}"
        )
        await state.clear()
        return
    elif option != answer:
        await send_captcha(
            message=callback.message,
            state=state,
            sponsor_user_id=sponsor_user_id,
            attempt=attempt + 1,
            exception_text="❌ Неверный вариант ответа.",
        )
        return

    if not current_user.captcha_verified:
        await telegram_user_service.update(
            obj_id=current_user.id,
            obj_in=dict(captcha_verified=True),
        )
        session.commit()
        session.close()

    await delete_message_or_pass(callback.message)
    await state.clear()

    await send_subscription_menu(callback, sponsor_user_id)


@donate_router.callback_query(F.data.startswith("menu_"))
@inject
async def subscription_checker(
        callback: CallbackQuery,
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
        user_id=callback.from_user.id,
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


    current_user = await telegram_user_service.get_telegram_user(
        user_id=callback.from_user.id
    )
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
    if current_user.is_donate_for_registration_sent:
        return

    await telegram_user_service.update(
        obj_id=current_user.id,
        obj_in=dict(is_donate_for_registration_sent=True)
    )
    registration_count = statistic_service.increment_registrations_count()
    is_increase_triumph_bills_step = (
        registration_count
        % settings.triumph_bills_increase_registration_interval == 0
    )
    if registration_count != 0 and is_increase_triumph_bills_step:
        await increase_triumph_bills_task.kiq()
        await send_message_task.kiq(
            chat_id=settings.donates_channel_id,
            text=increase_triumph_bills_message_text,
        )

    if not settings.send_donate_for_registration:
        return

    is_sponsor_status_bronze_or_higher = (
        DonateStatus.BRONZE.get_status_donate_value()
        <= sponsor.status.get_status_donate_value()
    )
    if is_sponsor_status_bronze_or_higher and (
            sponsor.donates_sum_for_registration
            < settings.max_donates_sum_for_registration
    ):
        await telegram_user_service.increment_bill_for_registration(
            telegram_user_id=sponsor.id,
            bill_type=BillType.TRIUMPH,
            amount=settings.donate_for_registration
        )
        admin_statistic = statistic_service.get_admin_statistic()
        statistic_service.update_admin_statistic(
            donates_sum_for_registration=(
                admin_statistic.donates_sum_for_registration
                + settings.donate_for_registration
            )
        )

        await asyncio.gather(
            send_message_task.kiq(
                chat_id=sponsor.user_id,
                text=registration_donate_triumph_bill_text.format(
                    f"от {current_user.full_username}"
                ),
            ),
            send_message_task.kiq(
                chat_id=settings.donates_channel_id,
                text=registration_donate_triumph_bill_text.format(""),
            )
        )

@donate_router.callback_query(F.data.startswith("donations"))
@donate_router.message(F.text.lower() == "⚡️ активация")
@inject
async def donations_menu_handler(
        aiogram_type: Message | CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        matrix_service: MatrixService = Provide[Container.matrix_service],
        matrix_node_service: MatrixNodeService = Provide[
            Container.matrix_node_service
        ],
        sponsors_contests_service: SponsorsContestService = Provide[
            Container.sponsors_contests_service
        ],
        statistic_service: StatisticService = Provide[
            Container.statistic_service
        ],
) -> None:
    telegram_method = bot.send_message if isinstance(aiogram_type, Message) \
        else aiogram_type.message.edit_text

    await send_donations_menu(
        from_user_id=aiogram_type.from_user.id,
        telegram_method=telegram_method,
        telegram_user_service=telegram_user_service,
        matrix_service=matrix_service,
        matrix_node_service=matrix_node_service,
        sponsors_contests_service=sponsors_contests_service,
        statistic_service=statistic_service,
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


@donate_router.callback_query(F.data.startswith("send_donate_"))
@inject
async def confirm_donate(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:

    callback_donate_data = "_".join(callback.data.split("_")[1:])
    donate_sum = Decimal(callback_donate_data.split("_")[-2])
    bill_type = BillType(callback_donate_data.split("_")[-1])
    current_user = await telegram_user_service.get_telegram_user(
        user_id=callback.from_user.id
    )
    bill = current_user.get_bill_by_type(bill_type)
    need_to_buy_tokens = bill - donate_sum

    if need_to_buy_tokens < 0:
        need_to_buy_tokens = int(abs(need_to_buy_tokens))
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

    reply_markup = get_confirm_inline_keyboard(
        yes_button_data=callback_donate_data,
        no_button_data="donations",
        sizes=(2, 1),
    )

    manifest_str = f"<a href='{settings.manifest_link}'>манифестом</a>"
    await callback.message.edit_text(
        text=(
            f"Продолжая, вы соглашаетесь с {manifest_str}.\n\n"
            f"Для активации площадки с вашего баланса будет списано {int(donate_sum)} USDT.\n\n"
            "Продолжить?"
        ),
        disable_web_page_preview=True,
        reply_markup=reply_markup,
    )



@donate_router.callback_query(F.data.startswith("donate_"))
@inject
async def donate_handler(
        callback: CallbackQuery,
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
        session: Session = Provide[Container.session],
) -> None:
    try:
        bill_type = BillType(callback.data.split("_")[-1])
        donate_sum = Decimal(callback.data.split("_")[-2])
        current_user, *sponsors = await telegram_user_service.get_telegram_user_with_sponsors(
            user_id=callback.from_user.id
        )
        bill = current_user.get_bill_by_type(bill_type)
        updated_bill = bill - donate_sum

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

        status = donate_confirm_service.get_donate_status(donate_sum)
        if not status:
            return

        if not callback.from_user.username:
            await callback.message.edit_text(
                "Перед отправкой подарка, "
                "добавьте пожалуйста <em>username</em> в свой телеграм аккаунт"
            )
            return

        if callback.from_user.username != current_user.username:
            current_user.username = callback.from_user.username

        first_sponsor = sponsors[0]
        is_triumph = (status in (DonateStatus.BRILLIANT,))
        create_tasks_data = {"donate_sum": donate_sum}

        transactions_data = await donate_service.update_transactions_data_with_sponsors(
            current_user,
            *sponsors,
            donate_sum=donate_sum,
            status=status,
        )

        if is_triumph:
            inserted_node, upline_nodes = await matrix_node_service.activate_matrix_node(
                current_user_id=current_user.id,
                sponsor_id=first_sponsor.id,
                status=status,
            )
            matrix_transactions_data = await donate_service.update_transactions_data_with_nodes(
                upline_nodes,
                donate_sum=donate_sum,
                status=status,
                transaction_percent=settings.triumph_matrix_transaction_percent,
            )
            transactions_data.extend(matrix_transactions_data)

            create_tasks_data.update({
                "obj_id": inserted_node.id,
                "engine_type": MatrixEngineType.NODES,
            })
            matrix_id = inserted_node.matrix_id
        else:
            result = await donate_service.handle_matrix_activation(
                current_user,
                first_sponsor,
                donate_sum,
                transactions_data,
                status,
            )
            if not result:
                await callback.message.delete()
                await callback.message.answer(
                    "Непредвиденая ошибка. "
                    "Пожалуйста, обратитесь в службу поддержки "
                    f"@{settings.support_username}"
                )
                return

            matrix, created_matrix = result
            create_tasks_data.update({
                "obj_id": created_matrix.id,
                "engine_type": MatrixEngineType.JSON,
            })
            matrix_id = matrix.id

        donate_service.update_transactions_data_with_system_transaction(
            transactions_data,
            donate_sum=donate_sum,
        )
        donate = await donate_confirm_service.create_donate(
            telegram_user_id=current_user.id,
            transactions=transactions_data,
            matrix_id=matrix_id,
            quantity=donate_sum,
        )

        if status != DonateStatus.TEST:
            contest_point_user_id = None
            for sponsor in sponsors:
                if not sponsor:
                    break

                last_sponsor = sponsor
                if sponsor.status not in (DonateStatus.NOT_ACTIVE, DonateStatus.TEST):
                    contest_point_user_id = sponsor.user_id
                    break

            if not contest_point_user_id:
                contest_point_user = await telegram_user_service.get_sponsor_recursively(
                    TelegramUser.status != DonateStatus.NOT_ACTIVE,
                    TelegramUser.status != DonateStatus.TEST,
                    user_id=last_sponsor.user_id
                )

                contest_point_user_id = contest_point_user.user_id

            await sponsors_contests_service.create_contest_point(
                user_id=contest_point_user_id
            )

        await telegram_user_service.increment_bill(
            telegram_user_id=current_user.id,
            bill_type=bill_type,
            amount=-donate_sum,
        )
        await donate_confirm_service.update_bills_by_donate_id(
            donate_id=donate.id,
        )

        if current_user.status == DonateStatus.NOT_ACTIVE or (
                int(status.get_status_donate_value())
                > int(current_user.status.get_status_donate_value())
        ):
            current_user.status = status

        matrix_activations_count = statistic_service.increment_matrix_activations_count()
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

    is_increase_triumph_bills_step = (
        matrix_activations_count
        % settings.triumph_bills_increase_activation_interval == 0
    )
    await apply_bot_matrix_tasks(**create_tasks_data)
    await callback.message.delete()
    await callback.message.answer("🎉")
    await callback.message.answer(
        "<b>Площадка успешно активирована, бот начал свою работу ✅</b>"
    )
    await send_donations_menu_task.kiq(
        callback.from_user.id,
    )

    if matrix_activations_count != 0 and is_increase_triumph_bills_step:
        await increase_triumph_bills_task.kiq()
        await send_message_task.kiq(
            chat_id=settings.donates_channel_id,
            text=increase_triumph_bills_message_text,
        )

    await matrix_activation_notifier_service.notify_invited_users(
        sponsor_user_id=callback.from_user.id,
        status=status,
    )
    await asyncio.gather(*[
        matrix_activation_notifier_service
        .send_transaction_message(transaction)
        for transaction in transactions_data
    ])


@donate_router.callback_query(F.data == "transactions")
@inject
async def get_transactions_menu(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:
    buttons = {
        "Транзакции мне 📈": f"transactions_to_me_1",
        "Транзакции от меня 📉": f"transactions_from_me_1",
    }
    user_id = callback.from_user.id
    user = await telegram_user_service.get_telegram_user(user_id=user_id)
    if user.is_admin:
        buttons.update({
            "Все транзакции 📊": f"all_transactions_1",
            "Транзакции в Сейф Триумф": "triumph_bill_transactions_1",
        })

    buttons["🔙 Назад"] = f"donations"

    await callback.message.edit_text(
        "В этом разделе вы можете посмотреть информацию о подтверждении транзакций по подаркам.\n"
        "Выберете раздел:",
        reply_markup=get_donate_keyboard(buttons=buttons),
    )


@donate_router.callback_query(F.data.startswith("transactions_to_me_"))
@inject
async def get_transactions_list_to_me(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
        donate_service: DonateService = Provide[Container.donate_service],
) -> None:
    page_number = int(callback.data.split("_")[-1])

    user_id = callback.from_user.id
    user = await telegram_user_service.get_telegram_user(user_id=user_id)
    transactions = await donate_confirm_service.get_donate_transaction_by_sponsor_id(
        sponsor_id=user.id,
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
                    donate.quantity
                )
                message += f"<b>От партнера {sponsor_depth} линии @{sender.username}.</b>\n\n"
            elif transaction.type_ == DonateTransactionType.MATRIX:
                status = donate_confirm_service.get_donate_status(donate.quantity)
                message += f"<b>Площадка {status.value}.</b>\n\n"

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
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        donate_service: DonateService = Provide[Container.donate_service],
        matrix_service: MatrixService = Provide[Container.matrix_service],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
) -> None:
    page_number = int(callback.data.split("_")[-1])

    user_id = callback.from_user.id
    user = await telegram_user_service.get_telegram_user(user_id=user_id)
    donates = await donate_confirm_service.get_all_my_donates_and_transactions(
        telegram_user_id=user.id,
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

