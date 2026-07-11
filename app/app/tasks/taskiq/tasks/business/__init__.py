from app.tasks.taskiq.tasks.business.triumph_bill import increase_triumph_bills_task
from app.tasks.taskiq.tasks.business.matrix import (
    add_bot_to_matrix_task,
    apply_bot_matrix_tasks,
    send_matrix_transaction_message_task,
)
from app.tasks.taskiq.tasks.business.contest import (
    update_sponsors_contest_task,
    update_registration_contest_task,
)

__all__ = (
    "add_bot_to_matrix_task",
    "apply_bot_matrix_tasks",
    "send_matrix_transaction_message_task",
    "increase_triumph_bills_task",
    "update_sponsors_contest_task",
    "update_registration_contest_task",
)