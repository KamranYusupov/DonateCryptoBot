import html
import uuid
from datetime import datetime, timedelta
from typing import Any, Tuple, List, Optional

import loguru
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.keyboards.donate import get_donations_buttons, get_start_marketing_donations_buttons, \
    get_global_marketing_donations_buttons
from app.keyboards.inline import get_inline_buttons_from_dict
from app.loader import bot
from app.models import Matrix
from app.models.telegram_user import (
    DonateStatus,
    TelegramUser,
    GlobalMarketingDonateStatus,
)
from app.services.matrix_node_service import MatrixNodeService
from app.services.matrix_service import MatrixService
from app.services.sponsors_contest_service import SponsorsContestService
from app.services.statistic_service import StatisticService
from app.services.telegram_user_service import TelegramUserService
from app.utils.matrix import get_main_matrices
from app.utils.texts import (
    places_emoji_list,
    get_matrices_statuses_statistic_message,
    get_matrices_length_statistic_message,
    format_decimal,
    admin_statistic_message_text_template,
    start_main_message_text_template,
    start_base_message_text_template,
    global_main_message_text_template,
    global_base_message_text_template, get_global_node_statistic_message,
)
from app.utils.texts import get_triumph_bill_increase_statistic_text
from app.models.matrix import MatrixMarketingType, MatrixNode
from app.schemas.marketing import MatrixMarketingScope
from app.core.config import settings


