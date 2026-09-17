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


def pluralize(n: int, one: str, few: str, many: str) -> str:
    if 11 <= n % 100 <= 19:
        return many
    r = n % 10
    if r == 1:
        return one
    if 2 <= r <= 4:
        return few
    return many


async def ask_selfbot(user_id: int = None, username: str = None) -> dict | None:
    req_id = str(uuid.uuid4())

    payload = {"req_id": req_id}
    if user_id is not None:
        payload["user_id"] = user_id
    if username is not None:
        payload["username"] = username

    with open(REQUEST_FILE, "w") as f:
        json.dump(payload, f)

    for _ in range(TIMEOUT * 2):
        await asyncio.sleep(0.5)
        if os.path.exists(RESPONSE_FILE):
            try:
                with open(RESPONSE_FILE, "r") as f:
                    resp = json.load(f)
                if resp.get("req_id") == req_id:
                    os.remove(RESPONSE_FILE)
                    return resp
            except Exception:
                pass

    return None


def format_roles(roles: list) -> str:
    if not roles:
        return "—"
    return " · ".join([r['name'] for r in roles])


def build_overview_embed(display_name: str, avatar_url: str, role_guilds: list, total_guilds: int) -> discord.Embed:
    embed = discord.Embed(color=0x36393F)
    embed.set_thumbnail(url=avatar_url)

    lines = [f"✅ **{entry['guild_name']}**" for entry in role_guilds]
    body = "\n".join(lines) if lines else "Нет серверов с ролями"
    embed.description = f"**{display_name}**\n\n{body}"

    embed.set_footer(text=f"{total_guilds} {pluralize(total_guilds, 'сервер в базе', 'сервера в базе', 'серверов в базе')}")
    return embed


def build_all_guilds_embed(display_name: str, avatar_url: str, all_guilds: list) -> discord.Embed:
    embed = discord.Embed(color=0x36393F)
    embed.set_thumbnail(url=avatar_url)

    lines = [f"• {entry['guild_name']}" for entry in all_guilds]
    body = "\n".join(lines) if lines else "Нет общих серверов"
    embed.description = f"**{display_name}**\n\n{body}"

    count = len(all_guilds)
    embed.set_footer(text=f"{count} {pluralize(count, 'общий сервер', 'общих сервера', 'общих серверов')}")
    return embed


def build_detail_embed(display_name: str, avatar_url: str, user_id: int, entry: dict) -> discord.Embed:
    embed = discord.Embed(title=entry["guild_name"], color=0x36393F)
    embed.set_thumbnail(url=avatar_url)

    embed.add_field(name="Юз", value=display_name, inline=True)

    nick = entry.get("nick")
    if nick and nick != display_name:
        embed.add_field(name="Ник", value=nick, inline=True)

    joined_str = entry.get("joined_at")
    if joined_str:
        try:
            dt = datetime.fromisoformat(joined_str)
            ts = int(dt.replace(tzinfo=timezone.utc).timestamp())
            embed.add_field(name="Вступил", value=f"<t:{ts}:D>", inline=True)
        except Exception:
            pass

    role_count = len(entry['roles'])
    embed.add_field(
        name=f"{role_count} {pluralize(role_count, 'роль', 'роли', 'ролей')}",
        value=f"```{format_roles(entry['roles'])}```",
        inline=False
    )
    embed.set_footer(text=f"ID: {user_id}")
    return embed


class GuildSelect(discord.ui.Select):
    def __init__(self, display_name: str, avatar_url: str, user_id: int, role_guilds: list):
        self.display_name = display_name
        self.avatar_url = avatar_url
        self.user_id = user_id
        self.guild_map = {str(e["guild_id"]): e for e in role_guilds}
        options = [
            discord.SelectOption(
                label=entry["guild_name"][:100],
                value=str(entry["guild_id"]),
                description=f"{len(entry['roles'])} {pluralize(len(entry['roles']), 'роль', 'роли', 'ролей')}",
            )
            for entry in role_guilds[:25]
        ]
        super().__init__(placeholder="Выбери сервер для подробностей...", options=options)

    async def callback(self, interaction: discord.Interaction):
        entry = self.guild_map.get(self.values[0])
        if not entry:
            await interaction.response.send_message("Данные не найдены.", ephemeral=True)
            return
        embed = build_detail_embed(self.display_name, self.avatar_url, self.user_id, entry)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class GuildSelectView(discord.ui.View):
    def __init__(self, display_name: str, avatar_url: str, user_id: int, role_guilds: list):
        super().__init__(timeout=120)
        self.add_item(GuildSelect(display_name, avatar_url, user_id, role_guilds))


class OverviewView(discord.ui.View):
    def __init__(self, display_name: str, avatar_url: str, user_id: int, all_guilds: list, role_guilds: list):
        super().__init__(timeout=180)
        self.display_name = display_name
        self.avatar_url = avatar_url
        self.user_id = user_id
        self.all_guilds = all_guilds
        self.role_guilds = role_guilds

        if not role_guilds:
            self.children[0].disabled = True
        if not all_guilds:
            self.children[1].disabled = True

    @discord.ui.button(label="Подробности", style=discord.ButtonStyle.primary)
    async def details_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = GuildSelectView(self.display_name, self.avatar_url, self.user_id, self.role_guilds)
        await interaction.response.send_message(
            "Выбери сервер:", view=view, ephemeral=True
        )

    @discord.ui.button(label="Все общие", style=discord.ButtonStyle.secondary)
    async def all_guilds_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = build_all_guilds_embed(self.display_name, self.avatar_url, self.all_guilds)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class CheckCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="check", description=".")
    async def check(
        self,
        interaction: discord.Interaction,
        target: str,
    ):
        await interaction.response.defer(ephemeral=True)

        target = target.strip().lstrip("@")

        resolved_user = None
        if target.isdigit():
            try:
                resolved_user = await self.bot.fetch_user(int(target))
            except Exception:
                pass

        await interaction.followup.send("👀 Ищу...", ephemeral=True)

        if resolved_user:
            resp = await ask_selfbot(user_id=resolved_user.id)
        else:
            resp = await ask_selfbot(username=target)

        if resp is None:
            await interaction.followup.send("Selfbot не ответил, попробуй позже.", ephemeral=True)
            return

        if resp.get("error") == "not_found":
            await interaction.followup.send("Пользователь не найден.", ephemeral=True)
            return

        user_id = resp["user_id"]

        if resolved_user is None:
            try:
                resolved_user = await self.bot.fetch_user(user_id)
            except Exception:
                resolved_user = None

        display_name = resolved_user.name if resolved_user else str(user_id)
        avatar_url = resolved_user.display_avatar.url if resolved_user else None

        all_guilds = [e for e in resp["all_guilds"] if e["guild_id"] not in IGNORED_GUILDS]
        role_guilds = [e for e in resp["role_guilds"] if e["guild_id"] not in IGNORED_GUILDS]
        total_guilds = resp.get("total_guilds", 0) - len(IGNORED_GUILDS)

        if not all_guilds:
            await interaction.followup.send(
                f"У **{display_name}** нет общих серверов.",
                ephemeral=True
            )
            return

        embed = build_overview_embed(display_name, avatar_url, role_guilds, total_guilds)
        view = OverviewView(display_name, avatar_url, user_id, all_guilds, role_guilds)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
