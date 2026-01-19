import random

from aiogram import types
from aiogram.dispatcher import FSMContext
from asgiref.sync import sync_to_async
from bot.dispatcher import dp, bot
from bot.states import ExamStates
from bot.utils import send_question, get_latest_user_answers, generate_and_send_exam_result
from apps.models import Exam, Question, User, UserAnswer

# /start
@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    user = await sync_to_async(
        User.objects.filter(telegram_id=telegram_id).first
    )()
    if user:
        exams = await sync_to_async(list)(Exam.objects.all())
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for exam in exams:
            kb.add(types.KeyboardButton(exam.name))
        await message.answer(
            f"👋 Xush kelibsiz, {user.first_name}!\n\nImtihonni tanlang:",
            reply_markup=kb
        )
        await ExamStates.waiting_for_exam.set()
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True))
    await message.answer(
        "Assalomu alaykum!\nIltimos, telefon raqamingizni yuboring 👇",
        reply_markup=kb
    )
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
    await send_question(bot,message.chat.id, state)



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
    await send_question(bot,message.chat.id, state)



@dp.message_handler(state=ExamStates.finished_exam)
async def finished_handler(message: types.Message, state: FSMContext):
    if message.text == "📄 Natijani yuklash":
        data = await state.get_data()
        user = await sync_to_async(User.objects.get)(
            telegram_id=message.from_user.id
        )
        await generate_and_send_exam_result(
            bot=bot,
            chat_id=message.chat.id,
            user=user,
            exam_id=data["exam_id"],
            total_questions=data.get("total_questions", 0)
        )
        return

    if message.text == "📝 Exams":
        exams = await sync_to_async(list)(Exam.objects.all())
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for exam in exams:
            kb.add(types.KeyboardButton(exam.name))

        await message.answer(
            "📚 Imtihonlardan birini tanlang:",
            reply_markup=kb
        )
        await ExamStates.waiting_for_exam.set()
        return
    await message.answer("❌ Iltimos, tugmalardan tanlang!")


