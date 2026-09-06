import discord
from discord.ext import commands


class RoleBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        from commands import CheckCog
        await self.add_cog(CheckCog(self))
        await self.tree.sync()
        print("[Bot] Слэш-команды синхронизированы", flush=True)

    async def on_ready(self):
        print(f"[Bot] Залогинен как {self.user}", flush=True)
