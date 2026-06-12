from aiogram.types import FSInputFile

from app.core.config import settings
from app.core.taskiq import broker
from app import loader
from app.db.backup import create_backup


@broker.task(
    schedule=[
        {
            "cron": "* * * * *",
        }
    ]
)
async def send_db_backup_task() -> None:
    file_path = await create_backup()
    backup_file = FSInputFile(file_path)
    await loader.bot.send_document(
        chat_id=settings.private_donates_channel_id,
        document=backup_file,
    )
