import os
import discord
from discord.ext import commands
from discord import app_commands
import asyncpg
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
STARTING_WALLET = 500
TAX_RATE = 0.05

def fmt(n: int) -> str:
    return f"{n:,}".replace(",", " ")

class Zebot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())
        self.pool = None

    async def setup_hook(self):
        # Подключение к базе данных и создание таблиц
        self.pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
        async with self.pool.acquire() as c:
            await c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                wallet BIGINT NOT NULL DEFAULT 500
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                from_id BIGINT,
                to_id BIGINT,
                amount BIGINT NOT NULL,
                kind TEXT NOT NULL
            );
            """)
        await self.tree.sync()
        print("Бот запущен, база подключена, команды синхронизированы!")

bot = Zebot()

async def get_user(user_id):
    async with bot.pool.acquire() as c:
        await c.execute("INSERT INTO users (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user_id)
        return await c.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)

def is_admin(interaction: discord.Interaction) -> bool:
    if not interaction.user.guild_permissions.administrator:
        raise app_commands.CheckFailure("Только для администраторов.")
    return True

@bot.tree.command(name="balance", description="Показать баланс")
async def balance(i: discord.Interaction, member: discord.Member = None):
    is_adm = i.user.guild_permissions.administrator
    if member and member.id != i.user.id and not is_adm:
        return await i.response.send_message("🚫 Только админ может смотреть чужой баланс.", ephemeral=True)
    
    target = member or i.user
    u = await get_user(target.id)
    e = discord.Embed(title=f"💰 Баланс {target.display_name}", description=f"## {fmt(u['wallet'])} монет", color=discord.Color.green())
    await i.response.send_message(embed=e, ephemeral=(target.id == i.user.id))

@bot.tree.command(name="pay", description="Перевести деньги (налог 5%)")
async def pay(i: discord.Interaction, member: discord.Member, amount: int):
    if member.bot or member.id == i.user.id or amount <= 0:
        return await i.response.send_message("❌ Некорректный получатель или сумма.", ephemeral=True)
    
    sender = await get_user(i.user.id)
    if sender['wallet'] < amount:
        return await i.response.send_message(f"❌ Недостаточно средств. У тебя: {fmt(sender['wallet'])}", ephemeral=True)
    
    await get_user(member.id)
    tax = int(amount * TAX_RATE)
    net = amount - tax
    
    async with bot.pool.acquire() as c:
        await c.execute("UPDATE users SET wallet = wallet - $1 WHERE user_id=$2", amount, i.user.id)
        await c.execute("UPDATE users SET wallet = wallet + $1 WHERE user_id=$2", net, member.id)
        await c.execute("INSERT INTO transactions (from_id, to_id, amount, kind) VALUES ($1,$2,$3,'pay')", i.user.id, member.id, amount)
        
    e = discord.Embed(title="💸 Перевод выполнен", color=discord.Color.blurple())
    e.add_field(name="От", value=i.user.mention)
    e.add_field(name="Кому", value=member.mention)
    e.add_field(name="Сумма", value=f"{fmt(amount)} (налог: {fmt(tax)})", inline=False)
    await i.response.send_message(embed=e)

@bot.tree.command(name="admin", description="[ADMIN] Управление балансом")
@app_commands.choices(action=[
    app_commands.Choice(name="➕ Добавить", value="add"),
    app_commands.Choice(name="➖ Убрать", value="remove"),
    app_commands.Choice(name="🔄 Обновить", value="update"),
])
@app_commands.check(is_admin)
async def admin(i: discord.Interaction, action: app_commands.Choice[str], member: discord.Member, amount: int):
    if amount < 0: 
        return await i.response.send_message("❌ Сумма должна быть больше нуля.", ephemeral=True)
    
    u = await get_user(member.id)
    before = u['wallet']
    
    async with bot.pool.acquire() as c:
        if action.value == "add":
            await c.execute("UPDATE users SET wallet = wallet + $1 WHERE user_id=$2", amount, member.id)
            after = before + amount
        elif action.value == "remove":
            await c.execute("UPDATE users SET wallet = GREATEST(wallet - $1, 0) WHERE user_id=$2", amount, member.id)
            after = max(before - amount, 0)
        else:
            await c.execute("UPDATE users SET wallet = $1 WHERE user_id=$2", amount, member.id)
            after = amount
        await c.execute("INSERT INTO transactions (from_id, to_id, amount, kind) VALUES ($1,$2,$3,$4)", i.user.id, member.id, amount, f"admin_{action.value}")
        
    e = discord.Embed(title=f"{action.name} баланса", color=discord.Color.orange())
    e.add_field(name="Игрок", value=member.mention)
    e.add_field(name="Было", value=fmt(before))
    e.add_field(name="Стало", value=fmt(after))
    await i.response.send_message(embed=e, ephemeral=True)

@admin.error
async def admin_error(i: discord.Interaction, error):
    if isinstance(error, app_commands.CheckFailure):
        await i.response.send_message(f"🚫 {error}", ephemeral=True)

bot.run(TOKEN)
