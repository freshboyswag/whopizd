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
TIMEOUT = 60
IGNORED_GUILDS = {1346230894951661632}


async def ask_selfbot(user_id: int) -> list | None:
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
                    data = resp.get("data", [])
                    return [e for e in data if e["guild_id"] not in IGNORED_GUILDS]
            except Exception:
                pass

    return None


def format_roles(roles: list) -> str:
    if not roles:
        return "—"
    return " · ".join([r['name'] for r in roles])


def build_overview_embed(user: discord.User, guild_data: list) -> discord.Embed:
    embed = discord.Embed(color=0x36393F)
    embed.set_author(
        name=f"{user.name}",
        icon_url=user.display_avatar.url
    )
    embed.set_thumbnail(url=user.display_avatar.url)

    lines = [f"✅ **{entry['guild_name']}**" for entry in guild_data]
    embed.description = "\n".join(lines) if lines else "Нет серверов с ролями"

    embed.set_footer(text=f"Серверов в базе: {len(guild_data)}")
    return embed


def build_detail_embed(user: discord.User, entry: dict) -> discord.Embed:
    embed = discord.Embed(title=entry["guild_name"], color=0x36393F)
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

    embed.add_field(
        name=f"Роли ({len(entry['roles'])})",
        value=format_roles(entry["roles"]),
        inline=False
    )
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
            for entry in guild_data[:25]
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
        user_id="Или введи Discord ID / username пользователя",
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
            user_id = user_id.strip().lstrip("@")
            # Пробуем как числовой ID
            if user_id.isdigit():
                try:
                    target = await self.bot.fetch_user(int(user_id))
                except Exception:
                    pass
            # Пробуем как username
            if target is None:
                try:
                    # Ищем по имени среди участников всех серверов бота
                    for guild in self.bot.guilds:
                        found = discord.utils.find(
                            lambda m: m.name.lower() == user_id.lower() or
                                      (m.nick and m.nick.lower() == user_id.lower()),
                            guild.members
                        )
                        if found:
                            target = found
                            break
                except Exception:
                    pass
            if target is None:
                await interaction.followup.send("❌ Пользователь не найден.", ephemeral=True)
                return
        else:
            await interaction.followup.send("❌ Укажи @пользователя, ID или username.", ephemeral=True)
            return

        await interaction.followup.send("🔍 Ищу данные...", ephemeral=True)

        guild_data = await ask_selfbot(target.id)

        if guild_data is None:
            await interaction.followup.send("⏱️ Selfbot не ответил, попробуй позже.", ephemeral=True)
            return

        if not guild_data:
            await interaction.followup.send(
                f"😶 У **{target.name}** нет ролей ни на одном общем сервере.",
                ephemeral=True
            )
            return

        embed = build_overview_embed(target, guild_data)
        view = GuildSelectView(target, guild_data)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
