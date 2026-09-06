import discord
from discord.ext import commands
import aiohttp

print(f"[Client] discord version: {discord.__version__}", flush=True)


class RoleBot(commands.Bot):
    def __init__(self, proxy_url: str, proxy_auth: aiohttp.BasicAuth):
        super().__init__(
            command_prefix="!",
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
