import discord
from discord.ext import commands


class RoleBot(commands.Bot):
    def __init__(self, selfbot):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.selfbot = selfbot

    async def setup_hook(self):
        from commands import CheckCog
        await self.add_cog(CheckCog(self))
        await self.tree.sync()
        print("[Bot] Слэш-команды синхронизированы")

    async def on_ready(self):
        print(f"[Bot] Залогинен как {self.user}")
