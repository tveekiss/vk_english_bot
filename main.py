import asyncio
import json
import random

from dotenv import load_dotenv
import os

import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id

from database.users import (
    add_user,
    get_topics,
    get_topic_by_name,
    get_random_unlearned_word,
    get_answer_options,
    add_user_word,
    get_random_repeat_word,
    update_user_word_repeat,
    get_user_statistics,
    get_random_game_word,
    set_user_word_repeat,
    update_user_max_streak,
    get_leaderboard,
)

load_dotenv()

token = os.getenv("VK_TOKEN")
authorize = vk_api.VkApi(token=token)

user_states = {}


def make_keyboard(buttons, one_time=False):
    keyboard = {
        "one_time": one_time,
        "buttons": []
    }

    for row in buttons:
        keyboard_row = []

        for text, color in row:
            keyboard_row.append({
                "action": {
                    "type": "text",
                    "label": text
                },
                "color": color
            })

        keyboard["buttons"].append(keyboard_row)

    return json.dumps(keyboard, ensure_ascii=False)


def main_menu_keyboard():
    return make_keyboard([
        [("Изучение", "positive"), ("Повторение", "primary")],
        [("Мини-игра", "secondary"), ("Статистика", "secondary")]
    ])


def write_message(user_id, message, keyboard=None):
    params = {
        "user_id": user_id,
        "message": message,
        "random_id": get_random_id()
    }

    if keyboard is not None:
        params["keyboard"] = keyboard

    authorize.method("messages.send", params)


def get_user_info(user_id):
    user_info = authorize.method("users.get", {"user_ids": user_id})
    return user_info[0]


async def send_start_message(user_id, user_name):
    await add_user(vk_id=user_id, name=user_name)

    user_states[user_id] = {
        "state": "main_menu"
    }

    write_message(
        user_id,
        f"Привет, {user_name}! 👋\n"
        f"Я бот для изучения английских слов.\n\n"
        f"Выбери, что хочешь сделать:",
        main_menu_keyboard()
    )


async def send_topics(user_id):
    topics = await get_topics()

    if not topics:
        write_message(
            user_id,
            "Темы пока не найдены в базе данных.",
            main_menu_keyboard()
        )
        return

    buttons = []
    row = []

    for topic in topics:
        row.append((topic.name, "positive"))

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([("Назад в меню", "negative")])

    user_states[user_id] = {
        "state": "choosing_topic"
    }

    write_message(
        user_id,
        "Выбери тему для изучения:",
        make_keyboard(buttons)
    )


async def send_learning_word(user_id, topic_name):
    word = await get_random_unlearned_word(user_id, topic_name)

    if word is None:
        write_message(
            user_id,
            "В этой теме больше нет новых слов для изучения 🎉",
            main_menu_keyboard()
        )

        user_states[user_id] = {
            "state": "main_menu"
        }
        return

    options = await get_answer_options(word.topic_id, word.id)

    if options is None:
        write_message(
            user_id,
            "В этой теме недостаточно слов для создания 4 вариантов ответа.",
            main_menu_keyboard()
        )

        user_states[user_id] = {
            "state": "main_menu"
        }
        return

    random.shuffle(options)

    answer_options = {}
    answer_text = ""

    for index, option in enumerate(options, start=1):
        number = str(index)
        answer_options[number] = option.rus
        answer_text += f"{number}. {option.rus}\n"

    buttons = [
        [("1", "positive"), ("2", "positive")],
        [("3", "positive"), ("4", "positive")],
        [("Назад в меню", "negative")]
    ]

    user_states[user_id] = {
        "state": "answering_word",
        "topic_name": topic_name,
        "word_id": word.id,
        "correct_answer": word.rus,
        "answer_options": answer_options
    }

    write_message(
        user_id,
        f"Как переводится слово:\n\n"
        f"🇬🇧 {word.eng}\n\n"
        f"Варианты ответа:\n"
        f"{answer_text}",
        make_keyboard(buttons)
    )


async def send_repeat_word(user_id):
    word = await get_random_repeat_word(user_id)

    if word is None:
        write_message(
            user_id,
            "Слов для повторения больше нет 🎉",
            main_menu_keyboard()
        )

        user_states[user_id] = {
            "state": "main_menu"
        }
        return

    options = await get_answer_options(word.topic_id, word.id)

    if options is None:
        write_message(
            user_id,
            "В этой теме недостаточно слов для создания 4 вариантов ответа.",
            main_menu_keyboard()
        )

        user_states[user_id] = {
            "state": "main_menu"
        }
        return

    random.shuffle(options)

    answer_options = {}
    answer_text = ""

    for index, option in enumerate(options, start=1):
        number = str(index)
        answer_options[number] = option.rus
        answer_text += f"{number}. {option.rus}\n"

    buttons = [
        [("1", "positive"), ("2", "positive")],
        [("3", "positive"), ("4", "positive")],
        [("Назад в меню", "negative")]
    ]

    user_states[user_id] = {
        "state": "answering_repeat_word",
        "word_id": word.id,
        "correct_answer": word.rus,
        "answer_options": answer_options
    }

    write_message(
        user_id,
        f"Повторение 🔁\n\n"
        f"Как переводится слово:\n\n"
        f"🇬🇧 {word.eng}\n\n"
        f"Варианты ответа:\n"
        f"{answer_text}",
        make_keyboard(buttons)
    )


