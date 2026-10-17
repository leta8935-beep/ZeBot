import asyncpg


class Database:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=5)
        async with self.pool.acquire() as c:
            # Твои старые таблицы
            await c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                wallet  BIGINT NOT NULL DEFAULT 500
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id      SERIAL PRIMARY KEY,
                from_id BIGINT,
                to_id   BIGINT,
                amount  BIGINT NOT NULL,
                kind    TEXT NOT NULL
            );
            """)
            # НОВЫЕ таблицы для регистрации и настроек
            await c.execute("""
            CREATE TABLE IF NOT EXISTS passports (
                user_id BIGINT PRIMARY KEY,
                surname TEXT NOT NULL,
                name TEXT NOT NULL,
                patronymic TEXT NOT NULL,
                dob TEXT NOT NULL,
                pob TEXT NOT NULL,
                bio TEXT NOT NULL,
                photo_url TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id BIGINT PRIMARY KEY,
                review_channel_id BIGINT,
                start_roles TEXT, -- Храним ID ролей через запятую
                embed_image TEXT,
                embed_desc TEXT
            );
            """)

    async def get_user(self, user_id: int):
        async with self.pool.acquire() as c:
            await c.execute("INSERT INTO users (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user_id)
            return await c.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)

    async def update_wallet(self, user_id: int, delta: int):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET wallet = GREATEST(wallet + $1, 0) WHERE user_id=$2", delta, user_id)

    async def set_wallet(self, user_id: int, amount: int):
        async with self.pool.acquire() as c:
            await c.execute("UPDATE users SET wallet = $1 WHERE user_id=$2", amount, user_id)

    async def log(self, from_id, to_id, amount, kind):
        async with self.pool.acquire() as c:
            await c.execute("INSERT INTO transactions (from_id, to_id, amount, kind) VALUES ($1,$2,$3,$4)", from_id, to_id, amount, kind)

    # ─── Методы для регистрации ───
    async def save_passport(self, user_id, surname, name, patronymic, dob, pob, bio, photo_url):
        async with self.pool.acquire() as c:
            await c.execute("""
                INSERT INTO passports (user_id, surname, name, patronymic, dob, pob, bio, photo_url)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
                ON CONFLICT (user_id) DO UPDATE SET 
                surname=$2, name=$3, patronymic=$4, dob=$5, pob=$6, bio=$7, photo_url=$8
            """, user_id, surname, name, patronymic, dob, pob, bio, photo_url)

    async def get_passport(self, user_id: int):
        async with self.pool.acquire() as c:
            return await c.fetchrow("SELECT * FROM passports WHERE user_id=$1", user_id)

    async def update_passport_field(self, user_id: int, field: str, value: str):
        allowed_fields = ["surname", "name", "patronymic", "dob", "pob", "bio", "photo_url"]
        if field not in allowed_fields:
            return False
        async with self.pool.acquire() as c:
            await c.execute(f"UPDATE passports SET {field}=$1 WHERE user_id=$2", value, user_id)
        return True

    # ─── Методы для настроек сервера ───
    async def set_guild_setting(self, guild_id: int, column: str, value: str):
        async with self.pool.acquire() as c:
            # Проверяем, есть ли запись
            exists = await c.fetchval("SELECT 1 FROM guild_settings WHERE guild_id=$1", guild_id)
            if not exists:
                await c.execute("INSERT INTO guild_settings (guild_id) VALUES ($1)", guild_id)
            # Обновляем нужную колонку
            await c.execute(f"UPDATE guild_settings SET {column}=$1 WHERE guild_id=$2", value, guild_id)

    async def get_guild_settings(self, guild_id: int):
        async with self.pool.acquire() as c:
            return await c.fetchrow("SELECT * FROM guild_settings WHERE guild_id=$1", guild_id)