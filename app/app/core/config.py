import os
import secrets
from enum import Enum
from zoneinfo import ZoneInfo

from pydantic import PostgresDsn, Field, computed_field
from pydantic_settings import BaseSettings


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


def field_validator(param, mode):
    pass


class Settings(BaseSettings):
    """Настройки проекта"""

    # region Настройки бота
    bot_token: str = Field(title="Токен бота")
    bot_name: str = Field(title="Имя бота(username)")
    bot_link: str = Field(title="Ссылка на бота", default="https://t.me/{bot_name}")
    chat_id: int = Field(title="ID чата")
    chat_link: str = Field(title="Ссылка на чат")
    channel_id: str = Field(title="ID канала")
    channel_link: str = Field(title="Ссылка на канал")
    group_link: str = Field(title="Ссылка на чат")
    presentation_link: str = Field(title="Ссылка на презентацию")
    donates_channel_id: int = Field(title="ID канала с донатами")
    donates_channel_link: str = Field(title="Ссылка на канал с донатами")
    web_app_link: str = Field(title="Ссылка на web app")
    manifest_link: str = Field(title="Ссылка на манифест")
    message_per_second: float = Field(title="Кол-во сообщений в секунду", default=1)
    support_username: str = Field(title="Username аккаунта поддержки")
    log_level: LogLevel = Field(title="Уровень логирования", default=LogLevel.INFO)
    timezone: str = Field(default="Europe/Moscow")
    send_donate_for_registration: bool = Field(default=False)
    donate_for_registration: int = Field(default=1)
    withdrawal_min_tokens_count: int = Field(
        title="Минимальное количество токенов для вывода",
        default=10
    )
    # endregion

    # region API
    api_prefix: str = Field(title="Префикс API", default="/api")
    # endregion

    debug: bool = Field(title="Режим отладки")
    secret_key: str = Field(
        title="Секретный ключ", default_factory=lambda: secrets.token_hex(16)
    )

    # region Настройки БД
    postgres_user: str = Field(title="Пользователь БД")
    postgres_password: str = Field(title="Пароль БД")
    postgres_host: str = Field(title="Хост БД")
    postgres_port: int = Field(title="Порт ДБ", default="5432")
    postgres_db: str = Field(title="Название БД")
    database_url: PostgresDsn | None = Field(title="Ссылка БД", default=None)
    # endregion

    # region Настройки CryptoBot
    crypto_bot_api_token: str = Field(title="CryptoBot API token")
    crypto_bot_api_base_url: str = Field(
        title="CryptoBot API base url",
        default="https://pay.crypt.bot/api/",
    )
    # endregion

    # region Настройки проценты донатов
    first_sponsor_donate_percent: int = Field(title="Процент доната первому спонсору", default=20)
    second_sponsor_donate_percent: int = Field(title="Процент доната второму спонсору", default=10)
    third_sponsor_donate_percent: int = Field(title="Процент доната третьему спонсору", default=5)
    matrix_donate_percent: int = Field(title="Процент доната для матрицы", default=10)
    # endregion

    # region Настройки длины бинарной матрицы в 4ой степени (2⁴)
    level_length: int = Field(title="Длина первого уровня матрицы", default=2)
    second_level_length: int = Field(title="Длина второго уровня матрицы", default=4)
    third_level_length: int = Field(title="Длина третьего уровня матрицы", default=8)
    fourth_level_length: int = Field(title="Длина четвертого уровня матрицы", default=16)
    matrix_max_length: int = Field(title="Максимальная длина матрицы", default=30)
    matrix_max_level: int = Field(title="Максимальный уровень матрицы", default=4)
    # endregion

    # region Настройки Telegram server
    telegram_server_host: str = Field(
        title="Telegram Local Server host",
        default="telegram-server",
    )
    telegram_server_port: int = Field(title="Telegram Local Server port", default=8081)
    telegram_app_api_id: int = Field(title="Telegram App API ID")
    telegram_app_api_hash: str = Field(title="Telegram App API Hash")
    # endregion

    # region Настройки Worker
    add_bot_to_matrix_task_delay: int = Field(default=600)
    update_contests_task_delay: int = Field(default=300)
    # endregion

    # region Настройки Captcha
    captcha_seconds_interval: int = Field(title="Время на решение каптчи", default=60)
    math_captcha_options_count: int = Field(default=6)
    math_captcha_max_attempts_count: int = Field(default=2)
    # endregion


    add_bot_to_matrix_1_countdown_minutes: int = Field(
        title="Время ожидания первой задачи добавления бота в матрицу",
        default=5
    )
    add_bot_to_matrix_2_countdown_minutes: int = Field(
        title="Время ожидания второй задачи добавления бота в матрицу",
        default=15
    )

    @computed_field
    @property
    def timezone_info(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @computed_field
    @property
    def telegram_server_url(self) -> str:
        return f"http://{self.telegram_server_host}:{self.telegram_server_port}"

    @computed_field
    @property
    def postgres_url(self) -> PostgresDsn:
        if self.database_url:
            return self.database_url
        return PostgresDsn.build(
            scheme="postgresql",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            path=f"{self.postgres_db}",
        )


class Config:
    env_file = ".env"


settings = Settings()
