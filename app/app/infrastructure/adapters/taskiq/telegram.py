from app.tasks.taskiq.tasks import send_message_task


class TelegramBotTaskIQAdapter:

    async def send_message(
            self,
            chat_id: int,
            text: str,
            **kwargs
    ) -> None:
        await send_message_task.kiq(
            chat_id=chat_id,
            text=text,
            **kwargs,
        )

