import discord
from discord.ext import commands
from discord import app_commands


class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ─── Одна команда для настройки сервера ───
    @app_commands.command(name="setup", description="[ADMIN] Настроить канал проверки и стартовые роли")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_cmd(
        self, i: discord.Interaction, 
        review_channel: discord.TextChannel,
        role1: discord.Role,
        role2: discord.Role = None,
        role3: discord.Role = None
    ):
        # Сохраняем канал
        await self.bot.db.set_guild_setting(i.guild.id, "review_channel_id", str(review_channel.id))
        
        # Сохраняем роли (только те, что были указаны)
        roles = [str(r.id) for r in [role1, role2, role3] if r]
        await self.bot.db.set_guild_setting(i.guild.id, "start_roles", ",".join(roles))
        
        roles_text = ", ".join([r.mention for r in [role1, role2, role3] if r])
        await i.response.send_message(
            f"✅ **Настройки сохранены!**\n"
            f"📌 Канал проверки: {review_channel.mention}\n"
            f"🎭 Стартовые роли: {roles_text}", 
            ephemeral=True
        )

    # ─── Универсальная команда для панелей ───
    @app_commands.command(name="idtext", description="[ADMIN] Отправить панель (регистрация и т.д.)")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(message_type=[
        app_commands.Choice(name="Регистрация", value="registration")
    ])
    async def idtext(
        self, 
        i: discord.Interaction,
        channel: discord.TextChannel,
        message_type: app_commands.Choice[str],
        text: str = "Нажмите на кнопку ниже, чтобы подать заявку.",
        image_file: discord.Attachment = None,
        image_url: str = None
    ):
        embed = discord.Embed(title="📋 Регистрация", description=text, color=discord.Color.blue())
        file_to_send = None

        # Обработка картинки (приоритет у загруженного файла)
        if image_file:
            file_to_send = await image_file.to_file()
            embed.set_image(url=f"attachment://{file_to_send.filename}")
        elif image_url:
            embed.set_image(url=image_url)

        # Отправка в зависимости от типа
        if message_type.value == "registration":
            from cogs.registration import RegistrationView
            view = RegistrationView()
            await channel.send(embed=embed, view=view, file=file_to_send)
            await i.response.send_message(f"✅ Панель регистрации отправлена в {channel.mention}", ephemeral=True)
        
        # Сюда в будущем можно добавлять другие типы (например, для магазина)


async def setup(bot):
    await bot.add_cog(Settings(bot))