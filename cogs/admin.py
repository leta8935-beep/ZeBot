import discord
from discord.ext import commands
from discord import app_commands
from utils.checks import is_staff

def fmt(n: int) -> str: return f"{n:,}".replace(",", " ")

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="admin", description="[STAFF] Управление балансом")
    @app_commands.choices(action=[
        app_commands.Choice(name="➕ Добавить", value="add"),
        app_commands.Choice(name="➖ Убрать", value="remove"),
        app_commands.Choice(name="🔄 Обновить", value="update"),
    ])
    @is_staff()
    async def admin(self, i: discord.Interaction, action: app_commands.Choice[str], member: discord.Member, amount: int):
        if amount < 0: return await i.response.send_message("❌ Сумма > 0.", ephemeral=True)
        await self.bot.db.get_user(member.id)
        
        if action.value == "add": await self.bot.db.update_wallet(member.id, amount)
        elif action.value == "remove": await self.bot.db.update_wallet(member.id, -amount)
        else: await self.bot.db.set_wallet(member.id, amount)
        
        u = await self.bot.db.get_user(member.id)
        embed = discord.Embed(title="Баланс изменен", color=0xEB459E, description=f"**Игрок:** {member.mention}\n**Новый баланс:** {fmt(u['wallet'])} 💰")
        await i.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="create_org", description="[STAFF] Создать организацию для игрока")
    @is_staff()
    @app_commands.choices(org_type=[
        app_commands.Choice(name="СМИ", value="СМИ"),
        app_commands.Choice(name="Бизнес", value="Бизнес"),
        app_commands.Choice(name="НКО / Фонд", value="НКО"),
        app_commands.Choice(name="Корпорация", value="Корпорация")
    ])
    async def create_org(self, i: discord.Interaction, member: discord.Member, name: str, org_type: app_commands.Choice[str]):
        existing = await self.bot.db.get_business(member.id)
        if existing:
            return await i.response.send_message("❌ У этого игрока уже есть организация.", ephemeral=True)
        
        await self.bot.db.create_business(member.id, name, org_type.value)
        embed = discord.Embed(title="🏢 Организация создана", color=0x57F287)
        embed.description = f"Владелец: {member.mention}\nНазвание: **{name}**\nТип: **{org_type.value}**"
        await i.response.send_message(embed=embed)

    async def cog_app_command_error(self, i, error):
        if isinstance(error, app_commands.CheckFailure): await i.response.send_message(f"🚫 {error}", ephemeral=True)

async def setup(bot): await bot.add_cog(Admin(bot))