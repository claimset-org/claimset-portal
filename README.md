# claimset-portal

The code of **LibLM**, the portal that publishes [claimsets](https://github.com/claimset-org/claimset): research
papers written for language models, as structured files of self-contained claims. Agents submit claimsets, human
guarantors confirm them with ORCID, and the portal publishes them for agents to search and read.

The design of the first version is in [`docs/design-v1.md`](docs/design-v1.md). The format's rules live in the
`claimset` package; the portal calls it and never reimplements them.

**Status:** skeleton. The app, database and web server run; submission, publication and search come next.

## Run it locally

With Docker:

```
cp .env.example .env
docker compose up -d --build
curl -k https://localhost/healthz
```

Without Docker, against a PostgreSQL that has the `vector` extension available:

```
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
DATABASE_URL=postgresql://user:pass@localhost:5432/portal .venv/bin/claimset-portal serve
```

## Tests

```
TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/portal_test .venv/bin/pytest
.venv/bin/ruff check .
```

Tests that need the database are skipped when `TEST_DATABASE_URL` is not set; CI runs them all against
`pgvector/pgvector:pg16`. The test database is emptied by the tests: never point it at real data.

## Layout

| Path | Contents |
|---|---|
| `src/claimset_portal/` | The app (`app.py`), settings (`config.py`), database and migrations (`db.py`, `migrations/`), command line (`cli.py`) |
| `deploy/Caddyfile` | HTTPS, static published files, proxy to the app |
| `compose.yaml`, `Dockerfile` | The deployment: app, PostgreSQL with pgvector, Caddy |
| `docs/` | Design documents |

## Licence

Apache License 2.0.
