import asyncio
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Пытаемся использовать именно selfbot_venv, если он есть
SELF_BOT_SITE = os.path.join(
    BASE_DIR,
    "selfbot_venv",
    "lib",
    "python3.12",
    "site-packages"
)

if os.path.isdir(SELF_BOT_SITE):
    sys.path.insert(0, SELF_BOT_SITE)

import aiohttp
import discord


REQUEST_FILE = os.path.join(BASE_DIR, "requests.json")
RESPONSE_FILE = os.path.join(BASE_DIR, "responses.json")

POLL_INTERVAL = 0.5


# =========================
# PROXY
# =========================

PROXY_HOST = "31.59.20.176"
PROXY_PORT = 6754
PROXY_USER = "zokylxzq"
PROXY_PASS = "kmiwh1bvbpl5"

PROXY_URL = f"http://{PROXY_HOST}:{PROXY_PORT}"
PROXY_AUTH = aiohttp.BasicAuth(
    PROXY_USER,
    PROXY_PASS
)


# =========================
# SELFBOT
# =========================

class SelfBot(discord.Client):

    def __init__(self):
        super().__init__(
            proxy=PROXY_URL,
            proxy_auth=PROXY_AUTH
        )

        self._ready_event = asyncio.Event()

    async def on_ready(self):
        print(
            f"[Selfbot] Залогинен как {self.user}",
            flush=True
        )

        print(
            f"[Selfbot] Серверов: {len(self.guilds)}",
            flush=True
        )

        print(
            f"[Selfbot] Discord module: {discord.__file__}",
            flush=True
        )

        print(
            f"[Selfbot] Discord version: {getattr(discord, '__version__', 'unknown')}",
            flush=True
        )

        print(
            f"[Selfbot] Proxy: {PROXY_HOST}:{PROXY_PORT}",
            flush=True
        )

        self._ready_event.set()

    async def get_user_guild_data(self, user_id: int) -> list:
        await self._ready_event.wait()

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
                    "nick": member.nick or member.display_name,
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
                            key=lambda r: r.position,
                            reverse=True
                        )
                    ]
                })

            except Exception as e:
                print(
                    f"[Selfbot] Ошибка на сервере "
                    f"{getattr(guild, 'name', 'unknown')}: {e}",
                    flush=True
                )

        return results

    async def poll_requests(self):
        await self._ready_event.wait()

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

                    if not user_id:
                        print(
                            "[Selfbot] В запросе нет user_id",
                            flush=True
                        )
                        await asyncio.sleep(POLL_INTERVAL)
                        continue

                    data = await self.get_user_guild_data(
                        int(user_id)
                    )

                    response = {
                        "req_id": req_id,
                        "data": data
                    }

                    with open(
                        RESPONSE_FILE,
                        "w",
                        encoding="utf-8"
                    ) as f:
                        json.dump(
                            response,
                            f,
                            ensure_ascii=False,
                            indent=2
                        )

                    print(
                        "[Selfbot] Ответ записан. "
                        f"Серверов с ролями: {len(data)}",
                        flush=True
                    )

            except json.JSONDecodeError as e:
                print(
                    f"[Selfbot] Ошибка JSON: {e}",
                    flush=True
                )

            except Exception as e:
                print(
                    f"[Selfbot] Ошибка poll: {type(e).__name__}: {e}",
                    flush=True
                )

            await asyncio.sleep(POLL_INTERVAL)

    async def setup_hook(self):
        asyncio.create_task(
            self.poll_requests()
        )


async def main():

    token = os.getenv("USER_TOKEN")

    if not token:
        raise ValueError(
            "USER_TOKEN не задан"
        )

    bot = SelfBot()

    try:
        print(
            "[Selfbot] Запуск...",
            flush=True
        )

        print(
            f"[Selfbot] Proxy = {PROXY_URL}",
            flush=True
        )

        print(
            f"[Selfbot] discord.py загружен из: {discord.__file__}",
            flush=True
        )

        await bot.start(token)

    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