class SendDonationsMenuUseCase:
    """
    Use Case для генерации и отправки меню донатов.
    """

    def __init__(
            self,
            telegram_user_service: TelegramUserService,
            matrix_service: MatrixService,
            matrix_node_service: MatrixNodeService,
            sponsors_contests_service: SponsorsContestService,
            statistic_service: StatisticService,
    ):
        self.telegram_user_service = telegram_user_service
        self.matrix_service = matrix_service
        self.matrix_node_service = matrix_node_service
        self.sponsors_contests_service = sponsors_contests_service
        self.statistic_service = statistic_service

    async def execute(
            self,
            marketing_scope: MatrixMarketingScope,
            from_user_id: int,
            current_user_id: uuid.UUID,
            telegram_method,
            callback_suffix: str,
            real_user: TelegramUser | None = None,
    ) -> None:
        if not isinstance(current_user_id, uuid.UUID):
            return None

        current_user = await self.telegram_user_service.get_telegram_user(id=current_user_id)
        if not current_user:
            return None

        execute_kwargs = {
            "marketing_scope": marketing_scope,
            "from_user_id": from_user_id,
            "current_user": current_user,
            "telegram_method": telegram_method,
            "callback_suffix": callback_suffix,
            "real_user": real_user,
        }

        match marketing_scope.marketing_type:
            case MatrixMarketingType.START:
                return await self._execute_start(**execute_kwargs)
            case MatrixMarketingType.GLOBAL:
                return await self._execute_global(**execute_kwargs)
            case _:
                raise ValueError(f"\"{marketing_scope.marketing_type}\" is not supported")


    async def _execute_start(
            self,
            marketing_scope: MatrixMarketingScope,
            from_user_id: int,
            current_user: TelegramUser,
            telegram_method,
            callback_suffix: str,
            real_user: TelegramUser | None = None,
    ) -> None:
        contest_place_text = await self._get_contest_place_text(current_user)
        base_message_text = start_base_message_text_template.format(
            current_user_place=contest_place_text,
            invites_count=current_user.invites_count,
            bill_for_activation=format_decimal(current_user.bill_for_activation),
            bill_for_withdraw=format_decimal(current_user.bill_for_withdraw),
            donates_sum=format_decimal(current_user.donates_sum),
        )

        if current_user.is_admin:
            await self._send_admin_statistic_menu(
                current_user,
                telegram_method,
                from_user_id,
                base_message_text,
                marketing_scope,
            )
            return

        triumph_node = await self.matrix_node_service.get_node(
            owner_id=current_user.id,
            matrix_status=DonateStatus.BRILLIANT,
            marketing_type=marketing_scope.marketing_type,
        )

        matrices_text = await self._get_matrices_length_text(
            current_user,
            MatrixMarketingType.START,
            triumph_node.downline_count if triumph_node else None
        )
        sponsor = await self.telegram_user_service.get_telegram_user(user_id=current_user.sponsor_user_id)

        message_text = start_main_message_text_template.format(
            matrices_length_statistic_message=matrices_text,
            triumph_info=self._get_triumph_deadline_text(triumph_node),
            sponsor_username=sponsor.full_username,
            created_at_date_str=current_user.created_at.strftime("%d.%m.%Y"),
            base_message_text=base_message_text,
        )

        keyboard = await self._build_keyboard(
            current_user=current_user,
            callback_suffix=callback_suffix,
            marketing_scope=marketing_scope,
            real_user=real_user,
        )
        await self._send(telegram_method, from_user_id, message_text, keyboard)

    async def _execute_global(
            self,
            marketing_scope: MatrixMarketingScope,
            from_user_id: int,
            current_user: TelegramUser,
            telegram_method,
            callback_suffix: str,
            real_user: TelegramUser | None = None,
    ) -> None:
        base_message_text = global_base_message_text_template.format(
            invites_count=current_user.invites_count,
            bill_for_activation=format_decimal(current_user.bill_for_activation),
            bill_for_withdraw=format_decimal(current_user.bill_for_withdraw),
            donates_sum=format_decimal(current_user.donates_sum),
        )

        if current_user.is_admin:
            await self._send_admin_statistic_menu(
                current_user,
                telegram_method,
                from_user_id,
                base_message_text,
                marketing_scope,
            )
            return

        matrices_text = await self._get_matrices_length_text(
            current_user,
            MatrixMarketingType.GLOBAL,
            None,
        )
        sponsor = await self.telegram_user_service.get_telegram_user(user_id=current_user.sponsor_user_id)

        message_text = global_main_message_text_template.format(
            matrices_length_statistic_message=matrices_text,
            sponsor_username=sponsor.full_username,
            created_at_date_str=current_user.created_at.strftime("%d.%m.%Y"),
            base_message_text=base_message_text,
        )

        keyboard = await self._build_keyboard(
            current_user=current_user,
            callback_suffix=callback_suffix,
            marketing_scope=marketing_scope,
            real_user=real_user,
        )
        await self._send(telegram_method, from_user_id, message_text, keyboard)


    async def _send(self, telegram_method, from_user_id: int, text: str, reply_markup: InlineKeyboardMarkup) -> None:
        kwargs = {}
        if telegram_method.__name__ == 'send_message':
            kwargs["chat_id"] = from_user_id

        await telegram_method(**kwargs, text=text, reply_markup=reply_markup)

    async def _get_contest_place_text(self, current_user: TelegramUser) -> str:
        current_sponsors_contest, _ = await self.sponsors_contests_service.get_or_create_current_contest()
        current_user_contest_result = current_sponsors_contest.results.get(str(current_user.user_id), {})
        current_user_place = current_user_contest_result.get("place", "-")

        if isinstance(current_user_place, int) and 0 < current_user_place <= 10:
            return str(places_emoji_list[current_user_place - 1])
        return str(current_user_place)

    def _get_triumph_deadline_text(self, triumph_node: MatrixNode) -> str:
        if not triumph_node:
            return ""

        now = datetime.now(triumph_node.last_activation.tzinfo)
        triumph_node_expires_at = triumph_node.last_activation + timedelta(days=365)
        time_difference = triumph_node_expires_at - now
        triumph_node_expires_in_days = time_difference.days
        triumph_node_deadline_additional_str = ""

        if triumph_node_expires_in_days == 1:
            remaining_seconds = time_difference.seconds
            hours = remaining_seconds // 3600
            minutes = (remaining_seconds % 3600) // 60
            triumph_node_deadline_additional_str = f" {hours} ч. {minutes} мин."
        else:
            triumph_node_expires_in_days += 1

        triumph_node_deadline_str = f"{triumph_node_expires_in_days} дней {triumph_node_deadline_additional_str}"
        return f"Срок действия площадки <b>🏆 ТРИУМФ</b>: {triumph_node_deadline_str}\n\n"

    async def _get_matrices_length_text(
            self,
            current_user: TelegramUser,
            marketing_type: MatrixMarketingType,
            triumph_downline_count: Optional[int] = None
    ) -> str:
        if marketing_type == MatrixMarketingType.START:
            matrices = await self.matrix_service.get_list(
                Matrix.marketing_type == marketing_type,
                Matrix.status != DonateStatus.BRILLIANT,
                order_by_create_at=True,
                owner_id=current_user.id,
            )
            main_matrices = get_main_matrices(matrices)
            message_text = "Активные площадки: "

            if not main_matrices:
                message_text += "не открыты."
                return message_text

            message_text += "\n" + get_matrices_length_statistic_message(
                matrices=main_matrices,
                triumph_node_downline_count=triumph_downline_count,
            )
            return message_text


        elif marketing_type == MatrixMarketingType.GLOBAL:
            global_marketing_node = await self.matrix_node_service.get_node(
                owner_id=current_user.id,
                marketing_type=marketing_type,
            )
            message_text = "Активный уровень: "

            if not current_user.global_marketing_status:
                message_text += "не открыт."
                return message_text

            message_text += (
                f"<b>{current_user.global_marketing_status.emoji} "
                f"{current_user.global_marketing_status.label.upper()}</b>"
            )

            nodes_count_per_level = await self.matrix_node_service.get_downline_counts_per_level(
                matrix_id=global_marketing_node.matrix_id,
                level=global_marketing_node.level,
                position=global_marketing_node.position,
                max_level=settings.global_marketing.matrix_max_level
            )

            message_text += "\n" + get_global_node_statistic_message(
                nodes_count_per_level,
            )
            return message_text

        else:
            raise ValueError(f"Unknown marketing type: \"{marketing_type.name}\"")

    @staticmethod
    def _get_other_marketing_buttons(
            callback_suffix: str,
            current_marketing_type: MatrixMarketingType
    ) -> List[InlineKeyboardButton]:
         return [
            InlineKeyboardButton(
                text=marketing_type.title.upper(),
                callback_data=f"{marketing_type.label}_{callback_suffix}",
            )
            for marketing_type in list(MatrixMarketingType)
            if marketing_type is not current_marketing_type
        ]

    def _get_bill_action_buttons(
            self,
    ) -> Tuple[List[InlineKeyboardButton], List[int]]:
        buttons = [
            InlineKeyboardButton(text="📤 Вывести".upper(), callback_data="withdrawal_request", style="primary"),
            InlineKeyboardButton(text="Пополнить 📥".upper(), callback_data="start_buy_tokens_state", style="primary"),
            InlineKeyboardButton(text="Внутренний перевод 💸".upper(), callback_data="start_transfer", style="success"),
        ]
        return buttons, [2, 1]

    def _get_safe_button(
            self,
            current_user: TelegramUser,
            marketing_scope: MatrixMarketingScope,
    ) -> InlineKeyboardButton:
        safe_value = getattr(current_user, marketing_scope.user_safe_orm_attr)
        marketing_type = marketing_scope.marketing_type

        return InlineKeyboardButton(
            text=f"🏦 Сейф {marketing_type.title}: ${format_decimal(safe_value)}".upper(),
            callback_data=f"{marketing_type.label}_increment_safe",
            style="danger",
        )


    async def _build_keyboard(
            self,
            current_user: TelegramUser,
            callback_suffix: str,
            marketing_scope: MatrixMarketingScope,
            triumph_node: MatrixNode | None = None,
            real_user: TelegramUser | None = None,
    ) -> InlineKeyboardMarkup:
        marketing_type = marketing_scope.marketing_type
        if marketing_type is MatrixMarketingType.START:
            user_statuses = await self.matrix_service.get_unique_statuses_by_owner_id(
                owner_id=current_user.id,
            )
        elif marketing_type is MatrixMarketingType.GLOBAL:
            user_global_status = getattr(current_user, marketing_scope.status_orm_attr)
            user_global_status_index = user_global_status.index if user_global_status else None
            user_statuses = [
                s for s in marketing_type.status_enum
                if s.index <= user_global_status_index
            ] if user_global_status else []
        else:
            raise TypeError(f"Unsupported marketing type: {marketing_type}")

        if triumph_node:
            user_statuses.append(DonateStatus.BRILLIANT)

        inline_buttons = get_donations_buttons(
            user_statuses=user_statuses,
            marketing_type=marketing_type,
        )
        safe_button = self._get_safe_button(current_user, marketing_scope)
        inline_buttons.append(safe_button)
        sizes = [1] * len(inline_buttons)

        current_user_status = getattr(current_user, marketing_scope.status_orm_attr)

        if current_user_status is not None and marketing_type is MatrixMarketingType.START:
            inline_buttons.append(
                InlineKeyboardButton(
                    text="АКТИВНЫЕ ПЛОЩАДКИ",
                    callback_data="team_1")
            )
            sizes.append(1)
        elif current_user_status is not None and marketing_type is MatrixMarketingType.GLOBAL:
            inline_buttons.append(
                InlineKeyboardButton(
                    text="Транзакции 💳",
                    callback_data=f"{marketing_type.label}_transactions")
            )
            sizes.append(1)

        bill_action_buttons, bill_action_buttons_sizes = self._get_bill_action_buttons()
        inline_buttons.extend(bill_action_buttons)
        sizes.extend(bill_action_buttons_sizes)

        if real_user and real_user.is_admin:
            other_marketing_buttons = self._get_other_marketing_buttons(callback_suffix, marketing_type)
            inline_buttons.extend(other_marketing_buttons)
            sizes += [1] * len(other_marketing_buttons)

        keyboard = InlineKeyboardBuilder()
        keyboard.add(*inline_buttons)

        return keyboard.adjust(*sizes).as_markup()


    async def _send_admin_statistic_menu(
            self,
            current_user,
            telegram_method,
            from_user_id: int,
            base_message_text: str,
            marketing_scope: MatrixMarketingScope,
    ) -> None:
        admin_statistic = await self.statistic_service.get_admin_statistic()
        matrix_activation_count = await self.statistic_service.get_matrix_activations_count()
        registration_count = await self.statistic_service.get_registrations_count()
        triumph_text = get_triumph_bill_increase_statistic_text(matrix_activation_count, registration_count)

        users_count = await self.telegram_user_service.get_count(is_bot=False)
        not_active_count = await self.telegram_user_service.get_count(status=None, is_bot=False)
        owners_ids = await self.telegram_user_service.get_ids(is_bot=False)
        matrices = await self.matrix_service.get_list(Matrix.owner_id.in_(owners_ids))  # FIXME

        # matrix_statuses_msg = get_matrices_statuses_statistic_message(
        #     matrices=matrices,
        #     marketing_scope=marketing_scope,
        # )
        matrices_text = await self._get_matrices_length_text(
            current_user,
            MatrixMarketingType.GLOBAL,
        )

        bills_activation_sum = (
            await self.telegram_user_service.get_bills_for_activation_sum()
        ) - current_user.bill_for_activation
        bills_withdraw_sum = (
            await self.telegram_user_service.get_bills_for_withdraw_sum()
        ) - current_user.bill_for_withdraw

        withdraw_gte_10_count = await self.telegram_user_service.get_count(
            TelegramUser.bill_for_withdraw >= 10, TelegramUser.is_bot == False
        )
        withdraw_gte_10_sum = (await self.telegram_user_service.get_bills_for_withdraw_sum(
            TelegramUser.bill_for_withdraw >= 10, TelegramUser.is_bot == False
        )) - current_user.bill_for_withdraw

        triumph_bills_sum = await self.telegram_user_service.get_triumph_bills_sum()

        message_text = admin_statistic_message_text_template.format(
            users_count=users_count,
            matrix_statuses_statistic_message=matrices_text,
            users_count_with_not_active_status=not_active_count,
            total_donates_sum=format_decimal(admin_statistic.total_donates_sum),
            system_bill=format_decimal(admin_statistic.system_bill),
            triumph_system_bill=format_decimal(admin_statistic.triumph_system_bill),
            donates_sum_for_registration=format_decimal(admin_statistic.donates_sum_for_registration),
            bills_for_activation_sum=format_decimal(bills_activation_sum),
            bills_for_withdraw_sum=format_decimal(bills_withdraw_sum),
            bills_for_withdraw_gte_10_sum=format_decimal(withdraw_gte_10_sum),
            triumph_bills_sum=format_decimal(triumph_bills_sum),
            users_count_with_bill_for_withdraw_gte_10=withdraw_gte_10_count,
            triumph_bill_increase_statistic_text=triumph_text,
            base_message_text=base_message_text,
        )

        buttons = {
            "АКТИВНЫЕ ПЛОЩАДКИ": "team_1",
            "Транзакции 💳".upper(): f"{marketing_scope.marketing_type.label}_transactions",
            "Скачать базу ⬇️".upper(): "excel_users",
            "Заявки на вывод 💸".upper(): "withdrawal_requests_1",
            "Список забаненных пользователей 📇🅱️".upper(): "banned_users_1",
            "Внутренние переводы".upper(): "transfer-list_1",
            "Забанить пользователя 🔒".upper(): "ban_user",
        }
        inline_buttons = get_inline_buttons_from_dict(buttons)
        inline_buttons.append(
            InlineKeyboardButton(text="Внутренний перевод 💸".upper(), callback_data="start_transfer", style="success")
        )

        keyboard = InlineKeyboardBuilder()
        keyboard.add(*inline_buttons)
        sizes = [1] * len(inline_buttons)

        await self._send(telegram_method, from_user_id, message_text, keyboard.adjust(*sizes).as_markup())
