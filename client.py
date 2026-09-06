import sys
import importlib

# Принудительно убираем discord.py-self из импорта для этого модуля
# и подгружаем обычный discord.py
import aiohttp

# Используем полный путь к discord.py
sys.path.insert(0, "/opt/render/project/src/.venv/lib/python3.12/site-packages")
import discord
from discord.ext import commands


class RoleBot(commands.Bot):
    def __init__(self, proxy_url: str, proxy_auth: aiohttp.BasicAuth):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(
            command_prefix="!",
            intents=intents,
            proxy=proxy_url,
            proxy_auth=proxy_auth,
        )

    async def setup_hook(self):
        from commands import CheckCog
        await self.add_cog(CheckCog(self))
        await self.tree.sync()
        print("[Bot] Слэш-команды синхронизированы", flush=True)

    async def on_ready(self):
        print(f"[Bot] Залогинен как {self.user}", flush=True)
