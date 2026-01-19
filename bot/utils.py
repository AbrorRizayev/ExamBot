from aiogram import types
from bot.states import ExamStates
import os
import pandas as pd
from asgiref.sync import sync_to_async
from apps.models import Exam, UserAnswer,Question


async def send_question(bot, chat_id: int, state):
    data = await state.get_data()
    questions = data["questions"]
    index = data["current_index"]

    if index >= len(questions):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("📄 Natijani yuklash", "📝 Exams")
        await bot.send_message(chat_id, "✅ Imtihon tugadi!", reply_markup=kb)
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


@sync_to_async
def get_latest_user_answers(user, exam_id, count):
    answers = list(
        UserAnswer.objects.filter(
            user=user,
            exam_id=exam_id
        ).select_related("question").order_by("-id")[:count]
    )
    return list(reversed(answers))




async def generate_and_send_exam_result(bot, chat_id, user, exam_id, total_questions):
    answers = await sync_to_async(list)(
        UserAnswer.objects.filter(
            user=user,
            exam_id=exam_id
        ).select_related("question").order_by("id")[:total_questions]
    )
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
        await bot.send_document(chat_id, f)

    os.remove(file_path)
    exams = await sync_to_async(list)(Exam.objects.all())
    return exams