import asyncio
import keepalive
from config import BOT_TOKEN, USER_TOKEN
from utils.selfbot import SelfBot
from bot.client import RoleBot


async def main():
    # Запускаем HTTP keepalive сервер для Render + UptimeRobot
    keepalive.start()

    selfbot = SelfBot()
    bot = RoleBot(selfbot)

    # Запускаем оба клиента параллельно
    async with asyncio.TaskGroup() as tg:
        tg.create_task(selfbot.start(USER_TOKEN))
        tg.create_task(bot.start(BOT_TOKEN))


if __name__ == "__main__":
    asyncio.run(main())
