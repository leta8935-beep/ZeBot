import time
import io
import discord
from discord.ext import commands
from discord import app_commands
from utils.render import render_template

def fmt(n: int) -> str: return f"{n:,}".replace(",", " ")

class Organization(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="org", description="Управление вашей организацией")
    @app_commands.choices(action=[
        app_commands.Choice(name="Обозрение (Инфо)", value="info"),
        app_commands.Choice(name="Собрать прибыль", value="collect"),
        app_commands.Choice(name="Улучшить", value="upgrade"),
    ])
    async def org(self, i: discord.Interaction, action: app_commands.Choice[str]):
        # Используем старую функцию get_business из БД
        biz = await self.bot.db.get_business(i.user.id)
        
        if not biz:
            return await i.response.send_message("❌ У вас нет организации. Подайте заявку!", ephemeral=True)

        if action.value == "info":
            now = time.time()
            income = biz["level"] * 500
            accumulated = min(int(((now - biz["last_collect"]) / 3600) * income), income * 24)
            
            await i.response.defer()
            
            # Формируем данные для HTML шаблона
            data = {
                "name": biz["name"], 
                "level": biz["level"],
                "income": income, 
                "acc": accumulated, 
                "owner": i.user.name,
                "org_type": biz["activity"], # Используем activity как тип
                "sphere": "Деятельность не указана" # Заглушка, если нет в БД
            }
            
            try:
                png = await render_template("organization.html", data)
                file = discord.File(fp=io.BytesIO(png), filename="org.png")
                await i.followup.send(file=file)
            except Exception as e:
                await i.followup.send(f"Ошибка рендера: {e}")

        elif action.value == "collect":
            now = time.time()
            hours_passed = (now - biz["last_collect"]) / 3600
            if hours_passed < 1:
                return await i.response.send_message(f"⏳ Ждите еще {int((1-hours_passed)*60)} мин.", ephemeral=True)
            
            income = biz["level"] * 500
            accumulated = min(int(hours_passed * income), income * 24)
            await self.bot.db.update_wallet(i.user.id, accumulated)
            await self.bot.db.update_business(biz["biz_id"], last_collect=now)
            
            embed = discord.Embed(title="💵 Прибыль собрана", color=0x57F287)
            embed.description = f"Вы получили **{fmt(accumulated)}** RUB с организации **{biz['name']}**."
            await i.response.send_message(embed=embed)

        elif action.value == "upgrade":
            cost = biz["level"] * 10000
            u = await self.bot.db.get_user(i.user.id)
            if u["wallet"] < cost: return await i.response.send_message(f"❌ Нужно **{fmt(cost)}** RUB.", ephemeral=True)
            
            await self.bot.db.update_wallet(i.user.id, -cost)
            await self.bot.db.update_business(biz["biz_id"], level=biz["level"]+1)
            
            embed = discord.Embed(title="📈 Организация улучшена", color=0x5865F2)
            embed.description = f"Уровень повышен до **{biz['level']+1}**. Доход увеличен!"
            await i.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Organization(bot))