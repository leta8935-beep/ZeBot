import discord
from discord.ext import commands
from discord import app_commands


def fmt(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def is_admin():
    async def predicate(i: discord.Interaction) -> bool:
        if not i.user.guild_permissions.administrator:
            raise app_commands.CheckFailure("Только для администраторов.")
        return True
    return app_commands.check(predicate)


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="admin",
                          description="[ADMIN] Управление балансом игрока")
    @app_commands.choices(action=[
        app_commands.Choice(name="➕ Добавить", value="add"),
        app_commands.Choice(name="➖ Убрать", value="remove"),
        app_commands.Choice(name="🔄 Обновить", value="update"),
    ])
    @is_admin()
    async def admin(self, i: discord.Interaction,
                    action: app_commands.Choice[str],
                    member: discord.Member, amount: int):
        if amount < 0:
            return await i.response.send_message(
                "❌ Сумма не может быть отрицательной.", ephemeral=True)

        u = await self.bot.db.get_user(member.id)
        before = u["wallet"]

        if action.value == "add":
            await self.bot.db.update_wallet(member.id, amount)
            after, sign = before + amount, "+"
        elif action.value == "remove":
            await self.bot.db.update_wallet(member.id, -amount)
            after, sign = max(before - amount, 0), "−"
        else:
            await self.bot.db.set_wallet(member.id, amount)
            after, sign = amount, "="

        await self.bot.db.log(i.user.id, member.id, amount,
                              f"admin_{action.value}")

        e = discord.Embed(title=f"{action.name} баланса",
                          color=discord.Color.orange())
        e.add_field(name="Игрок", value=member.mention, inline=True)
        e.add_field(name="Было", value=f"**{fmt(before)}**", inline=True)
        e.add_field(name="Сумма", value=f"**{sign} {fmt(amount)}**", inline=True)
        e.add_field(name="Стало", value=f"**{fmt(after)}**", inline=True)
        e.set_footer(text=f"Админ: {i.user.display_name}")
        await i.response.send_message(embed=e, ephemeral=True)

    async def cog_app_command_error(self, i: discord.Interaction,
                                    error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            if not i.response.is_done():
                await i.response.send_message(f"🚫 {error}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Admin(bot))