def game_over_keyboard():
    return make_keyboard([
        [("Добавить в повторение", "positive")],
        [("Не добавлять", "secondary")],
        [("Назад в меню", "negative")]
    ])


async def send_game_word(user_id):
    old_state = user_states.get(user_id, {})
    used_word_ids = old_state.get("used_word_ids", [])

    word = await get_random_game_word(user_id, used_word_ids)

    if word is None:
        old_state = user_states.get(user_id, {})
        streak = old_state.get("streak", 0)

        is_new_record = await update_user_max_streak(user_id, streak)

        record_text = ""

        if is_new_record:
            record_text = "\n\nНовый рекорд! 🏆"

        write_message(
            user_id,
            f"Ты прошёл все доступные слова в мини-игре 🎉\n\n"
            f"Твоя серия: {streak} 🔥"
            f"{record_text}",
            main_menu_keyboard()
        )

        user_states[user_id] = {
            "state": "main_menu"
        }
        return

    options = await get_answer_options(word.topic_id, word.id)

    if options is None:
        write_message(
            user_id,
            "В этой теме недостаточно слов для создания 4 вариантов ответа.",
            main_menu_keyboard()
        )

        user_states[user_id] = {
            "state": "main_menu"
        }
        return

    random.shuffle(options)

    answer_options = {}
    answer_text = ""

    for index, option in enumerate(options, start=1):
        number = str(index)
        answer_options[number] = option.rus
        answer_text += f"{number}. {option.rus}\n"

    buttons = [
        [("1", "positive"), ("2", "positive")],
        [("3", "positive"), ("4", "positive")],
        [("Назад в меню", "negative")]
    ]

    old_state = user_states.get(user_id, {})
    streak = old_state.get("streak", 0)
    used_word_ids = old_state.get("used_word_ids", [])
    used_word_ids.append(word.id)

    user_states[user_id] = {
        "state": "answering_game_word",
        "word_id": word.id,
        "correct_answer": word.rus,
        "answer_options": answer_options,
        "streak": streak,
        "used_word_ids": used_word_ids
    }

    write_message(
        user_id,
        f"Мини-игра 🎮\n\n"
        f"Серия: {streak} 🔥\n\n"
        f"Как переводится слово:\n\n"
        f"🇬🇧 {word.eng}\n\n"
        f"Варианты ответа:\n"
        f"{answer_text}",
        make_keyboard(buttons)
    )


def statistics_keyboard():
    return make_keyboard([
        [("Таблица лидеров", "primary")],
        [("Назад в меню", "negative")]
    ])


async def send_leaderboard(user_id):
    leaders = await get_leaderboard()

    if not leaders:
        write_message(
            user_id,
            "Таблица лидеров пока пустая 🎮",
            statistics_keyboard()
        )
        return

    text = "🏆 Таблица лидеров:\n\n"

    for index, user in enumerate(leaders, start=1):
        text += f"{index}. {user.name} — {user.max_streak} 🔥\n"

    write_message(
        user_id,
        text,
        statistics_keyboard()
    )


async def send_statistics(user_id):
    statistics = await get_user_statistics(user_id)

    if statistics is None:
        write_message(
            user_id,
            "Не удалось найти твою статистику.",
            main_menu_keyboard()
        )
        return

    write_message(
        user_id,
        f"📊 Твоя статистика:\n\n"
        f"Всего слов изучено: {statistics['total_learned']}\n"
        f"Дней подряд занимаешься: {statistics['streak_days']}\n"
        f"Максимальная серия в мини-игре: {statistics['max_streak']} 🔥\n\n"
        f"Выучено слов сегодня: {statistics['learned_today']}\n"
        f"Выучено слов за неделю: {statistics['learned_week']}\n"
        f"Выучено слов за месяц: {statistics['learned_month']}",
        statistics_keyboard()
    )

