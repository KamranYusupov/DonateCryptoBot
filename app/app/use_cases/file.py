from typing import Awaitable, Callable

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile

from app.utils.file_id import load_file_id, save_file_id


class SendFileFromLoadedFileIDOrSaveUseCase:

    @staticmethod
    async def __send_file_from_loaded_file_id_or_save(
            send_file_bot_method: Callable[..., Awaitable],
            send_file_argument_name: str,
            file_attr_name: str,
            chat_id: int,
            file_path: str,
            file_id_path: str,
            **kwargs,
    ):
        file_id = load_file_id(file_id_path)
        try:
            if file_id:
                kwargs[send_file_argument_name] = file_id
                await send_file_bot_method(
                    chat_id=chat_id,
                    **kwargs
                )
            else:
                raise ValueError("file_id not found")

        except (TelegramBadRequest, ValueError):
            file_obj = FSInputFile(file_path)

            kwargs[send_file_argument_name] = file_obj

            msg = await send_file_bot_method(
                chat_id=chat_id,
                **kwargs
            )

            file_attr = getattr(msg, file_attr_name)
            if isinstance(file_attr, list):
                file_attr = file_attr[0]
            if file_attr and file_attr.file_id:
                save_file_id(file_id_path, file_attr.file_id)

    @classmethod
    async def send_video(
            cls,
            bot: Bot,
            chat_id: int,
            file_path: str,
            file_id_path: str,
            **kwargs,
    ):
        await cls.__send_file_from_loaded_file_id_or_save(
            send_file_bot_method=bot.send_video,
            send_file_argument_name="video",
            file_attr_name="video",
            chat_id=chat_id,
            file_path=file_path,
            file_id_path=file_id_path,
            **kwargs,
        )

    @classmethod
    async def send_photo(
            cls,
            bot: Bot,
            chat_id: int,
            file_path: str,
            file_id_path: str,
            **kwargs,
    ):
        await cls.__send_file_from_loaded_file_id_or_save(
            send_file_bot_method=bot.send_photo,
            send_file_argument_name="photo",
            file_attr_name="photo",
            chat_id=chat_id,
            file_path=file_path,
            file_id_path=file_id_path,
            **kwargs,
        )

