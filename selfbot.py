import asyncio
import discord


class SelfBot(discord.Client):
    """
    Selfbot на юзерском аккаунте (discord.py-self).
    Не использует Intents — они не нужны в selfbot библиотеке.
    """

    def __init__(self):
        super().__init__()
        self._ready = asyncio.Event()

    async def on_ready(self):
        print(f"[Selfbot] Залогинен как {self.user} — вижу {len(self.guilds)} серверов")
        self._ready.set()

    async def get_user_guild_data(self, user_id: int) -> list[dict]:
        """
        Возвращает список серверов где у пользователя есть роли (кроме @everyone).
        """
        await self._ready.wait()
        results = []

        for guild in self.guilds:
            try:
                member = guild.get_member(user_id)
                if member is None:
                    try:
                        member = await guild.fetch_member(user_id)
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        continue

                roles = [r for r in member.roles if r.name != "@everyone"]

                if not roles:
                    continue

                results.append({
                    "guild_id": guild.id,
                    "guild_name": guild.name,
                    "nick": member.nick or member.display_name,
                    "joined_at": member.joined_at,
                    "roles": [
                        {"name": r.name, "color": r.color.value, "id": r.id}
                        for r in sorted(roles, key=lambda r: r.position, reverse=True)
                    ],
                })

            except Exception as e:
                print(f"[Selfbot] Ошибка на сервере {guild.name}: {e}")
                continue

        return results
