```python
"""
selfbot.py — запускается отдельным процессом через discord.py-self.
Читает запросы из requests.json, пишет ответы в responses.json.
"""

import asyncio
import json
import os
import sys

# ---------------------------------------------------------
# Пытаемся использовать локальную установку selfbot_venv
# ---------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SELF_VENV = os.path.join(
    BASE_DIR,
    "selfbot_venv",
    "lib",
    "python3.12",
    "site-packages"
)

if os.path.isdir(SELF_VENV):
    sys.path.insert(0, SELF_VENV)

import discord
import aiohttp


# ---------------------------------------------------------
# Настройки
# ---------------------------------------------------------

REQUEST_FILE = os.path.join(BASE_DIR, "requests.json")
RESPONSE_FILE = os.path.join(BASE_DIR, "responses.json")

POLL_INTERVAL = 0.5


# ---------------------------------------------------------
# Прокси
# ---------------------------------------------------------

PROXY_HOST = "31.59.20.176"
PROXY_PORT = 6754
PROXY_USER = "zokylxzq"
PROXY_PASS = "kmiwh1bvbpl5"

PROXY_URL = f"http://{PROXY_HOST}:{PROXY_PORT}"

PROXY_AUTH = aiohttp.BasicAuth(
    PROXY_USER,
    PROXY_PASS
)


# ---------------------------------------------------------
# SelfBot
# ---------------------------------------------------------

class SelfBot(discord.Client):

    def __init__(self):

        print(
            f"[Selfbot] discord module: {discord.__file__}",
            flush=True
        )

        print(
            f"[Selfbot] discord version: "
            f"{getattr(discord, '__version__', 'unknown')}",
            flush=True
        )

        print(
            f"[Selfbot] Proxy: "
            f"{PROXY_HOST}:{PROXY_PORT}",
            flush=True
        )

        super().__init__(
            proxy=PROXY_URL,
            proxy_auth=PROXY_AUTH
        )

        self._ready = asyncio.Event()


    # -----------------------------------------------------
    # Ready
    # -----------------------------------------------------

    async def on_ready(self):

        print(
            f"[Selfbot] Залогинен как {self.user} — "
            f"вижу {len(self.guilds)} серверов",
            flush=True
        )

        self._ready.set()


    # -----------------------------------------------------
    # Получение данных пользователя
    # -----------------------------------------------------

    async def get_user_guild_data(self, user_id: int) -> list:

        await self._ready.wait()

        results = []

        for guild in self.guilds:

            try:

                member = guild.get_member(user_id)

                if member is None:

                    try:
                        member = await guild.fetch_member(user_id)

                    except Exception:
                        continue

                roles = [
                    role
                    for role in member.roles
                    if role.name != "@everyone"
                ]

                if not roles:
                    continue

                results.append({
                    "guild_id": guild.id,
                    "guild_name": guild.name,
                    "nick": (
                        member.nick
                        or member.display_name
                    ),
                    "joined_at": (
                        member.joined_at.isoformat()
                        if member.joined_at
                        else None
                    ),
                    "roles": [
                        {
                            "name": role.name,
                            "color": role.color.value,
                            "id": role.id
                        }
                        for role in sorted(
                            roles,
                            key=lambda role: role.position,
                            reverse=True
                        )
                    ],
                })

            except Exception as e:

                print(
                    f"[Selfbot] Ошибка {guild.name}: {e}",
                    flush=True
                )

        return results


    # -----------------------------------------------------
    # Обработка requests.json
    # -----------------------------------------------------

    async def poll_requests(self):

        await self._ready.wait()

        while True:

            try:

                if os.path.exists(REQUEST_FILE):

                    with open(
                        REQUEST_FILE,
                        "r",
                        encoding="utf-8"
                    ) as f:

                        req = json.load(f)

                    os.remove(REQUEST_FILE)

                    user_id = req.get("user_id")
                    req_id = req.get("req_id")

                    print(
                        f"[Selfbot] Запрос для user_id={user_id}",
                        flush=True
                    )

                    data = await self.get_user_guild_data(
                        int(user_id)
                    )

                    with open(
                        RESPONSE_FILE,
                        "w",
                        encoding="utf-8"
                    ) as f:

                        json.dump(
                            {
                                "req_id": req_id,
                                "data": data
                            },
                            f,
                            ensure_ascii=False
                        )

                    print(
                        f"[Selfbot] Ответ записан, "
                        f"серверов с ролями: {len(data)}",
                        flush=True
                    )

            except Exception as e:

                print(
                    f"[Selfbot] Ошибка poll: {e}",
                    flush=True
                )

            await asyncio.sleep(POLL_INTERVAL)


    # -----------------------------------------------------
    # Startup hook
    # -----------------------------------------------------

    async def setup_hook(self):

        asyncio.create_task(
            self.poll_requests()
        )


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

async def main():

    token = os.getenv("USER_TOKEN")

    if not token:
        raise ValueError(
            "USER_TOKEN не задан"
        )

    bot = SelfBot()

    try:

        await bot.start(token)

    finally:

        try:
            await bot.close()
        except Exception:
            pass


# ---------------------------------------------------------
# Run
# ---------------------------------------------------------

if __name__ == "__main__":

    asyncio.run(main())
```
