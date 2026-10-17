import discord
from discord.ext import commands
from discord import app_commands


class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup", description="[ADMIN] Настроить канал проверки и роли")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(citizen_roles="ID ролей для граждан через запятую без пробелов (например: 123456789,987654321)")
    async def setup_cmd(
        self, i: discord.Interaction, 
        review_channel: discord.TextChannel,
        citizen_roles: str,
        curator_role: discord.Role = None,
        mod_role: discord.Role = None,
        admin_role: discord.Role = None,
        pr_role: discord.Role = None
    ):
        await self.bot.db.set_guild_setting(i.guild.id, "review_channel_id", str(review_channel.id))
        await self.bot.db.set_guild_setting(i.guild.id, "start_roles", citizen_roles.replace(" ", ""))
        
        if curator_role: await self.bot.db.set_guild_setting(i.guild.id, "curator_role", str(curator_role.id))
        if mod_role: await self.bot.db.set_guild_setting(i.guild.id, "mod_role", str(mod_role.id))
        if admin_role: await self.bot.db.set_guild_setting(i.guild.id, "admin_role", str(admin_role.id))
        if pr_role: await self.bot.db.set_guild_setting(i.guild.id, "pr_role", str(pr_role.id))
        
        msg = f"✅ **Настройки сохранены!**\n📌 Канал проверки: {review_channel.mention}\n👤 Роли граждан (ID): `{citizen_roles}`"
        if curator_role: msg += f"\n👑 Куратор: {curator_role.mention}"
        if mod_role: msg += f"\n🛡️ Модератор: {mod_role.mention}"
        if admin_role: msg += f"\n⚙️ Администратор: {admin_role.mention}"
        if pr_role: msg += f"\n📢 Пиар-менеджер: {pr_role.mention}"
        
        await i.response.send_message(msg, ephemeral=True)

    @app_commands.command(name="idtext", description="[ADMIN] Отправить панель")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(message_type=[
        app_commands.Choice(name="Регистрация (Граждане)", value="registration"),
        app_commands.Choice(name="Набор в Стафф", value="staff_registration")
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
        embed = discord.Embed(title="📋 Заявка", description=text, color=discord.Color.blue())
        file_to_send = None

        if image_file:
            file_to_send = await image_file.to_file()
            embed.set_image(url=f"attachment://{file_to_send.filename}")
        elif image_url:
            embed.set_image(url=image_url)

        # Импортируем нужные View из registration.py
        from cogs.registration import RegistrationView, StaffRegistrationView

        if message_type.value == "registration":
            embed.title = "📋 Регистрация Гражданина"
            view = RegistrationView()
        elif message_type.value == "staff_registration":
            embed.title = "👑 Набор в Администрацию"
            view = StaffRegistrationView()
        
        await channel.send(embed=embed, view=view, file=file_to_send)
        await i.response.send_message(f"✅ Панель отправлена в {channel.mention}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Settings(bot))