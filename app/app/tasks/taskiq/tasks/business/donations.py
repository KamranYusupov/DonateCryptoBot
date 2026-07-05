from app.core.taskiq import broker
from app.db.commit_decorator import commit_and_close_session
from app.loader import bot
from app.tasks.taskiq.dependencies.container import ContainerDependency
from app.use_cases.donations import send_donations_menu


@broker.task
@commit_and_close_session
async def send_donations_menu_task(
        chat_id: int,
        current_user_id: str,
        *,
        container: ContainerDependency,
) -> None:
    await send_donations_menu(
        from_user_id=chat_id,
        current_user_id=current_user_id,
        telegram_method=bot.send_message,
        telegram_user_service=container.telegram_user_service(),
        matrix_service=container.matrix_service(),
        matrix_node_service=container.matrix_node_service(),
        sponsors_contests_service=container.sponsors_contests_service(),
        statistic_service=container.statistic_service(),
    )
