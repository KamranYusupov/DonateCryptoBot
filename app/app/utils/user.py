from typing import Tuple


def parse_user_identifier(args_text: str) -> Tuple[int | None, str | None]:
    """
    Разбирает аргументы команды на ID или Username.
    Возвращает (user_id, username), где одно из значений всегда None.
    """
    cleaned_text = args_text.strip()

    if not cleaned_text:
        return None, None
    
    if cleaned_text.isdigit():
        return int(cleaned_text), None

    return None, cleaned_text.lstrip("@")