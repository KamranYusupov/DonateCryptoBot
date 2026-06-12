from typing import NamedTuple, Union

class SendTextMessageTuple(NamedTuple):
    chat_id: Union[int, str]
    text: str