import discord
from discord import app_commands
from discord.ext import commands
from datetime import timezone


def build_overview_embed(user: discord.User, guild_data: list[dict]) -> discord.Embed:
    """Главный эмбед — список серверов с ролями."""
    embed = discord.Embed(
        title=f"Проверка ролей: {user.name}",
        color=0x5865F2,
    )
    embed.set_thumbnail(url=user.display_avatar.url)

    lines = []
    for entry in guild_data:
        lines.append(f"✅ **{entry['guild_name']}**")

    embed.description = "\n".join(lines) if lines else "Нет серверов с ролями"
    embed.set_footer(text=f"ID: {user.id} • Выбери сервер ниже для подробностей")
    return embed


def build_detail_embed(user: discord.User, entry: dict) -> discord.Embed:
    """Детальный эмбед по конкретному серверу."""
    embed = discord.Embed(
        title=f"{entry['guild_name']}",
        color=0x57F287,
    )
    embed.set_thumbnail(url=user.display_avatar.url)

    # Ник на сервере
    embed.add_field(name="Ник", value=entry["nick"], inline=True)

    # Дата вступления
    joined = entry["joined_at"]
    if joined:
        ts = int(joined.replace(tzinfo=timezone.utc).timestamp())
        embed.add_field(name="Вступил", value=f"<t:{ts}:D>", inline=True)

    # Роли
    role_list = " ".join([f"`{r['name']}`" for r in entry["roles"]])
    embed.add_field(name=f"Роли ({len(entry['roles'])})", value=role_list or "—", inline=False)

    embed.set_footer(text=f"ID: {user.id}")
    return embed


class GuildSelect(discord.ui.Select):
    def __init__(self, user: discord.User, guild_data: list[dict]):
        self.user = user
        self.guild_data = {str(e["guild_id"]): e for e in guild_data}

        options = [
            discord.SelectOption(
                label=entry["guild_name"][:100],
                value=str(entry["guild_id"]),
                description=f"{len(entry['roles'])} роль(-и/-ей)",
            )
            for entry in guild_data
        ]

        super().__init__(
            placeholder="Выбери сервер для подробностей...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        guild_id = self.values[0]
        entry = self.guild_data.get(guild_id)
        if not entry:
            await interaction.response.send_message("Данные не найдены.", ephemeral=True)
            return

        embed = build_detail_embed(self.user, entry)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class GuildSelectView(discord.ui.View):
    def __init__(self, user: discord.User, guild_data: list[dict]):
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
        # Ephemeral — видит только вызвавший
        await interaction.response.defer(ephemeral=True)

        # Определяем target пользователя
        target: discord.User = None

        if user:
            target = user
        elif user_id:
            try:
                uid = int(user_id.strip())
                target = await self.bot.fetch_user(uid)
            except (ValueError, discord.NotFound):
                await interaction.followup.send(
                    "❌ Пользователь с таким ID не найден.", ephemeral=True
                )
                return
        else:
            await interaction.followup.send(
                "❌ Укажи пользователя (@упоминание) или его Discord ID.", ephemeral=True
            )
            return

        # Запрашиваем данные через selfbot
        await interaction.followup.send("🔍 Ищу данные...", ephemeral=True)

        try:
            guild_data = await self.bot.selfbot.get_user_guild_data(target.id)
        except Exception as e:
            await interaction.followup.send(f"❌ Ошибка при получении данных: {e}", ephemeral=True)
            return

        if not guild_data:
            await interaction.followup.send(
                f"😶 У **{target.name}** нет ролей ни на одном общем сервере.",
                ephemeral=True,
            )
            return

        embed = build_overview_embed(target, guild_data)
        view = GuildSelectView(target, guild_data)

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
