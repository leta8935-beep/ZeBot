import discord
from discord.ext import commands
from discord import app_commands
import asyncio


# ─── Модалки (2 шага) ───
class RegModalStep1(discord.ui.Modal, title="Регистрация (Шаг 1 из 2)"):
    surname = discord.ui.TextInput(label="Фамилия", placeholder="Иванов", max_length=50)
    name = discord.ui.TextInput(label="Имя", placeholder="Иван", max_length=50)
    patronymic = discord.ui.TextInput(label="Отчество", placeholder="Иванович", max_length=50)
    dob = discord.ui.TextInput(label="Дата рождения", placeholder="01.01.1990", max_length=20)
    pob = discord.ui.TextInput(label="Место рождения", placeholder="г. Москва", max_length=100)

    async def on_submit(self, interaction: discord.Interaction):
        # Сохраняем данные временно в памяти (в Python словаре)
        interaction.client.temp_reg_data[interaction.user.id] = {
            "surname": self.surname.value,
            "name": self.name.value,
            "patronymic": self.patronymic.value,
            "dob": self.dob.value,
            "pob": self.pob.value,
        }
        
        await interaction.response.send_message(
            "Шаг 1 из 2 завершен. Теперь нажмите кнопку ниже, чтобы заполнить биографию и фото.",
            ephemeral=True,
            view=NextStepView()
        )

