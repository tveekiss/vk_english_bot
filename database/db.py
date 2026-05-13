import os
import asyncio
from datetime import datetime

import pandas as pd

from sqlalchemy import ForeignKey, Column, BigInteger, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, MappedColumn
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # корень проекта
DB_PATH = os.path.join(BASE_DIR, "database/database.db")

engine = create_async_engine(
    f"sqlite+aiosqlite:///{DB_PATH}",
    echo=True
)

async_session = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class UserWords(Base):
    __tablename__ = 'users_words'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    word_id: Mapped[int] = mapped_column(ForeignKey('words.id', ondelete='CASCADE'))

    repeat: Mapped[int]
    date: Mapped[str] = mapped_column(
        default=lambda: datetime.now().strftime('%d.%m.%Y')
    )

    user: Mapped['Users'] = relationship(back_populates='words', lazy='joined')
    word: Mapped['Words'] = relationship(back_populates='users', lazy='joined')

    def __repr__(self):
        return f'Пользователь: {self.user}\nСлово: {self.word}\n кол-во повторений: {self.repeat}'



class Users(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    vk_id = Column(BigInteger, unique=True)

    name: Mapped[str]

    words: Mapped[list['UserWords']] = relationship(back_populates='user', lazy='joined')

    def __repr__(self):

        return f'айди: {self.vk_id}, Имя: {self.name}'


class WordsTopics(Base):
    __tablename__ = 'words_topics'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(unique=True)

    words: Mapped[list["Words"]] = relationship(back_populates="topic")






class Words(Base):
    __tablename__ = 'words'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    topic_id: Mapped[int] = mapped_column(ForeignKey('words_topics.id', ondelete='CASCADE'))
    eng: Mapped[str]
    rus: Mapped[str]

    users: Mapped[list['UserWords']] = relationship(back_populates='word', lazy='joined')

    topic: Mapped["WordsTopics"] = relationship(back_populates="words", lazy='joined')

async def get_or_create_topic(session, topic_name: str):
    result = await session.execute(
        select(WordsTopics).where(WordsTopics.name == topic_name)
    )
    topic = result.scalar_one_or_none()

    if topic:
        return topic

    topic = WordsTopics(name=topic_name)
    session.add(topic)
    await session.flush()  # чтобы появился id

    return topic


async def load_words(session):
    folder_path = "words"

    for file in os.listdir(folder_path):

        file_path = os.path.join(folder_path, file)
        df = pd.read_excel(file_path)

        # берём первые 2 столбца
        df = df.iloc[:, :2]
        df.columns = ["eng", "rus"]

        topic_name = os.path.splitext(file)[0]

        topic = await get_or_create_topic(session, topic_name)

        for _, row in df.iterrows():
            eng = row["eng"]
            rus = row["rus"]

            if pd.isna(eng) or pd.isna(rus):
                continue

            eng = str(eng).strip()
            rus = str(rus).strip()

            if not eng or not rus:
                continue

            word = Words(
                topic_id=topic.id,
                eng=eng,
                rus=rus
            )

            session.add(word)

async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        result = await session.execute(select(Words))
        words = result.scalars().all()

        if len(words) == 0:
            await load_words(session)
            await session.commit()

if __name__ == "__main__":
    asyncio.run(async_main())