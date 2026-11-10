import asyncio
from dataclasses import dataclass
from pathlib import Path

import aiosqlite

from bot.metrics import METRICS, METRICS_BY_KEY


@dataclass(frozen=True)
class Goal:
    key: str
    target: int
    source: str
    role_id: int | None
    value: int


@dataclass(frozen=True)
class Board:
    guild_id: int
    channel_id: int
    message_id: int


class Store:
    def __init__(self, connection: aiosqlite.Connection):
        self.db = connection
        self.lock = asyncio.Lock()

    @classmethod
    async def open(cls, path: Path) -> "Store":
        path.parent.mkdir(parents=True, exist_ok=True)
        db = await aiosqlite.connect(path)
        db.row_factory = aiosqlite.Row
        try:
            await db.executescript("""
                PRAGMA journal_mode=WAL;
                PRAGMA busy_timeout=5000;
                CREATE TABLE IF NOT EXISTS goals (
                    guild_id INTEGER NOT NULL,
                    metric TEXT NOT NULL,
                    target INTEGER NOT NULL CHECK(target > 0),
                    source TEXT NOT NULL,
                    role_id INTEGER,
                    value INTEGER NOT NULL DEFAULT 0 CHECK(value >= 0),
                    PRIMARY KEY (guild_id, metric)
                );
                CREATE TABLE IF NOT EXISTS boards (
                    guild_id INTEGER PRIMARY KEY,
                    channel_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL
                );
            """)
            await db.commit()
        except BaseException:
            await db.close()
            raise
        return cls(db)

    async def close(self) -> None:
        await self.db.close()

    async def _seed(self, guild_id: int) -> None:
        await self.db.executemany(
            "INSERT OR IGNORE INTO goals (guild_id, metric, target, source) VALUES (?, ?, ?, ?)",
            [(guild_id, m.key, m.target, m.source) for m in METRICS],
        )

    async def goals(self, guild_id: int) -> list[Goal]:
        async with self.lock:
            await self._seed(guild_id)
            await self.db.commit()
            async with self.db.execute(
                "SELECT metric, target, source, role_id, value FROM goals WHERE guild_id = ?",
                (guild_id,),
            ) as cursor:
                rows = {row["metric"]: row for row in await cursor.fetchall()}
        return [
            Goal(
                m.key,
                rows[m.key]["target"],
                rows[m.key]["source"],
                rows[m.key]["role_id"],
                rows[m.key]["value"],
            )
            for m in METRICS
        ]

    async def configure(
        self,
        guild_id: int,
        key: str,
        *,
        target: int | None = None,
        role_id: int | None = None,
        value: int | None = None,
    ) -> None:
        metric = METRICS_BY_KEY[key]
        if target is not None and target <= 0:
            raise ValueError("La meta debe ser mayor que cero.")
        if value is not None and value < 0:
            raise ValueError("El contador no puede ser negativo.")
        if value is not None and role_id is not None:
            raise ValueError("Elige un rol o un valor manual, no ambos.")
        if (role_id is not None or value is not None) and metric.source in {"members", "boosts"}:
            raise ValueError("Discord calcula automáticamente los miembros y los boosts.")
        if role_id is not None and role_id <= 0:
            raise ValueError("El ID del rol debe ser positivo.")
        async with self.lock:
            await self._seed(guild_id)
            if target is not None:
                await self.db.execute(
                    "UPDATE goals SET target = ? WHERE guild_id = ? AND metric = ?",
                    (target, guild_id, key),
                )
            if role_id is not None:
                await self.db.execute(
                    "UPDATE goals SET source = 'role', role_id = ? "
                    "WHERE guild_id = ? AND metric = ?",
                    (role_id, guild_id, key),
                )
            if value is not None:
                await self.db.execute(
                    "UPDATE goals SET source = 'manual', value = ?, role_id = NULL "
                    "WHERE guild_id = ? AND metric = ?",
                    (value, guild_id, key),
                )
            await self.db.commit()

    async def board(self, guild_id: int) -> Board | None:
        async with self.lock:
            async with self.db.execute(
                "SELECT guild_id, channel_id, message_id FROM boards WHERE guild_id = ?",
                (guild_id,),
            ) as cursor:
                row = await cursor.fetchone()
        return Board(**dict(row)) if row else None

    async def boards(self) -> list[Board]:
        async with self.lock:
            async with self.db.execute("SELECT * FROM boards") as cursor:
                return [Board(**dict(row)) for row in await cursor.fetchall()]

    async def save_board(self, board: Board) -> None:
        async with self.lock:
            await self.db.execute(
                "INSERT INTO boards VALUES (?, ?, ?) ON CONFLICT(guild_id) DO UPDATE SET "
                "channel_id = excluded.channel_id, message_id = excluded.message_id",
                (board.guild_id, board.channel_id, board.message_id),
            )
            await self.db.commit()

    async def remove_board(self, guild_id: int) -> None:
        async with self.lock:
            await self.db.execute("DELETE FROM boards WHERE guild_id = ?", (guild_id,))
            await self.db.commit()
