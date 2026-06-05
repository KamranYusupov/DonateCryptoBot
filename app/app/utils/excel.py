from io import BytesIO

import loguru
import pandas as pd
from dependency_injector.wiring import inject, Provide

from app.core.container import Container
from app.models.telegram_user import TelegramUser, DonateStatus
from app.schemas.telegram_user import TelegramUserEntity
from app.services.telegram_user_service import TelegramUserService
from openpyxl.utils import get_column_letter
from app.utils.datetime import to_main_tz


@inject
async def export_users_to_excel(
        file_name: str,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
):
    """
    Экспортирует данные пользователй в Excel.
    """
    data = []

    users: list[TelegramUser] = await telegram_user_service.get_list(
        is_bot=False,
        join_sponsor=True
    )
    count = 1

    for user in users:
        data.append({
            "Порядок": count,
            "Уровень глубины": user.depth_level,
            "Логин ТГ": user.username,
            "Имя фамилия": user.full_name,
            "Логин тг пригласителя": user.sponsor,
            "Статус": user.status.value,
            "Кол-во приглашенных": user.invites_count,
            "Баланс для активации": user.bill_for_activation,
            "Баланс для вывода": user.bill_for_withdraw,
            "Всего заработано": user.donates_sum,
            "Tg ID": user.user_id,
            "Дата время регистрации": \
                to_main_tz(user.created_at).strftime("%d.%m.%Y %H:%M")
        })
        count += 1

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

        # Получаем активный лист
        worksheet = writer.sheets['Sheet1']

        # Устанавливаем ширину столбцов
        for idx, col in enumerate(df.columns):
            max_length = max(df[col].astype(str).map(len).max(), len(col))  # Максимальная длина
            adjusted_width = (max_length + 2)  # Добавляем немного пространства
            worksheet.column_dimensions[get_column_letter(idx + 1)].width = adjusted_width

    with open(file_name, 'wb') as f:
        f.write(output.getvalue())


@inject
async def import_users_from_excel(
    file_path: str,
    telegram_user_service: TelegramUserService = Provide[
        Container.telegram_user_service
    ],
):
    """
    Загружает пользователей из Excel-файла обратно в базу данных.
    Данные сортируются по глубине и дате регистрации для сохранения иерархии рефералов.
    """
    # 1. Читаем файл через pandas
    df = pd.read_excel(file_path)

    # 2. Приводим дату к правильному формату datetime для сортировки
    df["Дата время регистрации"] = pd.to_datetime(
        df["Дата время регистрации"], format="%d.%m.%Y %H:%M"
    )

    # 3. Сортируем: сначала глубина (0, 1, 2...), затем дата (от старых к новым)
    df = df.sort_values(
        by=["Уровень глубины", "Дата время регистрации"],
        ascending=[True, True]
    )

    # Локальный кэш для быстрой связи "username -> user_id",
    # чтобы не долбить базу лишними SELECT-запросами на каждой строке
    username_to_id_cache = {}

    loguru.logger.info(f"Начало импорта. Всего строк для обработки: {len(df)}")

    for _, row in df.iterrows():
        user_id = int(row["Tg ID"])
        username = str(row["Логин ТГ"]) if pd.notna(row["Логин ТГ"]) else None

        # Запоминаем юзернейм текущего пользователя в кэш для следующих строк
        if username:
            username_to_id_cache[username] = user_id

        # 4. Проверяем, существует ли уже пользователь в БД
        user_exists = await telegram_user_service.exists(user_id=user_id)
        if user_exists:
            loguru.logger.info(f"Пользователь {user_id} уже есть в базе. Пропускаем.")
            continue

        # 5. Парсим ФИО обратно на first_name и last_name
        full_name = str(row["Имя фамилия"]) if pd.notna(row["Имя фамилия"]) else ""
        name_parts = full_name.split(maxsplit=1)
        first_name = name_parts[0] if len(name_parts) > 0 else None
        last_name = name_parts[1] if len(name_parts) > 1 else None

        # 6. Восстанавливаем статус из Enum по его текстовому значению
        status_value = row["Статус"]
        try:
            user_status = DonateStatus(status_value)
        except ValueError:
            user_status = DonateStatus.NOT_ACTIVE

        sponsor_str = str(row["Логин тг пригласителя"]).strip() if pd.notna(row["Логин тг пригласителя"]) else None
        sponsor_user_id = None

        if sponsor_str and sponsor_str not in ("None", "nan", ""):
            if sponsor_str in username_to_id_cache:
                sponsor_user_id = username_to_id_cache[sponsor_str]
            else:
                sponsor_db = await telegram_user_service.get_telegram_user(username=sponsor_str)
                if sponsor_db:
                    sponsor_user_id = sponsor_db.user_id


        # 8. Собираем объект для отправки в сервис / репозиторий
        user_data = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "status": user_status,
            "sponsor_user_id": sponsor_user_id,
            "depth_level": int(row["Уровень глубины"]),
            "invites_count": int(row["Кол-во приглашенных"]),
            "bill_for_activation": float(row["Баланс для активации"]),
            "bill_for_withdraw": float(row["Баланс для вывода"]),
            "donates_sum": float(row["Всего заработано"]),
            "captcha_verified": True,
            "is_donate_for_registration_sent": True,
        }
        user = TelegramUserEntity(**user_data)
        user_schema_data = user.model_dump()
        user_schema_data.update({
            "created_at": row["Дата время регистрации"].to_pydatetime(),
        })
        await telegram_user_service.raw_create(user_schema_data)

    loguru.logger.info("Импорт успешно завершен!")