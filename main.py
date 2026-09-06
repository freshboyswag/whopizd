import asyncio
import subprocess
import sys
import os
import keepalive
from config import BOT_TOKEN, get_working_proxy
from client import RoleBot


async def main():
    keepalive.start()

    proxy_url, proxy_auth = await get_working_proxy()

    if proxy_url is None:
        print("[Main] Нет рабочих прокси, выход", flush=True)
        return

    env = {**os.environ, "PROXY_URL": proxy_url}

    selfbot_proc = subprocess.Popen(
        [sys.executable, "selfbot.py"],
        env=env,
    )
    print(f"[Main] Selfbot процесс запущен (PID {selfbot_proc.pid})", flush=True)

    try:
        bot = RoleBot(proxy_url=proxy_url, proxy_auth=proxy_auth)
        await bot.start(BOT_TOKEN)
    finally:
        selfbot_proc.terminate()
        print("[Main] Selfbot процесс остановлен", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
