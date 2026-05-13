import os
import asyncio
from datetime import datetime

from sqlalchemy import select, update

from database.db import Users, async_session, Words, UserWords

async def get_users_by_id(vk_id) -> Users:
    async with async_session() as session:
        user = await session.scalar(select(Users).where(Users.vk_id == vk_id))
    return user

async def add_user(vk_id: int, name: str):
    async with async_session() as session:
        if await get_users_by_id(vk_id) is None:
            user = Users(vk_id=vk_id, name=name)
            session.add(user)
            await session.commit()

