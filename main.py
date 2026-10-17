import asyncio
import logging
import discord
from discord.ext import commands
import config
from database import Database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("zebot")

COGS = ["cogs.economy", "cogs.admin"]


class Zebot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.db = Database(config.DATABASE_URL)

    async def setup_hook(self):
        await self.db.connect()
        log.info("DB connected")
        for c in COGS:
            await self.load_extension(c)
            log.info(f"Loaded {c}")
        await self.tree.sync()
        log.info("Slash commands synced")

    async def on_ready(self):
        log.info(f"Logged in as {self.user} ({self.user.id})")

    async def close(self):
        await self.db.close()
        await super().close()


async def main():
    if not config.TOKEN or not config.DATABASE_URL:
        raise RuntimeError("Заполни DISCORD_TOKEN и DATABASE_URL в .env")
    bot = Zebot()
    await bot.start(config.TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
