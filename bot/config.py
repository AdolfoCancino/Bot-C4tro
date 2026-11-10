import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    token: str = field(repr=False)
    database_path: Path
    guild_id: int | None = None
    proxy_url: str | None = field(default=None, repr=False)

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        token = os.getenv("DISCORD_TOKEN", "").strip()
        if not token:
            raise ValueError("Falta DISCORD_TOKEN. Configúralo en .env (ver .env.example).")
        raw_guild = os.getenv("DISCORD_GUILD_ID", "").strip()
        if raw_guild and (not raw_guild.isdecimal() or int(raw_guild) <= 0):
            raise ValueError("DISCORD_GUILD_ID debe ser un ID numérico positivo.")
        return cls(
            token=token,
            database_path=Path(os.getenv("DATABASE_PATH", "data/bot.sqlite3")),
            guild_id=int(raw_guild) if raw_guild else None,
            proxy_url=os.getenv("https_proxy") or os.getenv("HTTPS_PROXY") or None,
        )
