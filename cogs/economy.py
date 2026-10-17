import discord
from discord.ext import commands
from discord import app_commands
TAX_RATE = 0

def fmt(n: int) -> str:
    return f"{n:,}".replace(",", " ")


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="balance", description="Показать баланс")
    @app_commands.describe(member="Чужой баланс — только для администраторов")
    async def balance(self, i: discord.Interaction,
                      member: discord.Member | None = None):
        is_admin = i.user.guild_permissions.administrator
        if member and member.id != i.user.id and not is_admin:
            return await i.response.send_message(
                "🚫 Только администратор может смотреть чужие балансы.",
                ephemeral=True)

        target = member or i.user
        u = await self.bot.db.get_user(target.id)
        e = discord.Embed(
            title=f"💰 Баланс {target.display_name}",
            description=f"## {fmt(u['wallet'])} монет",
            color=discord.Color.green())
        e.set_thumbnail(url=target.display_avatar.url)
        await i.response.send_message(
            embed=e, ephemeral=(target.id == i.user.id))

    @app_commands.command(name="pay", description="Перевести деньги")
    async def pay(self, i: discord.Interaction,
                  member: discord.Member, amount: int):
        if member.bot or member.id == i.user.id or amount <= 0:
            return await i.response.send_message(
                "❌ Некорректный получатель или сумма.", ephemeral=True)

        sender = await self.bot.db.get_user(i.user.id)
        if sender["wallet"] < amount:
            return await i.response.send_message(
                f"❌ Недостаточно средств. У тебя: **{fmt(sender['wallet'])}**",
                ephemeral=True)

        await self.bot.db.get_user(member.id)
        tax = int(amount * TAX_RATE)
        net = amount - tax

        await self.bot.db.update_wallet(i.user.id, -amount)
        await self.bot.db.update_wallet(member.id, net)
        await self.bot.db.log(i.user.id, member.id, amount, "pay")

        e = discord.Embed(title="💸 Перевод выполнен",
                          color=discord.Color.blurple())
        e.add_field(name="От", value=i.user.mention, inline=True)
        e.add_field(name="Кому", value=member.mention, inline=True)
        e.add_field(name="Сумма", value=f"**{fmt(amount)}**", inline=True)
        e.add_field(name="Налог", value=f"**{fmt(tax)}**", inline=True)
        e.add_field(name="Получено", value=f"**{fmt(net)}**", inline=True)
        await i.response.send_message(embed=e)


async def setup(bot):
    await bot.add_cog(Economy(bot))