async def handle_message(user_id, user_name, text):
    text = text.strip()

    if text.lower() in ["start", "/start", "начать", "привет"]:
        await send_start_message(user_id, user_name)
        return

    if text == "Назад в меню":
        await send_start_message(user_id, user_name)
        return

    state = user_states.get(user_id, {}).get("state")

    if text == "Изучение":
        await send_topics(user_id)
        return

    if text == "Повторение":
        await send_repeat_word(user_id)

        return

    if text == "Статистика":
        await send_statistics(user_id)
        return

    if text == "Таблица лидеров":
        await send_leaderboard(user_id)
        return

    if text == "Мини-игра":
        user_states[user_id] = {
            "state": "answering_game_word",
            "streak": 0,
            "used_word_ids": []
        }

        await send_game_word(user_id)
        return

    if state == "choosing_topic":
        topic = await get_topic_by_name(text)

        if topic is None:
            write_message(
                user_id,
                "Пожалуйста, выбери тему кнопкой ниже."
            )
            return

        await send_learning_word(user_id, topic.name)
        return

    if state == "answering_word":
        current_state = user_states[user_id]

        correct_answer = current_state["correct_answer"]
        word_id = current_state["word_id"]
        topic_name = current_state["topic_name"]
        answer_options = current_state["answer_options"]

        selected_answer = answer_options.get(text)

        if selected_answer is None:
            write_message(
                user_id,
                "Пожалуйста, выбери вариант кнопкой: 1, 2, 3 или 4."
            )
            return

        if selected_answer == correct_answer:
            await add_user_word(user_id, word_id, repeat=1)
            write_message(user_id, "Правильно! ✅")
        else:
            await add_user_word(user_id, word_id, repeat=3)
            write_message(
                user_id,
                f"Неправильно ❌\n"
                f"Правильный ответ: {correct_answer}"
            )

        await send_learning_word(user_id, topic_name)
        return

    if state == "answering_repeat_word":
        current_state = user_states[user_id]

        correct_answer = current_state["correct_answer"]
        word_id = current_state["word_id"]
        answer_options = current_state["answer_options"]

        selected_answer = answer_options.get(text)

        if selected_answer is None:
            write_message(
                user_id,
                "Пожалуйста, выбери вариант кнопкой: 1, 2, 3 или 4."
            )
            return

        if selected_answer == correct_answer:
            await update_user_word_repeat(user_id, word_id, delta=-1)
            write_message(user_id, "Правильно! ✅\nПовторений стало меньше.")
        else:
            await update_user_word_repeat(user_id, word_id, delta=1)
            write_message(
                user_id,
                f"Неправильно ❌\n"
                f"Правильный ответ: {correct_answer}\n"
                f"Это слово нужно будет повторить ещё раз."
            )

        await send_repeat_word(user_id)
        return

    if state == "answering_game_word":
        current_state = user_states[user_id]

        correct_answer = current_state["correct_answer"]
        word_id = current_state["word_id"]
        answer_options = current_state["answer_options"]
        streak = current_state["streak"]

        selected_answer = answer_options.get(text)

        if selected_answer is None:
            write_message(
                user_id,
                "Пожалуйста, выбери вариант кнопкой: 1, 2, 3 или 4."
            )
            return

        if selected_answer == correct_answer:
            used_word_ids = current_state.get("used_word_ids", [])
            user_states[user_id]["streak"] = streak + 1
            user_states[user_id]["used_word_ids"] = used_word_ids
            write_message(
                user_id,
                f"Правильно! ✅\n"
                f"Серия: {streak + 1} 🔥"
            )

            await send_game_word(user_id)
            return

        is_new_record = await update_user_max_streak(user_id, streak)

        record_text = ""

        if is_new_record:
            record_text = "\n\nНовый рекорд! 🏆"

        user_states[user_id] = {
            "state": "game_over",
            "word_id": word_id,
            "correct_answer": correct_answer,
            "streak": streak,
            "used_word_ids": current_state.get("used_word_ids", [])
        }

        write_message(
            user_id,
            f"Неправильно ❌\n\n"
            f"Правильный ответ: {correct_answer}\n"
            f"Твоя серия: {streak} 🔥"
            f"{record_text}\n\n"
            f"Хочешь добавить это слово в повторение?",
            game_over_keyboard()
        )
        return

    if state == "game_over":
        current_state = user_states[user_id]
        word_id = current_state["word_id"]

        if text == "Добавить в повторение":
            await set_user_word_repeat(user_id, word_id, repeat=1)

            write_message(
                user_id,
                "Слово добавлено в повторение 🔁",
                main_menu_keyboard()
            )

            user_states[user_id] = {
                "state": "main_menu"
            }
            return

        if text == "Не добавлять":
            write_message(
                user_id,
                "Хорошо, слово не добавлено в повторение.",
                main_menu_keyboard()
            )

            user_states[user_id] = {
                "state": "main_menu"
            }
            return

        write_message(
            user_id,
            "Выбери действие кнопкой ниже.",
            game_over_keyboard()
        )
        return

    await send_start_message(user_id, user_name)


async def main():
    long_poll = VkLongPoll(authorize)

    for event in long_poll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text:
            info = get_user_info(event.user_id)

            user_id = info["id"]
            user_name = info["first_name"]

            await handle_message(user_id, user_name, event.text)


if __name__ == "__main__":
    asyncio.run(main())