import sys
import aiohttp

# Принудительно используем discord.py (не discord.py-self)
sys.path.insert(0, "/opt/render/project/src/.venv/lib/python3.12/site-packages")
import discord
from discord.ext import commands

print(f"[Client] discord: {discord.__file__}", flush=True)


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
