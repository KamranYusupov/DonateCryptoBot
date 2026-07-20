from typing import Protocol, Optional


class ITelegramBotProtocol(Protocol):

    async def send_message(
            self,
            chat_id: int,
            text: str,
            delay: Optional[int | float] = None,
            **kwargs
    ) -> None: ...
