import asyncio
import keepalive
from config import BOT_TOKEN, USER_TOKEN
from selfbot import SelfBot
from client import RoleBot


async def main():
    keepalive.start()
    selfbot = SelfBot()
    bot = RoleBot(selfbot)

    async with asyncio.TaskGroup() as tg:
        tg.create_task(selfbot.start(USER_TOKEN))
        tg.create_task(bot.start(BOT_TOKEN))


if __name__ == "__main__":
    asyncio.run(main())
