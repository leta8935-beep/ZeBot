import asyncpg


class Database:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=5)
        async with self.pool.acquire() as c:
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

    async def get_user(self, user_id: int):
        async with self.pool.acquire() as c:
            await c.execute(
                "INSERT INTO users (user_id) VALUES ($1) "
                "ON CONFLICT DO NOTHING", user_id)
            return await c.fetchrow(
                "SELECT * FROM users WHERE user_id=$1", user_id)

    async def update_wallet(self, user_id: int, delta: int):
        async with self.pool.acquire() as c:
            await c.execute(
                "UPDATE users SET wallet = GREATEST(wallet + $1, 0) "
                "WHERE user_id=$2", delta, user_id)

    async def set_wallet(self, user_id: int, amount: int):
        async with self.pool.acquire() as c:
            await c.execute(
                "UPDATE users SET wallet = $1 WHERE user_id=$2",
                amount, user_id)

    async def log(self, from_id, to_id, amount, kind):
        async with self.pool.acquire() as c:
            await c.execute(
                "INSERT INTO transactions (from_id, to_id, amount, kind) "
                "VALUES ($1,$2,$3,$4)", from_id, to_id, amount, kind)