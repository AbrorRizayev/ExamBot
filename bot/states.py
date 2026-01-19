from aiogram.dispatcher.filters.state import State, StatesGroup


class ExamStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_name = State()
    waiting_for_exam = State()
    taking_exam = State()
    finished_exam = State()
