import loguru
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError



async def handle_invoice_webhook_in_bot(
    bot: Bot,
    telegram_id: int,
    tokens_count: int,
    messages_to_delete_ids: list[int]
):
    from app.use_cases.donations import send_donations_menu

    for message_id in messages_to_delete_ids:
        try:
            await bot.delete_message(
                chat_id=telegram_id,
                message_id=message_id,
            )
        except TelegramAPIError:
            pass

    await bot.send_message(
        chat_id=telegram_id,
        text="Оплата прошла успешно ✅\n\n"
             f"На баланс зачислено {tokens_count} USDT.",
    )

    await send_donations_menu(
        from_user_id=telegram_id,
        telegram_method=bot.send_message
    )