import asyncio
import json
import os
import uuid
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone

REQUEST_FILE = "requests.json"
RESPONSE_FILE = "responses.json"
TIMEOUT = 15  # секунд ждём ответа от selfbot


async def ask_selfbot(user_id: int) -> list | None:
    """Пишет запрос в файл и ждёт ответа от selfbot."""
    req_id = str(uuid.uuid4())

    with open(REQUEST_FILE, "w") as f:
        json.dump({"req_id": req_id, "user_id": user_id}, f)

    for _ in range(TIMEOUT * 2):
        await asyncio.sleep(0.5)
        if os.path.exists(RESPONSE_FILE):
            try:
                with open(RESPONSE_FILE, "r") as f:
                    resp = json.load(f)
                if resp.get("req_id") == req_id:
                    os.remove(RESPONSE_FILE)
                    return resp.get("data", [])
            except Exception:
                pass

    return None  # таймаут


def build_overview_embed(user: discord.User, guild_data: list) -> discord.Embed:
    embed = discord.Embed(title=f"Проверка ролей: {user.name}", color=0x5865F2)
    embed.set_thumbnail(url=user.display_avatar.url)
    lines = [f"✅ **{entry['guild_name']}**" for entry in guild_data]
    embed.description = "\n".join(lines) if lines else "Нет серверов с ролями"
    embed.set_footer(text=f"ID: {user.id} • Выбери сервер ниже для подробностей")
    return embed


def build_detail_embed(user: discord.User, entry: dict) -> discord.Embed:
    embed = discord.Embed(title=entry["guild_name"], color=0x57F287)
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="Ник", value=entry["nick"] or "—", inline=True)

    joined_str = entry.get("joined_at")
    if joined_str:
        try:
            dt = datetime.fromisoformat(joined_str)
            ts = int(dt.replace(tzinfo=timezone.utc).timestamp())
            embed.add_field(name="Вступил", value=f"<t:{ts}:D>", inline=True)
        except Exception:
            pass

    role_list = " ".join([f"`{r['name']}`" for r in entry["roles"]])
    embed.add_field(name=f"Роли ({len(entry['roles'])})", value=role_list or "—", inline=False)
    embed.set_footer(text=f"ID: {user.id}")
    return embed


class GuildSelect(discord.ui.Select):
    def __init__(self, user: discord.User, guild_data: list):
        self.user = user
        self.guild_map = {str(e["guild_id"]): e for e in guild_data}
        options = [
            discord.SelectOption(
                label=entry["guild_name"][:100],
                value=str(entry["guild_id"]),
                description=f"{len(entry['roles'])} роль(-и/-ей)",
            )
            for entry in guild_data[:25]  # Discord лимит — 25 опций
        ]
        super().__init__(placeholder="Выбери сервер для подробностей...", options=options)

    async def callback(self, interaction: discord.Interaction):
        entry = self.guild_map.get(self.values[0])
        if not entry:
            await interaction.response.send_message("Данные не найдены.", ephemeral=True)
            return
        embed = build_detail_embed(self.user, entry)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class GuildSelectView(discord.ui.View):
    def __init__(self, user: discord.User, guild_data: list):
        super().__init__(timeout=120)
        self.add_item(GuildSelect(user, guild_data))


class CheckCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="check", description="Проверить роли пользователя по всем серверам")
    @app_commands.describe(
        user="Упомяни пользователя (@user)",
        user_id="Или введи Discord ID пользователя",
    )
    async def check(
        self,
        interaction: discord.Interaction,
        user: discord.User = None,
        user_id: str = None,
    ):
        await interaction.response.defer(ephemeral=True)

        target = None
        if user:
            target = user
        elif user_id:
            try:
                target = await self.bot.fetch_user(int(user_id.strip()))
            except Exception:
                await interaction.followup.send("❌ Пользователь не найден.", ephemeral=True)
                return
        else:
            await interaction.followup.send("❌ Укажи @пользователя или ID.", ephemeral=True)
            return

        await interaction.followup.send("🔍 Ищу данные...", ephemeral=True)

        guild_data = await ask_selfbot(target.id)

        if guild_data is None:
            await interaction.followup.send("⏱️ Selfbot не ответил, попробуй позже.", ephemeral=True)
            return

        if not guild_data:
            await interaction.followup.send(
                f"😶 У **{target.name}** нет ролей ни на одном общем сервере.", ephemeral=True
            )
            return

        embed = build_overview_embed(target, guild_data)
        view = GuildSelectView(target, guild_data)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
