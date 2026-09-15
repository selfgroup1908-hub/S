import aiosqlite
from config import LOG_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS search_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER,
    query     TEXT,
    kind      TEXT,
    found     INTEGER,
    ts        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


async def init_logs():
    async with aiosqlite.connect(LOG_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def log_search(user_id: int, query: str, kind: str, found: bool):
    async with aiosqlite.connect(LOG_PATH) as db:
        await db.execute(
            "INSERT INTO search_log (user_id, query, kind, found) VALUES (?,?,?,?)",
            (user_id, query, kind, int(found)),
        )
        await db.commit()


async def get_recent_logs(limit: int = 20):
    async with aiosqlite.connect(LOG_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM search_log ORDER BY id DESC LIMIT ?", (limit,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def count_searches() -> int:
    async with aiosqlite.connect(LOG_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM search_log") as cur:
            (n,) = await cur.fetchone()
            return n
