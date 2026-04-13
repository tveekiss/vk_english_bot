import os
import asyncio
from datetime import datetime

from sqlalchemy import select, update

from database.db import Users, async_session, Words, UserWords

async def get_users_by_id(vk_id) -> Users:
    async with async_session() as session:
        user = await session.scalar(select(Users).where(Users.id == vk_id))

    return user

async def add_user(user_id):
    async with async_session() as session:
        user = Users(vk_id=364418333)
        session.add(user)
        await session.commit()

async def edit_user(vk_id):
    async with async_session() as session:
        user = get_users_by_id(vk_id)
        session.add(user)
        await session.commit()
