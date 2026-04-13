import asyncio

import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id

from database.users import add_user

token = 'vk1.a.ynkozQOPuhC19SfmXq7m5XkRKInLRZ5A5jg5ELC9XX5W5CIAGXA7ceAWVlVT-tcMq2OZ91Uujgtx7-tjw1zvyP0Mok4A3xYroAZwHVPFvu3Eny6PG-0QNI2Ev1lD9iUa8RjVYBpdXtHzMeNRKuoUjc5v6HzF2nLgGh2-0dKVYv_NEPcMnjB3JWGBeXSmAnhWFfbDnel2BN8K4XZeWp-tmQ'
authorize = vk_api.VkApi(token=token)

def write_message(user_id, message):
    authorize.method('messages.send', {'user_id': user_id, 'message': message, 'random_id': get_random_id()})




async def main():

    long_poll = VkLongPoll(authorize)
    for event in long_poll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text:
            resieved_message = event.text
            sender = event.user_id
            if resieved_message == 'Привет':
                write_message(sender, 'Пошел нахуй')
                await add_user(sender)



if __name__ == '__main__':
    asyncio.run(main())