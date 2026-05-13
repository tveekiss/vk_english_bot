import asyncio
import json
import random

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
)


token = "vk1.a.ynkozQOPuhC19SfmXq7m5XkRKInLRZ5A5jg5ELC9XX5W5CIAGXA7ceAWVlVT-tcMq2OZ91Uujgtx7-tjw1zvyP0Mok4A3xYroAZwHVPFvu3Eny6PG-0QNI2Ev1lD9iUa8RjVYBpdXtHzMeNRKuoUjc5v6HzF2nLgGh2-0dKVYv_NEPcMnjB3JWGBeXSmAnhWFfbDnel2BN8K4XZeWp-tmQ"
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

    if text in ["Повторение", "Мини-игра", "Статистика"]:
        write_message(
            user_id,
            "Этот раздел сделаем позже 🙂\nПока доступно изучение слов.",
            main_menu_keyboard()
        )
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