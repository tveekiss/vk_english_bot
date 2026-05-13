import asyncio

import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id

from sqlalchemy import text

from database.db import async_session, DB_PATH

from database.users import add_user

token = 'vk1.a.ynkozQOPuhC19SfmXq7m5XkRKInLRZ5A5jg5ELC9XX5W5CIAGXA7ceAWVlVT-tcMq2OZ91Uujgtx7-tjw1zvyP0Mok4A3xYroAZwHVPFvu3Eny6PG-0QNI2Ev1lD9iUa8RjVYBpdXtHzMeNRKuoUjc5v6HzF2nLgGh2-0dKVYv_NEPcMnjB3JWGBeXSmAnhWFfbDnel2BN8K4XZeWp-tmQ'
authorize = vk_api.VkApi(token=token)

def write_message(user_id, message):
    authorize.method('messages.send', {'user_id': user_id, 'message': message, 'random_id': get_random_id()})

def get_user_info(id):
    user_info = authorize.method('users.get', {'user_ids': id})
    return user_info[0]




async def main():

    long_poll = VkLongPoll(authorize)
    for event in long_poll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text:
            resieved_message = event.text
            info = get_user_info(event.user_id)
            user_name = info['first_name']
            user_id = info['id']
            if resieved_message == 'Привет':
                write_message(user_id, f'Пошел нахуй, {user_name}!')
                await add_user(vk_id=user_id, name=user_name)




if __name__ == '__main__':
    asyncio.run(main())