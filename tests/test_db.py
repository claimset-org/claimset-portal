import psycopg

from portal.db import migrate, migration_files


def test_migration_files_are_numbered_in_order():
    files = migration_files()
    assert files and files[0][1] == "0001_init.sql"
    assert [v for v, _, _ in files] == sorted(v for v, _, _ in files)


def test_migrate_applies_once(database_url):
    first = migrate(database_url)
    assert first == [name for _, name, _ in migration_files()]
    assert migrate(database_url) == []
    with psycopg.connect(database_url) as conn:
        extensions = {row[0] for row in conn.execute("SELECT extname FROM pg_extension")}
    assert {"vector", "pg_trgm"} <= extensions


def test_settings_defaults():
    from portal.config import Settings
    s = Settings.from_env({"PORTAL_BASE_URL": "https://example.org/"})
    assert s.base_url == "https://example.org"
    assert s.environment == "development"
