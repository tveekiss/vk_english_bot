from sqlalchemy import select, func
from database.db import Users, async_session, Words, UserWords, WordsTopics

from datetime import datetime, timedelta
from sqlalchemy import select, func


async def get_users_by_id(vk_id) -> Users | None:
    async with async_session() as session:
        return await session.scalar(select(Users).where(Users.vk_id == vk_id))


async def add_user(vk_id: int, name: str):
    async with async_session() as session:
        user = await session.scalar(select(Users).where(Users.vk_id == vk_id))

        if user is None:
            user = Users(vk_id=vk_id, name=name)
            session.add(user)
            await session.commit()

        return user


async def get_topics():
    async with async_session() as session:
        result = await session.execute(select(WordsTopics).order_by(WordsTopics.name))
        return result.unique().scalars().all()

async def get_topic_by_name(topic_name: str):
    async with async_session() as session:
        return await session.scalar(
            select(WordsTopics).where(WordsTopics.name == topic_name)
        )


async def get_random_unlearned_word(vk_id: int, topic_name: str):
    async with async_session() as session:
        user = await session.scalar(select(Users).where(Users.vk_id == vk_id))
        topic = await session.scalar(
            select(WordsTopics).where(WordsTopics.name == topic_name)
        )

        if user is None or topic is None:
            return None

        learned_words_query = select(UserWords.word_id).where(UserWords.user_id == user.id)

        word = await session.scalar(
            select(Words)
            .where(Words.topic_id == topic.id)
            .where(Words.id.not_in(learned_words_query))
            .order_by(func.random())
            .limit(1)
        )

        return word


async def get_answer_options(topic_id: int, correct_word_id: int):
    async with async_session() as session:
        correct_word = await session.scalar(
            select(Words).where(Words.id == correct_word_id)
        )

        wrong_result = await session.execute(
            select(Words)
            .where(Words.topic_id == topic_id)
            .where(Words.id != correct_word_id)
            .order_by(func.random())
            .limit(3)
        )

        wrong_words = wrong_result.unique().scalars().all()

        if correct_word is None or len(wrong_words) < 3:
            return None

        options = wrong_words + [correct_word]
        return options


async def add_user_word(vk_id: int, word_id: int, repeat: int):
    async with async_session() as session:
        user = await session.scalar(select(Users).where(Users.vk_id == vk_id))

        if user is None:
            return

        user_word = UserWords(
            user_id=user.id,
            word_id=word_id,
            repeat=repeat
        )

        session.add(user_word)
        await session.commit()

async def get_random_repeat_word(vk_id: int):
    async with async_session() as session:
        user = await session.scalar(select(Users).where(Users.vk_id == vk_id))

        if user is None:
            return None

        word = await session.scalar(
            select(Words)
            .join(UserWords, UserWords.word_id == Words.id)
            .where(UserWords.user_id == user.id)
            .where(UserWords.repeat > 0)
            .order_by(func.random())
            .limit(1)
        )

        return word


async def update_user_word_repeat(vk_id: int, word_id: int, delta: int):
    async with async_session() as session:
        user = await session.scalar(select(Users).where(Users.vk_id == vk_id))

        if user is None:
            return

        user_word = await session.scalar(
            select(UserWords)
            .where(UserWords.user_id == user.id)
            .where(UserWords.word_id == word_id)
        )

        if user_word is None:
            return

        user_word.repeat += delta

        if user_word.repeat < 0:
            user_word.repeat = 0

        await session.commit()


async def get_user_statistics(vk_id: int):
    async with async_session() as session:
        user = await session.scalar(select(Users).where(Users.vk_id == vk_id))

        if user is None:
            return None

        user_words_result = await session.execute(
            select(UserWords).where(UserWords.user_id == user.id)
        )

        user_words = user_words_result.unique().scalars().all()

        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        total_learned = len(user_words)

        learned_today = 0
        learned_week = 0
        learned_month = 0

        learning_dates = set()

        for user_word in user_words:
            try:
                word_date = datetime.strptime(user_word.date, "%d.%m.%Y").date()
            except ValueError:
                continue

            learning_dates.add(word_date)

            if word_date == today:
                learned_today += 1

            if word_date >= week_ago:
                learned_week += 1

            if word_date >= month_ago:
                learned_month += 1

        streak_days = 0
        current_date = today

        while current_date in learning_dates:
            streak_days += 1
            current_date -= timedelta(days=1)

        return {
            "total_learned": total_learned,
            "streak_days": streak_days,
            "learned_today": learned_today,
            "learned_week": learned_week,
            "learned_month": learned_month
        }