"""Database access and schema migrations.

Migrations are plain SQL files in `migrations/`, named `NNNN_description.sql` and applied in order, each in its own
transaction. Applied migrations are recorded in `schema_migrations`; a migration is never edited after it has been
merged: a change is a new file.
"""

from importlib import resources

import psycopg
from psycopg_pool import ConnectionPool


def make_pool(database_url, **kwargs):
    """A connection pool; opened by the caller (the app's lifespan) and closed with it."""
    return ConnectionPool(database_url, open=False, kwargs={"autocommit": True}, **kwargs)


def migration_files():
    """[(version, name, sql)] in order."""
    out = []
    for f in sorted((resources.files("claimset_portal") / "migrations").iterdir(), key=lambda f: f.name):
        if f.name.endswith(".sql"):
            version = f.name.split("_", 1)[0]
            if not version.isdigit():
                raise ValueError(f"migration {f.name}: the name starts with its number, e.g. 0001_init.sql")
            out.append((int(version), f.name, f.read_text(encoding="utf-8")))
    versions = [v for v, _, _ in out]
    if len(set(versions)) != len(versions):
        raise ValueError("two migrations share a number")
    return out


def migrate(database_url):
    """Apply every migration not yet applied. Returns the names of those applied."""
    applied = []
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations ("
                     " version integer PRIMARY KEY, name text NOT NULL,"
                     " applied_at timestamptz NOT NULL DEFAULT now())")
        done = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
        for version, name, sql in migration_files():
            if version in done:
                continue
            with conn.transaction():
                conn.execute(sql)
                conn.execute("INSERT INTO schema_migrations (version, name) VALUES (%s, %s)", (version, name))
            applied.append(name)
    return applied
