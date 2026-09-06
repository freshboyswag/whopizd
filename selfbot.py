import asyncio
import discord
from discord.ext import commands as self_commands


class SelfBot(discord.Client):
    """
    Selfbot на твоём юзерском аккаунте.
    Ходит по всем серверам где ты сидишь и собирает данные о пользователе.
    """

    def __init__(self):
        super().__init__()
        self._ready = asyncio.Event()

    async def on_ready(self):
        print(f"[Selfbot] Залогинен как {self.user} — вижу {len(self.guilds)} серверов")
        self._ready.set()

    async def wait_until_ready_custom(self):
        await self._ready.wait()

    async def get_user_guild_data(self, user_id: int) -> list[dict]:
        """
        Возвращает список словарей по серверам где есть пользователь И у него есть роли (кроме @everyone).
        """
        await self._ready.wait()
        results = []

        for guild in self.guilds:
            try:
                member = guild.get_member(user_id)
                if member is None:
                    # Пробуем подтянуть через API если не в кэше
                    try:
                        member = await guild.fetch_member(user_id)
                    except (discord.NotFound, discord.Forbidden):
                        continue

                # Роли без @everyone
                roles = [r for r in member.roles if r.name != "@everyone"]

                if not roles:
                    continue  # Не показываем сервера без ролей

                results.append({
                    "guild_id": guild.id,
                    "guild_name": guild.name,
                    "guild_icon": str(guild.icon.url) if guild.icon else None,
                    "nick": member.nick or member.name,
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
