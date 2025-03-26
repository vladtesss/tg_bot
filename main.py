import asyncio
from gspread_asyncio import AsyncioGspreadClientManager
from google.oauth2.service_account import Credentials
import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import F
from datetime import datetime

TOKEN = "7358499815:AAHPEkuMdRRR9UhA2obzR2ntEtYFCqry_y0"

SHEET_ID = "1qyB967ahF0X3GUGnKk82TbKfk3sUg3Y5q5lxJKhDkLc"
CREDENTIALS_FILE = "mindsetters-bot-a8e6dced4d15.json"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
def get_creds():
    return Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)


agcm = AsyncioGspreadClientManager(get_creds)

with open("questions.json", "r", encoding="utf-8") as file:
    tests = json.load(file)

KEYS = {
    "test1":{
        "Фізична агресія": {"k": 11, "plus": [1, 25, 33, 41, 48, 55, 62, 68], "minus":[9, 17]},
        "Вербальна агресія": {"k": 8, "plus": [7, 15, 23, 31, 46, 53, 60, 71, 73], "minus": [75, 39, 66, 74]},
        "Непряма агресія": {"k": 13, "plus": [2, 10, 18, 34, 42, 56, 63],"minus":[26, 49]},
        "Негативізм": {"k": 20, "plus": [4, 12, 20, 28], "minus":[36]},
        "Дратівливість": {"k": 9, "plus": [3, 19, 27, 43, 50, 57, 64, 72], "minus":[11, 35, 69]},
        "Схильність до підозр": {"k": 11, "plus": [6, 14, 22, 30, 38, 45, 52, 59], "minus":[65, 70]},
        "Образа": {"k": 13, "plus": [5, 13, 21, 29, 37, 44, 51, 58]},
        "Відчуття провини": {"k": 11, "plus": [8, 16, 24, 32, 40, 47, 54, 61, 67]}
    },

    "test2":{
            "Екстраверсія": {"plus": [1, 3, 8, 10, 13, 17, 22, 25, 27, 29, 39, 44, 46, 49, 53, 56],"minus": [5, 15, 20, 32, 34, 37, 41, 51]},
            "Нейротизм": { "plus": [2, 4, 7, 9, 11, 14, 16, 19, 21, 23, 26, 28, 31, 33, 36, 38, 40, 43, 45, 47, 50, 52, 55, 57]},
            "Відвертість": {"plus": [6, 24, 36], "minus": [12, 18, 30, 42, 48, 54]}
    }
}

bot = Bot(token=TOKEN)
dp = Dispatcher()

user_progress = {}


@dp.message(Command("start"))
async def start_command(message: types.Message):

    keyboard = InlineKeyboardBuilder()
    for test_name in tests.keys():
        keyboard.add(InlineKeyboardButton(text=test_name, callback_data=f"test_{test_name}"))

    await message.answer("""
        👋🏻Вітаю в боті!

Вам доступні наступні опитувачі:
🖌test1 - Методика вивчення схильності особи до агресивної поведінки  А. Басса та А.Даркі
🖌test2 - Особистісний опитувальник Айзенка
🖌test3 - Шкала PCL-5(Перелік симптомів ПТСР)
🖌test4 - Госпітальна шкала тривони і депресії(HADS)

📍Оберіть тест, який хочете пройти:""", reply_markup=keyboard.as_markup())


@dp.callback_query(F.data.startswith("test_"))
async def start_test(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    test_key = callback_query.data.split('_')[1]

    existing_results = await check_if_user_completed_test(user_id, test_key)

    if existing_results:
        result_text = "\n".join([f"{key}: {value}" for key, value in existing_results.items()])

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Пройти знову", callback_data=f"restart_{test_key}")],
                [InlineKeyboardButton(text="⬅️ Повернутись у меню", callback_data="back_to_menu")]
            ]
        )

        await callback_query.message.edit_text(
            text=f"✅ Ви вже проходили цей тест!\nОсь ваші результати:\n\n{result_text}\n\n"
                 f"Хочете пройти його ще раз?",
            reply_markup=keyboard
        )
    else:
        user_progress[user_id] = {"test": test_key, "index": 0, "answers": []}
        await show_question(user_id, callback_query.message.message_id)

    await callback_query.answer()


