from app.tasks.taskiq.events import (
    on_worker_startup,
)
from app.tasks.taskiq.tasks import (
    send_db_backup_task,
    send_message_task,
    mass_mailing_task,
    add_bot_to_matrix_task,
    apply_bot_matrix_tasks,
    increase_triumph_bills_task,
    update_sponsors_contest_task,
    update_registration_contest_task,
)

__all__ = (
    "on_worker_startup",
    "add_bot_to_matrix_task",
    "apply_bot_matrix_tasks",
    "increase_triumph_bills_task",
    "send_db_backup_task",
    "send_message_task",
    "mass_mailing_task",
    "update_sponsors_contest_task",
    "update_registration_contest_task",
)