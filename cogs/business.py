import time
import io
import discord
from discord.ext import commands
from discord import app_commands
from utils.render import render_template

def fmt(n: int) -> str: return f"{n:,}".replace(",", " ")

class Business(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="biz", description="Управление бизнесом")
    @app_commands.choices(action=[
        app_commands.Choice(name="Создать (5000 💰)", value="create"),
        app_commands.Choice(name="Информация", value="info"),
        app_commands.Choice(name="Собрать прибыль", value="collect"),
        app_commands.Choice(name="Улучшить", value="upgrade"),
    ])
    async def biz(self, i: discord.Interaction, action: app_commands.Choice[str], name: str = None):
        biz = await self.bot.db.get_business(i.user.id)

        if action.value == "create":
            if biz: return await i.response.send_message("❌ У вас уже есть бизнес.", ephemeral=True)
            if not name: return await i.response.send_message("❌ Укажите название компании.", ephemeral=True)
            u = await self.bot.db.get_user(i.user.id)
            if u["wallet"] < 5000: return await i.response.send_message("❌ Нужно 5000 💰.", ephemeral=True)
            
            await self.bot.db.update_wallet(i.user.id, -5000)
            await self.bot.db.create_business(i.user.id, name)
            return await i.response.send_message(f"🏢 Бизнес **{name}** успешно открыт!")

        if not biz:
            return await i.response.send_message("❌ У вас нет бизнеса.", ephemeral=True)

        if action.value == "info":
            now = time.time()
            income = biz["level"] * 500
            accumulated = min(int(((now - biz["last_collect"]) / 3600) * income), income * 24)
            
            await i.response.defer()
            data = {
                "name": biz["name"], "level": biz["level"],
                "income": income, "acc": accumulated, "owner": i.user.name
            }
            png = await render_template("business.html", data)
            file = discord.File(fp=io.BytesIO(png), filename="biz.png")
            await i.followup.send(file=file)

        elif action.value == "collect":
            now = time.time()
            hours_passed = (now - biz["last_collect"]) / 3600
            if hours_passed < 1:
                return await i.response.send_message(f"⏳ Ждите еще {int((1-hours_passed)*60)} мин.", ephemeral=True)
            
            income = biz["level"] * 500
            accumulated = min(int(hours_passed * income), income * 24)
            await self.bot.db.update_wallet(i.user.id, accumulated)
            await self.bot.db.update_business(biz["biz_id"], last_collect=now)
            await i.response.send_message(f"💵 Вы собрали **{fmt(accumulated)}** 💰!")

        elif action.value == "upgrade":
            cost = biz["level"] * 10000
            u = await self.bot.db.get_user(i.user.id)
            if u["wallet"] < cost: return await i.response.send_message(f"❌ Нужно **{fmt(cost)}** 💰.", ephemeral=True)
            
            await self.bot.db.update_wallet(i.user.id, -cost)
            await self.bot.db.update_business(biz["biz_id"], level=biz["level"]+1)
            await i.response.send_message(f"📈 Бизнес улучшен до **{biz['level']+1}** уровня!")

async def setup(bot):
    await bot.add_cog(Business(bot))