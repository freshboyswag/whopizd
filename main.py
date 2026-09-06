"""
main.py — запускает selfbot и официальный бот как два параллельных процесса.
"""
import asyncio
import subprocess
import sys
import os
import keepalive
from config import BOT_TOKEN
from client import RoleBot


async def run_bot():
    bot = RoleBot()
    await bot.start(BOT_TOKEN)


async def main():
    # Keepalive HTTP для Render + UptimeRobot
    keepalive.start()

    # Запускаем selfbot как отдельный процесс
    selfbot_proc = subprocess.Popen(
        [sys.executable, "selfbot.py"],
        env={**os.environ},
    )
    print(f"[Main] Selfbot процесс запущен (PID {selfbot_proc.pid})", flush=True)

    try:
        await run_bot()
    finally:
        selfbot_proc.terminate()
        print("[Main] Selfbot процесс остановлен", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
