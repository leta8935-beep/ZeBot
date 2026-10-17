import discord
from discord.ext import commands
from discord import app_commands


class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_review", description="[ADMIN] Настроить канал для проверки анкет")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_review(self, i: discord.Interaction, channel: discord.TextChannel):
        await self.bot.db.set_guild_setting(i.guild.id, "review_channel_id", str(channel.id))
        await i.response.send_message(f"✅ Канал проверки установлен: {channel.mention}", ephemeral=True)

    @app_commands.command(name="setup_roles", description="[ADMIN] Настроить роли, выдаваемые после регистрации")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_roles(self, i: discord.Interaction, role1: discord.Role, role2: discord.Role = None, role3: discord.Role = None):
        roles = [str(r.id) for r in [role1, role2, role3] if r]
        await self.bot.db.set_guild_setting(i.guild.id, "start_roles", ",".join(roles))
        await i.response.send_message(f"✅ Стартовые роли настроены: {', '.join([r.mention for r in [role1, role2, role3] if r])}", ephemeral=True)

    @app_commands.command(name="setup_embed", description="[ADMIN] Настроить картинку и текст для сообщения с кнопкой регистрации")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_embed(self, i: discord.Interaction, image_url: str, description: str):
        await self.bot.db.set_guild_setting(i.guild.id, "embed_image", image_url)
        await self.bot.db.set_guild_setting(i.guild.id, "embed_desc", description)
        await i.response.send_message("✅ Настройки эмбеда сохранены!", ephemeral=True)

    @app_commands.command(name="send_registration", description="[ADMIN] Отправить сообщение с кнопкой регистрации")
    @app_commands.checks.has_permissions(administrator=True)
    async def send_registration(self, i: discord.Interaction):
        settings = await self.bot.db.get_guild_settings(i.guild.id)
        
        desc = settings["embed_desc"] if settings and settings["embed_desc"] else "Нажмите на кнопку ниже, чтобы подать заявку на регистрацию в городе."
        img = settings["embed_image"] if settings and settings["embed_image"] else None

        embed = discord.Embed(title="📋 Регистрация", description=desc, color=discord.Color.blue())
        if img:
            embed.set_image(url=img)

        # Импортируем View из файла регистрации
        from cogs.registration import RegistrationView
        view = RegistrationView()
        
        await i.channel.send(embed=embed, view=view)
        await i.response.send_message("✅ Сообщение с регистрацией отправлено!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Settings(bot))