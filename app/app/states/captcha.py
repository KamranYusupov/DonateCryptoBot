from aiogram.fsm.state import StatesGroup, State

class CaptchaState(StatesGroup):
    option = State()