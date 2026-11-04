"""Settings, read from the environment. Secrets live only in the environment, never in the repository."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    #: PostgreSQL connection string (libpq form or URL).
    database_url: str
    #: The public address of the portal, without a trailing slash: used in links the portal writes.
    base_url: str
    #: Where published static files (JSON, reading views, index) are written; Caddy serves them.
    published_dir: Path
    #: "development" or "production".
    environment: str

    @classmethod
    def from_env(cls, env=None):
        env = os.environ if env is None else env
        return cls(
            database_url=env.get("DATABASE_URL", "postgresql://portal:portal@localhost:5432/portal"),
            base_url=env.get("PORTAL_BASE_URL", "http://localhost:8000").rstrip("/"),
            published_dir=Path(env.get("PORTAL_PUBLISHED_DIR", "./published")),
            environment=env.get("PORTAL_ENV", "development"),
        )
