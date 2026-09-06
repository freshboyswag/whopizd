"""
selfbot.py — запускается отдельным процессом через discord.py-self.
Читает запросы из requests.json, пишет ответы в responses.json.
"""
import asyncio
import json
import os
import sys

# Используем discord.py-self
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'selfbot_venv', 'lib', 'python3.12', 'site-packages'))

import discord

REQUEST_FILE = "requests.json"
RESPONSE_FILE = "responses.json"
POLL_INTERVAL = 0.5  # секунд


class SelfBot(discord.Client):
    def __init__(self):
        super().__init__()
        self._ready = asyncio.Event()

    async def on_ready(self):
        print(f"[Selfbot] Залогинен как {self.user} — вижу {len(self.guilds)} серверов", flush=True)
        self._ready.set()

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
                roles = [r for r in member.roles if r.name != "@everyone"]
                if not roles:
                    continue
                results.append({
                    "guild_id": guild.id,
                    "guild_name": guild.name,
                    "nick": member.nick or member.display_name,
                    "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                    "roles": [
                        {"name": r.name, "color": r.color.value, "id": r.id}
                        for r in sorted(roles, key=lambda r: r.position, reverse=True)
                    ],
                })
            except Exception as e:
                print(f"[Selfbot] Ошибка {guild.name}: {e}", flush=True)
        return results

    async def poll_requests(self):
        """Периодически проверяет requests.json и пишет ответ в responses.json."""
        await self._ready.wait()
        while True:
            try:
                if os.path.exists(REQUEST_FILE):
                    with open(REQUEST_FILE, "r") as f:
                        req = json.load(f)
                    os.remove(REQUEST_FILE)

                    user_id = req.get("user_id")
                    req_id = req.get("req_id")
                    print(f"[Selfbot] Запрос для user_id={user_id}", flush=True)

                    data = await self.get_user_guild_data(int(user_id))
                    with open(RESPONSE_FILE, "w") as f:
                        json.dump({"req_id": req_id, "data": data}, f)

                    print(f"[Selfbot] Ответ записан, серверов с ролями: {len(data)}", flush=True)
            except Exception as e:
                print(f"[Selfbot] Ошибка poll: {e}", flush=True)

            await asyncio.sleep(POLL_INTERVAL)

    async def setup_hook(self):
        asyncio.create_task(self.poll_requests())


async def main():
    token = os.getenv("USER_TOKEN")
    if not token:
        raise ValueError("USER_TOKEN не задан")
    bot = SelfBot()
    await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