class RegModalStep2(discord.ui.Modal, title="Регистрация (Шаг 2 из 2)"):
    bio = discord.ui.TextInput(label="Биография", style=discord.TextStyle.paragraph, max_length=1000)
    photo_url = discord.ui.TextInput(label="Ссылка на фото персонажа", placeholder="https://...", max_length=200)

    async def on_submit(self, interaction: discord.Interaction):
        # Достаем данные из шага 1
        data = interaction.client.temp_reg_data.get(interaction.user.id)
        if not data:
            return await interaction.response.send_message("Ошибка: данные шага 1 потеряны. Начните заново.", ephemeral=True)

        # Сохраняем в БД
        await interaction.client.db.save_passport(
            interaction.user.id,
            data["surname"], data["name"], data["patronymic"],
            data["dob"], data["pob"], self.bio.value, self.photo_url.value
        )
        # Очищаем память
        del interaction.client.temp_reg_data[interaction.user.id]

        # Отправляем анкету в канал проверки
        settings = await interaction.client.db.get_guild_settings(interaction.guild_id)
        if not settings or not settings["review_channel_id"]:
            return await interaction.response.send_message("❌ Канал для проверки не настроен. Сообщите администрации.", ephemeral=True)

        review_channel = interaction.guild.get_channel(int(settings["review_channel_id"]))
        if not review_channel:
            return await interaction.response.send_message("❌ Канал проверки не найден.", ephemeral=True)

        # Формируем эмбед анкеты
        embed = discord.Embed(title="Новая анкета", color=discord.Color.yellow())
        embed.add_field(name="Участник", value=f"{interaction.user.mention} (`{interaction.user.id}`)")
        embed.add_field(name="ФИО", value=f"{data['surname']} {data['name']} {data['patronymic']}")
        embed.add_field(name="Дата рождения", value=data["dob"])
        embed.add_field(name="Место рождения", value=data["pob"])
        embed.add_field(name="Биография", value=self.bio.value, inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_image(url=self.photo_url.value)

        view = ReviewView(target_user=interaction.user)
        msg = await review_channel.send(content=f"🔔 Проверка для {interaction.user.mention}", embed=embed, view=view)

        # Отправляем копию в ЛС
        try:
            await interaction.user.send("📝 **Копия вашей анкеты:**", embed=embed)
        except discord.Forbidden:
            pass # Если у пользователя закрыты ЛС

        await interaction.response.send_message("✅ Ваша анкета отправлена на проверку!", ephemeral=True)


# ─── Кнопка для перехода ко второму шагу ───
class NextStepView(discord.ui.View):
    @discord.ui.button(label="Заполнить биографию и фото", style=discord.ButtonStyle.primary)
    async def next_step(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RegModalStep2())


# ─── Кнопка "Заполнить анкету" ───
class RegistrationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Кнопка будет работать всегда

    @discord.ui.button(label="Заполнить анкету", style=discord.ButtonStyle.green, custom_id="start_registration")
    async def start_reg(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Проверяем, не зарегистрирован ли уже
        passport = await interaction.client.db.get_passport(interaction.user.id)
        if passport:
            return await interaction.response.send_message("❌ Вы уже зарегистрированы!", ephemeral=True)
        
        await interaction.response.send_modal(RegModalStep1())


# ─── Кнопки "Принять" и "Отклонить" для проверяющего ───
class ReviewView(discord.ui.View):
    def __init__(self, target_user: discord.Member):
        super().__init__(timeout=None)
        self.target_user = target_user

    @discord.ui.button(label="Принять", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Убираем кнопки
        for child in self.children:
            child.disabled = True

        # Меняем эмбед
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.set_footer(text=f"Одобрено | Проверяющий: {interaction.user.mention} ({interaction.user.name})")

        # Выдаем роли
        settings = await interaction.client.db.get_guild_settings(interaction.guild_id)
        if settings and settings["start_roles"]:
            role_ids = settings["start_roles"].split(",")
            roles_to_add = [interaction.guild.get_role(int(r)) for r in role_ids if r]
            roles_to_add = [r for r in roles_to_add if r]
            try:
                await self.target_user.add_roles(*roles_to_add)
            except:
                pass

        # ЛС пользователю
        try:
            await self.target_user.send("✅ Ваша анкета была **одобрена**! Добро пожаловать.")
        except:
            pass

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Отклонить", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        # ЛС пользователю
        try:
            await self.target_user.send("❌ Ваша анкета была **отклонена**.")
        except:
            pass

        # Удаляем сообщение из канала проверки
        await interaction.message.delete()


# ─── Команды ───
class Registration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="passport", description="Посмотреть свой паспорт")
    async def passport(self, i: discord.Interaction, member: discord.Member = None):
        member = member or i.user
        p = await self.bot.db.get_passport(member.id)
        
        if not p:
            return await i.response.send_message("❌ Паспорт не найден. Вы не зарегистрированы.", ephemeral=True)

        embed = discord.Embed(title=f"📄 Паспорт: {p['surname']} {p['name']}", color=discord.Color.blue())
        embed.add_field(name="Отчество", value=p["patronymic"], inline=True)
        embed.add_field(name="Дата рождения", value=p["dob"], inline=True)
        embed.add_field(name="Место рождения", value=p["pob"], inline=True)
        embed.add_field(name="Биография", value=p["bio"], inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_image(url=p["photo_url"])
        await i.response.send_message(embed=embed)

    @app_commands.command(name="edit_passport", description="[ADMIN] Изменить данные паспорта игрока")
    @app_commands.checks.has_permissions(administrator=True)
    async def edit_passport(self, i: discord.Interaction, member: discord.Member):
        p = await self.bot.db.get_passport(member.id)
        if not p:
            return await i.response.send_message("❌ У этого игрока нет паспорта.", ephemeral=True)

        view = EditSelectView(member)
        await i.response.send_message(f"Что вы хотите изменить у {member.mention}?", view=view, ephemeral=True)


# ─── Меню выбора поля для редактирования ───
class EditSelectView(discord.ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=60)
        self.member = member

    @discord.ui.select(
        placeholder="Выберите поле для изменения...",
        options=[
            discord.SelectOption(label="Фамилия", value="surname"),
            discord.SelectOption(label="Имя", value="name"),
            discord.SelectOption(label="Отчество", value="patronymic"),
            discord.SelectOption(label="Дата рождения", value="dob"),
            discord.SelectOption(label="Место рождения", value="pob"),
            discord.SelectOption(label="Биография", value="bio"),
            discord.SelectOption(label="Ссылка на фото", value="photo_url"),
        ]
    )
    async def select_field(self, interaction: discord.Interaction, select: discord.ui.Select):
        field = select.values[0]
        await interaction.response.send_modal(EditModal(self.member, field))


# ─── Модалка для ввода нового значения ───
class EditModal(discord.ui.Modal, title="Изменение данных"):
    value = discord.ui.TextInput(label="Новое значение", style=discord.TextStyle.paragraph)

    def __init__(self, member: discord.Member, field: str):
        super().__init__()
        self.member = member
        self.field = field
        self.value.label = f"Новое значение для '{field}'"

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.client.db.update_passport_field(self.member.id, self.field, self.value.value)
        await interaction.response.send_message(f"✅ Поле `{self.field}` обновлено!", ephemeral=True)


async def setup(bot):
    # Создаем словарь в памяти для передачи данных между модалками
    if not hasattr(bot, 'temp_reg_data'):
        bot.temp_reg_data = {}
    await bot.add_cog(Registration(bot))