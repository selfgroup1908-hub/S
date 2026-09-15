import aiosqlite
from config import DB_PATH

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    first_name  TEXT,
    last_name   TEXT,
    phone       TEXT,
    note        TEXT,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_phone    ON users(phone);

-- FTS5 برای جستجوی جزئی نام
CREATE VIRTUAL TABLE IF NOT EXISTS users_fts USING fts5(
    first_name, last_name, username, note,
    content='users', content_rowid='user_id',
    tokenize='unicode61'
);

-- تریگرها برای همگام‌سازی FTS
CREATE TRIGGER IF NOT EXISTS users_ai AFTER INSERT ON users BEGIN
  INSERT INTO users_fts(rowid, first_name, last_name, username, note)
  VALUES (new.user_id, new.first_name, new.last_name, new.username, new.note);
END;

CREATE TRIGGER IF NOT EXISTS users_ad AFTER DELETE ON users BEGIN
  INSERT INTO users_fts(users_fts, rowid, first_name, last_name, username, note)
  VALUES ('delete', old.user_id, old.first_name, old.last_name, old.username, old.note);
END;

CREATE TRIGGER IF NOT EXISTS users_au AFTER UPDATE ON users BEGIN
  INSERT INTO users_fts(users_fts, rowid, first_name, last_name, username, note)
  VALUES ('delete', old.user_id, old.first_name, old.last_name, old.username, old.note);
  INSERT INTO users_fts(rowid, first_name, last_name, username, note)
  VALUES (new.user_id, new.first_name, new.last_name, new.username, new.note);
END;
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def get_by_id(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_by_username(username: str):
    username = username.lstrip("@").lower()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE LOWER(username) = ?", (username,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_by_phone(phone: str):
    phone = phone.replace("+", "").replace(" ", "").replace("-", "")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE phone = ?", (phone,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def search_by_name(query: str, limit: int = 20):
    """جستجوی جزئی — FTS5"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # FTS5 با ستاره برای prefix matching
        q = " ".join(f"{w}*" for w in query.split())
        async with db.execute(
            """SELECT u.* FROM users u
               JOIN users_fts f ON u.user_id = f.rowid
               WHERE users_fts MATCH ?
               LIMIT ?""",
            (q, limit),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def upsert_user(user_id: int, **fields):
    if not fields:
        return
    cols = ["user_id"] + list(fields.keys())
    placeholders = ",".join("?" * len(cols))
    updates = ",".join(f"{k}=excluded.{k}" for k in fields.keys())
    sql = f"""
        INSERT INTO users ({','.join(cols)}) VALUES ({placeholders})
        ON CONFLICT(user_id) DO UPDATE SET {updates},
            updated_at = CURRENT_TIMESTAMP
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(sql, [user_id] + list(fields.values()))
        await db.commit()


async def delete_user(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.commit()
        return cur.rowcount > 0


async def count_users() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            (n,) = await cur.fetchone()
            return n


async def export_all():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users") as cur:
            return [dict(r) for r in await cur.fetchall()]
