import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from database import Database

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

COGS = ["cogs.economy", "cogs.admin"]


class Zebot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())
        self.db = Database(DATABASE_URL)

    async def setup_hook(self):
        await self.db.connect()
        for cog in COGS:
            await self.load_extension(cog)
        await self.tree.sync()
        print("Бот запущен, команды синхронизированы!")


if __name__ == "__main__":
    if not TOKEN or not DATABASE_URL:
        raise RuntimeError("Заполни DISCORD_TOKEN и DATABASE_URL в .env")
    Zebot().run(TOKEN)