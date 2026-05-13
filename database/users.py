from sqlalchemy import select, func
from database.db import Users, async_session, Words, UserWords, WordsTopics


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