async def show_question(user_id, message_id):
    data = user_progress[user_id]
    test_key = data["test"]
    index = data["index"]
    total_questions = len(tests[test_key])

    if index < total_questions:
        question_data = tests[test_key][index]  # Отримуємо питання

        if test_key in ["test1", "test2"]:
            question_text = f"{index + 1} з {total_questions}\n{question_data}"
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="➖", callback_data="minus"),
                        InlineKeyboardButton(text="➕", callback_data="plus")
                    ]
                ]
            )

        elif test_key == "test3":
            question_text = f"{index + 1} з {total_questions}\n{question_data}"
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text=str(i), callback_data=f"score3_{i}")
                        for i in range(5)
                    ]
                ]
            )

        elif test_key == "test4":
            question_text = f"{index + 1} з {total_questions}\n{question_data['question']}"
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=option, callback_data=f"score4_{i}")]
                    for i, option in enumerate(question_data["options"])
                ]
            )

        await bot.edit_message_text(
            chat_id=user_id,
            message_id=message_id,
            text=question_text,
            reply_markup=keyboard
        )

    else:
        results = calculate_results(user_progress[user_id]["answers"], data["test"])
        await save_results(user_id, results, data["test"])
        result_text = "\n".join([f"{key}: {value}" for key, value in results.items()])
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Повернутись у меню", callback_data="back_to_menu")]
            ]
        )

        await bot.edit_message_text(
            chat_id=user_id,
            message_id=message_id,
            text=f"Обраховуємо ваші результати...\n{result_text}",
            reply_markup=keyboard
        )


@dp.callback_query(F.data.in_({"plus", "minus"}))
async def handle_answer(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in user_progress:
        return

    user_progress[user_id]["answers"].append(1 if callback_query.data == "plus" else 0)
    user_progress[user_id]["index"] += 1
    await show_question(user_id, callback_query.message.message_id)
    await callback_query.answer()


def calculate_results(answers, test_key):

    if test_key == "test3":  # PTSD (PCL-5)
        return {"Загальний бал": sum(answers)}

    elif test_key == "test4":  # Госпітальна шкала тривоги і депресії
        anxiety_score = sum(answers[i] for i in range(0, len(answers), 2))  # Непарні – Тривога
        depression_score = sum(answers[i] for i in range(1, len(answers), 2))  # Парні – Депресія
        return {"Тривога (A)": anxiety_score, "Депресія (D)": depression_score}

    elif test_key in KEYS:
        scores = {key: 0 for key in KEYS[test_key]}

        for category, values in KEYS[test_key].items():
            category_score = 0

            for q_num in values.get("plus", []):
                if answers[q_num - 1] == 1:
                    category_score += 1

            for q_num in values.get("minus", []):
                if answers[q_num - 1] == 0:
                    category_score += 1

            if test_key == "test1":
                category_score *= values["k"]

            scores[category] = category_score

        return scores

    return {}


async def save_results(user_id, results, test_key):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    answers = user_progress[user_id]["answers"]

    agc = await agcm.authorize()
    ss = await agc.open_by_key(SHEET_ID)

    sheet_name = "Op1" if test_key == "test1" else \
                 "Op2" if test_key == "test2" else \
                 "Op3" if test_key == "test3" else "Op4"

    sheet = await ss.worksheet(sheet_name)
    row = [timestamp, user_id]

    if test_key == "test3":
        sheet = await ss.worksheet("Op3")
        total_score = sum(answers)
        row = [timestamp, user_id, total_score] + answers

    elif test_key == "test4":
        sheet = await ss.worksheet("Op4")
        anxiety_score = sum(answers[i] for i in range(0, len(answers), 2))
        depression_score = sum(answers[i] for i in range(1, len(answers), 2))
        row = [timestamp, user_id, anxiety_score, depression_score] + answers

    else:
        row.extend(results.values())
        row.extend(answers)

    await sheet.append_row(row)

    if user_id in user_progress:
        del user_progress[user_id]



def get_scale_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="0", callback_data="score_0"),
            InlineKeyboardButton(text="1", callback_data="score_1"),
            InlineKeyboardButton(text="2", callback_data="score_2"),
            InlineKeyboardButton(text="3", callback_data="score_3"),
            InlineKeyboardButton(text="4", callback_data="score_4"),
        ]
    ])
    return keyboard


