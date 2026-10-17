import discord
from discord.ext import commands
from discord import app_commands


# ═══════════════════════════════════════════════════
# 1. РЕГИСТРАЦИЯ ГРАЖДАН (2 шага)
# ═══════════════════════════════════════════════════
class RegModalStep1(discord.ui.Modal, title="Регистрация (Шаг 1 из 2)"):
    surname = discord.ui.TextInput(label="Фамилия", placeholder="Иванов", max_length=50)
    name = discord.ui.TextInput(label="Имя", placeholder="Иван", max_length=50)
    patronymic = discord.ui.TextInput(label="Отчество", placeholder="Иванович", max_length=50)
    dob = discord.ui.TextInput(label="Дата рождения", placeholder="01.01.1990", max_length=20)
    pob = discord.ui.TextInput(label="Место рождения", placeholder="г. Москва", max_length=100)

    async def on_submit(self, interaction: discord.Interaction):
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
        data = interaction.client.temp_reg_data.get(interaction.user.id)
        if not data:
            return await interaction.response.send_message("Ошибка: данные шага 1 потеряны. Начните заново.", ephemeral=True)

        await interaction.client.db.save_passport(
            interaction.user.id,
            data["surname"], data["name"], data["patronymic"],
            data["dob"], data["pob"], self.bio.value, self.photo_url.value
        )
        del interaction.client.temp_reg_data[interaction.user.id]

        settings = await interaction.client.db.get_guild_settings(interaction.guild_id)
        if not settings or not settings["review_channel_id"]:
            return await interaction.response.send_message("❌ Канал для проверки не настроен.", ephemeral=True)

        review_channel = interaction.guild.get_channel(int(settings["review_channel_id"]))
        
        embed = discord.Embed(title="Новая анкета (Гражданин)", color=discord.Color.yellow())
        embed.add_field(name="Участник", value=f"{interaction.user.mention} (`{interaction.user.id}`)")
        embed.add_field(name="ФИО", value=f"{data['surname']} {data['name']} {data['patronymic']}")
        embed.add_field(name="Дата рождения", value=data["dob"])
        embed.add_field(name="Место рождения", value=data["pob"])
        embed.add_field(name="Биография", value=self.bio.value, inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_image(url=self.photo_url.value)

        view = ReviewView(target_user=interaction.user)
        await review_channel.send(content=f"🔔 Проверка для {interaction.user.mention}", embed=embed, view=view)

        try:
            await interaction.user.send("📝 **Копия вашей анкеты:**", embed=embed)
        except discord.Forbidden:
            pass

        await interaction.response.send_message("✅ Ваша анкета отправлена на проверку!", ephemeral=True)

class NextStepView(discord.ui.View):
    @discord.ui.button(label="Заполнить биографию и фото", style=discord.ButtonStyle.primary)
    async def next_step(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RegModalStep2())

class RegistrationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Заполнить анкету", style=discord.ButtonStyle.green, custom_id="start_registration")
    async def start_reg(self, interaction: discord.Interaction, button: discord.ui.Button):
        passport = await interaction.client.db.get_passport(interaction.user.id)
        if passport:
            return await interaction.response.send_message("❌ Вы уже зарегистрированы!", ephemeral=True)
        await interaction.response.send_modal(RegModalStep1())

class ReviewView(discord.ui.View):
    def __init__(self, target_user: discord.Member):
        super().__init__(timeout=None)
        self.target_user = target_user

    @discord.ui.button(label="Принять", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children: child.disabled = True
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.set_footer(text=f"Одобрено | Проверяющий: {interaction.user.mention} ({interaction.user.name})")

        settings = await interaction.client.db.get_guild_settings(interaction.guild_id)
        if settings and settings["start_roles"]:
            role_ids = settings["start_roles"].split(",")
            roles_to_add = [interaction.guild.get_role(int(r)) for r in role_ids if r]
            roles_to_add = [r for r in roles_to_add if r]
            try:
                await self.target_user.add_roles(*roles_to_add)
            except: pass

        try:
            await self.target_user.send("✅ Ваша анкета была **одобрена**! Добро пожаловать.")
        except: pass

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Отклонить", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.target_user.send("❌ Ваша анкета была **отклонена**.")
        except: pass
        await interaction.message.delete()


# ═══════════════════════════════════════════════════
# 2. НАБОР В СТАФФ (1 шаг)
# ═══════════════════════════════════════════════════
class StaffModal(discord.ui.Modal, title="Анкета в Администрацию"):
    name = discord.ui.TextInput(label="Ваше имя/никнейм", placeholder="Иван / Vanya", max_length=50)
    age = discord.ui.TextInput(label="Ваш возраст", placeholder="18", max_length=2)
    position = discord.ui.TextInput(
        label="Желаемая должность", 
        placeholder="Куратор / Модератор / Администратор / Пиар-менеджер",
        max_length=30
    )
    experience = discord.ui.TextInput(label="Опыт в RP/администрировании", style=discord.TextStyle.paragraph, max_length=1000)
    motivation = discord.ui.TextInput(label="Почему мы должны выбрать именно вас?", style=discord.TextStyle.paragraph, max_length=1000)

    async def on_submit(self, interaction: discord.Interaction):
        pos_text = self.position.value.lower()
        valid_positions = {
            "куратор": "curator_role", 
            "модератор": "mod_role", 
            "администратор": "admin_role", 
            "пиар-менеджер": "pr_role", 
            "пиар": "pr_role"
        }
        
        matched_column = None
        for k, v in valid_positions.items():
            if k in pos_text:
                matched_column = v
                break
                
        if not matched_column:
            return await interaction.response.send_message(
                "❌ Вы указали неверную должность. Выберите одну из: Куратор, Модератор, Администратор, Пиар-менеджер.", 
                ephemeral=True
            )

        settings = await interaction.client.db.get_guild_settings(interaction.guild_id)
        if not settings or not settings["review_channel_id"]:
            return await interaction.response.send_message("❌ Канал проверки не настроен.", ephemeral=True)

        review_channel = interaction.guild.get_channel(int(settings["review_channel_id"]))
        
        embed = discord.Embed(title="Заявка в Стафф", color=discord.Color.purple())
        embed.add_field(name="Кандидат", value=f"{interaction.user.mention} (`{interaction.user.id}`)")
        embed.add_field(name="Имя", value=self.name.value, inline=True)
        embed.add_field(name="Возраст", value=self.age.value, inline=True)
        embed.add_field(name="Должность", value=self.position.value, inline=True)
        embed.add_field(name="Опыт", value=self.experience.value, inline=False)
        embed.add_field(name="Мотивация", value=self.motivation.value, inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        view = StaffReviewView(target_user=interaction.user, role_column=matched_column, pos_name=self.position.value)
        await review_channel.send(content=f"🔔 Новая заявка в стафф от {interaction.user.mention}", embed=embed, view=view)

        try:
            await interaction.user.send("📝 Ваша заявка в администрацию отправлена на рассмотрение!", embed=embed)
        except discord.Forbidden:
            pass

        await interaction.response.send_message("✅ Ваша заявка отправлена на проверку!", ephemeral=True)

class StaffRegistrationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Подать заявку в стафф", style=discord.ButtonStyle.blurple, custom_id="staff_reg_btn")
    async def start_staff_reg(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(StaffModal())

class StaffReviewView(discord.ui.View):
    def __init__(self, target_user: discord.Member, role_column: str, pos_name: str):
        super().__init__(timeout=None)
        self.target_user = target_user
        self.role_column = role_column 
        self.pos_name = pos_name

    @discord.ui.button(label="Принять", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children: child.disabled = True
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.set_footer(text=f"Одобрено | Проверяющий: {interaction.user.mention} ({interaction.user.name})")

        settings = await interaction.client.db.get_guild_settings(interaction.guild_id)
        if settings and settings[self.role_column]:
            role = interaction.guild.get_role(int(settings[self.role_column]))
            if role:
                try:
                    await self.target_user.add_roles(role)
                except: pass

        try:
            await self.target_user.send(f"✅ Ваша заявка на должность **{self.pos_name}** была **одобрена**!")
        except: pass

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Отклонить", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.target_user.send(f"❌ Ваша заявка на должность **{self.pos_name}** была **отклонена**.")
        except: pass
        await interaction.message.delete()


# ═══════════════════════════════════════════════════
# 3. КОМАНДЫ (/passport, /edit_passport, /register)
# ═══════════════════════════════════════════════════
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

    @app_commands.command(name="register", description="[ADMIN] Зарегистрировать игрока вручную")
    @app_commands.checks.has_permissions(administrator=True)
    async def register_admin(
        self, i: discord.Interaction, 
        member: discord.Member,
        surname: str,
        name: str,
        patronymic: str,
        dob: str,
        pob: str,
        bio: str,
        photo_url: str
    ):
        await self.bot.db.save_passport(
            member.id, surname, name, patronymic, dob, pob, bio, photo_url
        )

        settings = await self.bot.db.get_guild_settings(i.guild.id)
        roles_added_text = "Нет"
        
        if settings and settings["start_roles"]:
            role_ids = settings["start_roles"].split(",")
            roles_to_add = [i.guild.get_role(int(r)) for r in role_ids if r]
            roles_to_add = [r for r in roles_to_add if r]
            
            if roles_to_add:
                try:
                    await member.add_roles(*roles_to_add)
                    roles_added_text = ", ".join([r.mention for r in roles_to_add])
                except discord.Forbidden:
                    roles_added_text = "Ошибка: у бота нет прав на выдачу ролей (проверь иерархию)"

        embed = discord.Embed(title="✅ Игрок зарегистрирован", color=discord.Color.green())
        embed.add_field(name="Игрок", value=member.mention, inline=False)
        embed.add_field(name="ФИО", value=f"{surname} {name} {patronymic}", inline=False)
        embed.add_field(name="Выданы роли", value=roles_added_text, inline=False)
        
        await i.response.send_message(embed=embed, ephemeral=True)

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
    if not hasattr(bot, 'temp_reg_data'):
        bot.temp_reg_data = {}
    await bot.add_cog(Registration(bot))
