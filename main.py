import os
import random
import django
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from asgiref.sync import sync_to_async
import pandas as pd

# ===================
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
django.setup()
load_dotenv()

from apps.models import Exam, Question, User, UserAnswer

# =========================
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# states ==============
class ExamStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_name = State()
    waiting_for_exam = State()
    taking_exam = State()
    finished_exam = State()


# =========================

async def send_question(chat_id: int, state: FSMContext):
    data = await state.get_data()
    questions = data["questions"]
    index = data["current_index"]

    if index >= len(questions):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("📄 Natijani yuklash", "📝 Exams")
        await bot.send_message(chat_id, "✅ Imtihon tugadi! Natijani tanlang:", reply_markup=kb)
        await ExamStates.finished_exam.set()
        return

    question = await sync_to_async(Question.objects.get)(id=questions[index])

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("A", "B", "C", "D")

    text = (
        f"{question.text}\n\n"
        f"A) {question.option_a}\n"
        f"B) {question.option_b}\n"
        f"C) {question.option_c}\n"
        f"D) {question.option_d}"
    )

    await bot.send_message(chat_id, text, reply_markup=kb)
    await ExamStates.taking_exam.set()


# =========================
# Async ga yordanchu funk
@sync_to_async
def get_latest_user_answers(user, exam_id, count):
    answers = list(UserAnswer.objects.filter(
        user=user,
        exam_id=exam_id
    ).select_related('question').order_by('-id')[:count])
    return list(reversed(answers))
    return answers


# /start
@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True))
    await message.answer("Assalomu alaykum!\nIltimos, telefon raqamingizni yuboring 👇", reply_markup=kb)
    await ExamStates.waiting_for_phone.set()


@dp.message_handler(content_types=types.ContentType.CONTACT, state=ExamStates.waiting_for_phone)
async def phone_handler(message: types.Message, state: FSMContext):
    phone_number = message.contact.phone_number
    await state.update_data(phone_number=phone_number)
    await message.answer("Ism va familiyangizni yozing:", reply_markup=types.ReplyKeyboardRemove())
    await ExamStates.waiting_for_name.set()


@dp.message_handler(state=ExamStates.waiting_for_name)
async def name_handler(message: types.Message, state: FSMContext):
    full_name = message.text
    data = await state.get_data()
    user, created = await sync_to_async(User.objects.get_or_create)(
        telegram_id=message.from_user.id,
        defaults={"first_name": full_name, "phone_number": data["phone_number"]}
    )
    if not created:
        user.first_name = full_name
        user.phone_number = data["phone_number"]
        await sync_to_async(user.save)()

    exams = await sync_to_async(list)(Exam.objects.all())
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for exam in exams:
        kb.add(types.KeyboardButton(exam.name))
    await message.answer("Imtihonni tanlang:", reply_markup=kb)
    await ExamStates.waiting_for_exam.set()


@dp.message_handler(state=ExamStates.waiting_for_exam)
async def exam_handler(message: types.Message, state: FSMContext):
    try:
        exam = await sync_to_async(Exam.objects.get)(name=message.text)
    except Exam.DoesNotExist:
        await message.answer("❌ Iltimos, ro'yxatdan tanlang")
        return

    questions = await sync_to_async(list)(exam.questions.all())
    random.shuffle(questions)

    await state.update_data(
        exam_id=exam.id,
        questions=[q.id for q in questions],
        current_index=0,
        total_questions=len(questions)
    )
    await send_question(message.chat.id, state)


@dp.message_handler(lambda m: m.text in ["A", "B", "C", "D"], state=ExamStates.taking_exam)
async def answer_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    index = data["current_index"]
    question_id = data["questions"][index]

    question = await sync_to_async(Question.objects.get)(id=question_id)
    is_correct = question.correct_option == message.text

    user = await sync_to_async(User.objects.get)(telegram_id=message.from_user.id)

    await sync_to_async(UserAnswer.objects.create)(
        user=user,
        exam_id=data["exam_id"],
        question=question,
        selected_option=message.text,
        is_correct=is_correct
    )

    await state.update_data(current_index=index + 1)
    await send_question(message.chat.id, state)


@dp.message_handler(state=ExamStates.finished_exam)
async def finished_handler(message: types.Message, state: FSMContext):
    if message.text == "📄 Natijani yuklash":
        data = await state.get_data()
        user = await sync_to_async(User.objects.get)(telegram_id=message.from_user.id)

        total_questions = data.get("total_questions", 0)
        answers = await get_latest_user_answers(user, data["exam_id"], total_questions)

        correct_count = sum(ans.is_correct for ans in answers)
        wrong_count = len(answers) - correct_count

        rows = []
        for i, ans in enumerate(answers, 1):
            rows.append({
                "№": i,
                "Savol": ans.question.text,
                "Sizning javobingiz": ans.selected_option,
                "To'g'ri javob": ans.question.correct_option,
                "Natija": "✅" if ans.is_correct else "❌"
            })
        rows.append({
            "№": "",
            "Savol": "Umumiy natija",
            "Sizning javobingiz": "",
            "To'g'ri javob": "",
            "Natija": f"✅ {correct_count}, ❌ {wrong_count}"
        })

        file_path = f"{user.telegram_id}_exam_result.xlsx"
        df = pd.DataFrame(rows)
        df.to_excel(file_path, index=False)

        with open(file_path, "rb") as f:
            await bot.send_document(message.chat.id, f)

        os.remove(file_path)
        exams = await sync_to_async(list)(Exam.objects.all())
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for exam in exams:
            kb.add(types.KeyboardButton(exam.name))
        await message.answer("✅ Natija yuborildi!\n\nYangi imtihon tanlang:", reply_markup=kb)
        await ExamStates.waiting_for_exam.set()

    else:
        await message.answer("❌ Iltimos, tugmalardan tanlang!")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)