@dp.callback_query(F.data.startswith("score3_"))
async def handle_scale_answer_test3(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in user_progress:
        return

    score = int(callback_query.data.split("_")[1])
    user_progress[user_id]["answers"].append(score)
    user_progress[user_id]["index"] += 1

    await show_question(user_id, callback_query.message.message_id)
    await callback_query.answer()

@dp.callback_query(F.data.startswith("score4_"))
async def handle_scale_answer_test4(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in user_progress:
        return

    index = int(callback_query.data.split("_")[1])
    score = 4 - index

    user_progress[user_id]["answers"].append(score)
    user_progress[user_id]["index"] += 1

    await show_question(user_id, callback_query.message.message_id)
    await callback_query.answer()

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardBuilder()
    for test_name in tests.keys():
        keyboard.add(InlineKeyboardButton(text=test_name, callback_data=f"test_{test_name}"))

    await callback_query.message.edit_text(
        "\U0001F44B Вітаю в боті Mindsetters!\nОберіть тест, який хочете пройти:",
        reply_markup=keyboard.as_markup()
    )
    await callback_query.answer()


async def check_if_user_completed_test(user_id, test_key):
    agc = await agcm.authorize()
    ss = await agc.open_by_key(SHEET_ID)

    sheet_name = "Op1" if test_key == "test1" else \
        "Op2" if test_key == "test2" else \
            "Op3" if test_key == "test3" else "Op4"

    sheet = await ss.worksheet(sheet_name)
    records = await sheet.get_all_values()

    for row in records:
        if str(user_id) in row:
            if  test_key == "test3":
                return {"Загальний бал - ": row[2]}
            elif test_key == "test4":
                return {
                    "Тривога (A)": row[2],
                    "Депресія (D)": row[3]
                }
            elif test_key == "test1":
                categories = [
                    "Фізична агресія", "Вербальна агресія", "Непряма агресія",
                    "Негативізм", "Дратівливість", "Схильність до підозр",
                    "Образа", "Відчуття провини"
                ]
                return {categories[i]: row[i + 2] for i in range(len(categories))}
            else:
                categories = ["Екстраверсія", "Нейротизм", "Відвертість"]
                return {categories[i]: row[i + 2] for i in range(len(categories))}
    return None

async def delete_user_results(user_id, test_key):
    agc = await agcm.authorize()
    ss = await agc.open_by_key(SHEET_ID)
    sheet_name = "Op1" if test_key == "test1" else \
                 "Op2" if test_key == "test2" else \
                 "Op3" if test_key == "test3" else "Op4"

    sheet = await ss.worksheet(sheet_name)
    records = await sheet.get_all_values()

    for index, row in enumerate(records, start=1):
        if str(user_id) in row:
            await sheet.delete_rows(index)
            break


@dp.callback_query(F.data.startswith("restart_"))
async def restart_test(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    test_key = callback_query.data.split('_')[1]

    await delete_user_results(user_id, test_key)
    user_progress[user_id] = {"test": test_key, "index": 0, "answers": []}
    await show_question(user_id, callback_query.message.message_id) 

    await callback_query.answer("🔄 Ви починаєте тест з початку.")


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
